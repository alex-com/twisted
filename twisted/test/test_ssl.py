# Copyright (c) 2001-2004 Twisted Matrix Laboratories.
# See LICENSE for details.


from __future__ import nested_scopes
from twisted.trial import unittest
from twisted.internet import protocol, reactor, interfaces, defer
from twisted.protocols import basic
from twisted.python import util, components

try:
    from OpenSSL import SSL, crypto
    from twisted.internet import ssl
    from ssl_helpers import ClientTLSContext
except ImportError:
    SSL = ssl = None

import os
import test_tcp


certPath = util.sibpath(__file__, "server.pem")

class StolenTCPTestCase(test_tcp.ProperlyCloseFilesTestCase, test_tcp.WriteDataTestCase):
    
    def setUp(self):
        self._setUp()
        f = protocol.ServerFactory()
        f.protocol = protocol.Protocol
        self.listener = reactor.listenSSL(
            0, f, ssl.DefaultOpenSSLContextFactory(certPath, certPath), interface="127.0.0.1",
        )
        self.ports.append(self.listener)
        f = protocol.ClientFactory()
        f.protocol = test_tcp.ConnectionLosingProtocol

        f.protocol.master = self
        
        L = []
        def connector():
            p = self.listener.getHost().port
            ctx = ssl.ClientContextFactory()
            return reactor.connectSSL('127.0.0.1', p, f, ctx)
        self.connector = connector

        self.totalConnections = 0


class UnintelligentProtocol(basic.LineReceiver):
    pretext = [
        "first line",
        "last thing before tls starts",
        "STARTTLS",
    ]
    
    posttext = [
        "first thing after tls started",
        "last thing ever",
    ]
    
    
    def connectionMade(self):
        for l in self.pretext:
            self.sendLine(l)

    def lineReceived(self, line):
        if line == "READY":
            self.transport.startTLS(ClientTLSContext(), self.factory.client)
            for l in self.posttext:
                self.sendLine(l)
            self.transport.loseConnection()
        
if ssl is not None:
    class ServerTLSContext(ssl.DefaultOpenSSLContextFactory):
        isClient = 0
        def __init__(self, *args, **kw):
            kw['sslmethod'] = SSL.TLSv1_METHOD
            ssl.DefaultOpenSSLContextFactory.__init__(self, *args, **kw)

class LineCollector(basic.LineReceiver):
    def __init__(self, doTLS, fillBuffer=0):
        self.doTLS = doTLS
        self.fillBuffer = fillBuffer
        
    def connectionMade(self):
        self.factory.rawdata = ''
        self.factory.lines = []

    def lineReceived(self, line):
        self.factory.lines.append(line)
        if line == 'STARTTLS':
            if self.fillBuffer:
                for x in range(500):
                    self.sendLine('X'*1000)
            self.sendLine('READY')
            if self.doTLS:
                ctx = ServerTLSContext(
                    privateKeyFileName=certPath,
                    certificateFileName=certPath,
                )
                self.transport.startTLS(ctx, self.factory.server)
            else:
                self.setRawMode()
    
    def rawDataReceived(self, data):
        self.factory.rawdata += data
        self.factory.done = 1
    
    def connectionLost(self, reason):
        self.factory.done = 1

class TLSTestCase(unittest.TestCase):
    fillBuffer = 0
    
    def testTLS(self):
        cf = protocol.ClientFactory()
        cf.protocol = UnintelligentProtocol
        cf.client = 1

        sf = protocol.ServerFactory()
        sf.protocol = lambda: LineCollector(1, self.fillBuffer)
        sf.done = 0
        sf.server = 1

        port = reactor.listenTCP(0, sf, interface="127.0.0.1")
        portNo = port.getHost().port
        
        reactor.connectTCP('127.0.0.1', portNo, cf)
        
        i = 0
        while i < 1000 and not sf.done:
            reactor.iterate(0.01)
            i += 1
        
        self.failUnless(sf.done, "Never finished reading all lines: %s" % sf.lines)
        self.assertEquals(
            sf.lines,
            UnintelligentProtocol.pretext + UnintelligentProtocol.posttext
        )
    
    def testUnTLS(self):
        cf = protocol.ClientFactory()
        cf.protocol = UnintelligentProtocol
        cf.client = 1

        sf = protocol.ServerFactory()
        sf.protocol = lambda: LineCollector(0, self.fillBuffer)
        sf.done = 0
        sf.server = 1

        port = reactor.listenTCP(0, sf, interface="127.0.0.1")
        portNo = port.getHost().port
        
        reactor.connectTCP('127.0.0.1', portNo, cf)
        
        i = 0
        while i < 1000 and not sf.done:
            reactor.iterate(0.01)
            i += 1
        
        self.failUnless(sf.done, "Never finished reading all lines")
        self.assertEquals(
            sf.lines,
            UnintelligentProtocol.pretext
        )
        self.failUnless(sf.rawdata, "No encrypted bytes received")

    def testBackwardsTLS(self):
        cf = protocol.ClientFactory()
        cf.protocol = lambda: LineCollector(1, self.fillBuffer)
        cf.server = 0
        cf.done = 0

        sf = protocol.ServerFactory()
        sf.protocol = UnintelligentProtocol
        sf.client = 0

        port = reactor.listenTCP(0, sf, interface="127.0.0.1")
        portNo = port.getHost().port
        
        reactor.connectTCP('127.0.0.1', portNo, cf)
        
        i = 0
        while i < 1000 and not cf.done:
            reactor.iterate(0.01)
            i += 1
        
        self.failUnless(cf.done, "Never finished reading all lines")
        self.assertEquals(
            cf.lines,
            UnintelligentProtocol.pretext + UnintelligentProtocol.posttext
        )

    
class SpammyTLSTestCase(TLSTestCase):
    fillBuffer = 1
    def testTLS(self):
        TLSTestCase.testTLS(self)
    def testBackwardsTLS(self):
        TLSTestCase.testBackwardsTLS(self)

    testTLS.todo = "startTLS doesn't empty buffer before starting TLS. :("
    testBackwardsTLS.todo = "startTLS doesn't empty buffer before starting TLS. :("

class SingleLineServerProtocol(protocol.Protocol):
    def connectionMade(self):
        self.transport.identifier = 'SERVER'
        self.transport.write("+OK <some crap>\r\n")
        self.transport.getPeerCertificate()
        
class RecordingClientProtocol(protocol.Protocol):
    def connectionMade(self):
        self.transport.identifier = 'CLIENT'
        self.buffer = []
        self.transport.getPeerCertificate()
    
    def dataReceived(self, data):
        self.factory.buffer.append(data)
        
class BufferingTestCase(unittest.TestCase):
    def testOpenSSLBuffering(self):
        server = protocol.ServerFactory()
        client = protocol.ClientFactory()
        
        server.protocol = SingleLineServerProtocol
        client.protocol = RecordingClientProtocol
        client.buffer = []

        from twisted.internet.ssl import DefaultOpenSSLContextFactory
        from twisted.internet.ssl import ClientContextFactory

        sCTX = DefaultOpenSSLContextFactory(certPath, certPath)
        cCTX = ClientContextFactory()
        
        port = reactor.listenSSL(0, server, sCTX, interface='127.0.0.1')
        reactor.connectSSL('127.0.0.1', port.getHost().port, client, cCTX)

        i = 0
        while i < 5000 and not client.buffer:
            i += 1
            reactor.iterate()
        
        self.assertEquals(client.buffer, ["+OK <some crap>\r\n"])

def generateCertificateObjects(organization, organizationalUnit):
    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, 512)
    req = crypto.X509Req()
    subject = req.get_subject()
    subject.O = organization
    subject.OU = organizationalUnit
    req.set_pubkey(pkey)
    req.sign(pkey, "md5")

    # Here comes the actual certificate
    cert = crypto.X509()
    cert.set_serial_number(1)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365 * 5 * 86400) # expires after 5 years
    cert.set_issuer(req.get_subject())
    cert.set_subject(req.get_subject())
    cert.set_pubkey(req.get_pubkey())
    cert.sign(pkey, "md5")

    return pkey, req, cert

def generateCertificateFiles(basename, organization, organizationalUnit):
    pkey, req, cert = generateCertificateObjects(organization, organizationalUnit)

    for ext, obj, dumpFunc in [
        ('key', pkey, crypto.dump_privatekey),
        ('req', req, crypto.dump_certificate_request),
        ('cert', cert, crypto.dump_certificate)]:
        fName = os.extsep.join((basename, ext))
        fObj = file(fName, 'w')
        fObj.write(dumpFunc(crypto.FILETYPE_PEM, obj))
        fObj.close()

class ImmediatelyDisconnectingProtocol(protocol.Protocol):
    def connectionMade(self):
        # Twisted's SSL support is terribly broken.
        reactor.callLater(0.1, self.transport.loseConnection)

    def connectionLost(self, reason):
        self.factory.connectionDisconnected.callback(None)

class CertificateVerificationCallback(unittest.TestCase):
    def testVerificationCallback(self):
        from twisted.internet.ssl import DefaultOpenSSLContextFactory
        from twisted.internet.ssl import ClientContextFactory

        self.calls = {}
        def serverCallback(*args):
            self.calls['server'] = args
            return True

        def clientCallback(*args):
            self.calls['client'] = args
            return True

        # Make a fake certificate for the server
        self.serverBase = self.mktemp()
        generateCertificateFiles(self.serverBase, "twisted.test.test_ssl", "testVerificationCallback, server")
        serverCtxFactory = DefaultOpenSSLContextFactory(
            os.extsep.join((self.serverBase, 'key')),
            os.extsep.join((self.serverBase, 'cert')),
            verifyCallback=serverCallback)

        # Now do the same thing for the client
        self.clientBase = self.mktemp()
        generateCertificateFiles(self.clientBase, "twisted.test.test_ssl", "testVerificationCallback, client")
        clientCtxFactory = DefaultOpenSSLContextFactory(
            os.extsep.join((self.clientBase, 'key')),
            os.extsep.join((self.clientBase, 'cert')),
            verifyCallback=clientCallback)

        # Set up a server, connect to it with a client, which should work since our verifiers
        # allow anything, then disconnect.
        serverProtocolFactory = protocol.ServerFactory()
        serverProtocolFactory.protocol = protocol.Protocol
        self.serverPort = serverPort = reactor.listenSSL(0, serverProtocolFactory, serverCtxFactory)

        clientProtocolFactory = protocol.ClientFactory()
        clientProtocolFactory.protocol = ImmediatelyDisconnectingProtocol
        clientProtocolFactory.connectionDisconnected = defer.Deferred()
        clientConnector = reactor.connectSSL('127.0.0.1', serverPort.getHost().port, clientProtocolFactory, clientCtxFactory)

        # Go go go go
        return clientProtocolFactory.connectionDisconnected.addCallback(
            self._cbVerificationCallback)

    def _cbVerificationCallback(self, ignoredResult):
        self.assertEquals(len(self.calls), 2)
        self.assertEquals(
            crypto.dump_certificate(crypto.FILETYPE_PEM, self.calls['client'][1]),
            file(os.extsep.join((self.serverBase, 'cert'))).read())
        self.assertEquals(
            crypto.dump_certificate(crypto.FILETYPE_PEM, self.calls['server'][1]),
            file(os.extsep.join((self.clientBase, 'cert'))).read())


        return self.serverPort.stopListening()

if SSL is None:
    for case in (BufferingTestCase, TLSTestCase, SpammyTLSTestCase, StolenTCPTestCase):
        case.skip = "OpenSSL not present"

if not interfaces.IReactorSSL(reactor, None):
    for case in (BufferingTestCase, TLSTestCase, SpammyTLSTestCase, StolenTCPTestCase):
        case.skip = "Reactor doesn't support SSL"
