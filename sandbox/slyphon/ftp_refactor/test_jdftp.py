# Twisted, the Framework of Your Internet
# Copyright (C) 2001 Matthew W. Lefkowitz
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# written and maintained by slyphon (Jonathan D. Simms)

from __future__ import  nested_scopes

import sys, types, os.path
from cStringIO import StringIO

from twisted.trial import unittest
from twisted.protocols import basic
from twisted.internet import reactor, protocol, defer
from twisted.cred import error, portal, checkers, credentials
from twisted.python import log

import jdftp as ftp
from jdftp import DTPFactory
from twisted.protocols.ftp import FTPClient


# taken from t.test.test_pb
class IOPump:
    """Utility to pump data between clients and servers for protocol testing.

    Perhaps this is a utility worthy of being in protocol.py?
    """
    def __init__(self, client, server, clientIO, serverIO):
        self.client = client
        self.server = server
        self.clientIO = clientIO
        self.serverIO = serverIO

    def flush(self):
        "Pump until there is no more input or output."
        reactor.iterate()
        while self.pump():
            reactor.iterate()
        reactor.iterate()

    def pumpAndCount(self):
        numMessages = 0
        while True:
            result = self.pump()
            if result == 0:
                return numMessages
            else:
                numMessages += result
       
    def pump(self):
        """Move data back and forth.

        Returns whether any data was moved.
        """
        self.clientIO.seek(0)
        self.serverIO.seek(0)
        cData = self.clientIO.read()
        sData = self.serverIO.read()
        self.clientIO.seek(0)
        self.serverIO.seek(0)
        self.clientIO.truncate()
        self.serverIO.truncate()
        self.client.transport._checkProducer()
        self.server.transport._checkProducer()
        for byte in cData:
            self.server.dataReceived(byte)
        for byte in sData:
            self.client.dataReceived(byte)
        if cData or sData:
            return 1
        else:
            return 0


class ConnectedServerAndClient(object):
    dc   = None
    dp   = None
    ds   = None
    c    = None
    s    = None
    pump = None
    def __init__(self):
        """Returns a 3-tuple: (client, server, pump)
        """
        self.createPIClientAndServer()

    def createPIClientAndServer(self):
        svr = ftp.FTPFactory()
        svr.timeOut = None
        svr.dtpTimeout = None
        port = portal.Portal(ftp.FTPRealm())
        port.registerChecker(checkers.AllowAnonymousAccess(), credentials.IAnonymous)
        svr.portal = port
        s = svr.buildProtocol(('127.0.0.1',))
        class Foo(basic.LineReceiver):
            def connectionMade(self):
                self.f = self.factory   # to save typing in pdb :-)
            def lineReceived(self,line):
                self.factory.lines.append(line)
        cf = protocol.ClientFactory()
        cf.protocol = Foo
        cf.lines = []
        c = cf.buildProtocol(('127.0.0.1',))
        cio = StringIO()
        sio = StringIO()
        c.makeConnection(protocol.FileWrapper(cio))
        s.makeConnection(protocol.FileWrapper(sio))
        pump = IOPump(c, s, cio, sio)
        self.c, self.s, self.pump = c, s, pump

    def connectDTPClient(self):
        self.dtpFactory = DTPFactory
        self.dtpFactory.debug = False
        self.dtpFactory.peerCheck = False
        svr = self.dtpFactory(self, )
        dtps = svr.buildProtocol(('127.0.0.1',))
        class _(basic.LineReceiver):
            def connectionMade(self):
                self.f = self.factory   # to save typing in pdb :-)
            def lineReceived(self,line):
                self.factory.lines.append(line)
        dtpcf = protocol.ClientFactory()
        dtpcf.protocol = _
        dtpcf.lines = []
        dtpc = dtpcf.buildProtocol(('127.0.0.1',))
        cio = StringIO()
        sio = StringIO()
        dtpc.makeConnection(protocol.FileWrapper(cio))
        dtps.makeConnection(protocol.FileWrapper(sio))
        pump = IOPump(dtpc, dtps, cio, sio)
        self.dc, self.ds, self.dp = dtpc, dtps, pump

    def getCSPumpTuple(self):
        return (self.c, self.s, self.pump)

    def getDtpCSPumpTuple(self):
        if not self.dc:
            self.connectDTPClient()
        return (self.dc, self.ds, self.dp)


class JDFtpTests(unittest.TestCase):
    def setUp(self):
        self.X = ConnectedServerAndClient()

    def tearDown(self):
        delayeds = reactor.getDelayedCalls()
        for d in delayeds:
            d.cancel()

    def testAnonymousLogin(self):
        c, s, pump = self.X.getCSPumpTuple()
        pump.flush()
        self.assertEquals(c.f.lines[-1], ftp.RESPONSE[ftp.WELCOME_MSG])
        c.sendLine('USER anonymous')
        pump.flush()
        self.assertEquals(c.f.lines[-1], ftp.RESPONSE[ftp.GUEST_NAME_OK_NEED_EMAIL])
        c.sendLine('PASS w00t@twistedmatrix.com')
        pump.flush()
        self.assertEquals(c.f.lines[-1], ftp.RESPONSE[ftp.GUEST_LOGGED_IN_PROCEED], c.f.lines)


    def doAnonymousLogin(self,c,s,pump):
        c, s, pump = self.X.getCSPumpTuple()
        pump.flush()
        c.sendLine('USER anonymous')
        pump.flush()
        c.sendLine('PASS w00t@twistedmatrix.com')
        pump.flush()


    def testPWDOnLogin(self):
        c, s, pump = self.X.getCSPumpTuple()
        self.doAnonymousLogin(c,s,pump)
        c.sendLine('PWD')
        pump.flush()
        self.assertEquals(c.f.lines[-1], '257 "/" is current directory.')


    def testCWD(self):
        import warnings
        warnings.warn("""This test is VERY FRAGILE! in fact, its so fragile it won't run on any other computer but mine""")
        c, s, pump = self.X.getCSPumpTuple()
        send = c.sendLine
        flush = pump.flush

        self.doAnonymousLogin(c,s,pump)

        send('CWD src'); flush()
        self.assertEquals(c.f.lines[-1], ftp.RESPONSE[ftp.REQ_FILE_ACTN_COMPLETED_OK])

        send('PWD'); flush()
        self.assertEquals(c.f.lines[-1], '257 "/src" is current directory.')

        send('CWD freemind'); flush()
        self.assertEquals(c.f.lines[-1], ftp.RESPONSE[ftp.REQ_FILE_ACTN_COMPLETED_OK])

        send('PWD'); flush()
        self.assertEquals(c.f.lines[-1], '257 "/src/freemind" is current directory.')

        send('CWD ../radix'); flush()
        self.assertEquals(c.f.lines[-1], ftp.RESPONSE[ftp.REQ_FILE_ACTN_COMPLETED_OK])

        send('PWD'); flush()
        send('CWD ../../../'); flush()


    def testCDUP(self):
        c, s, pump = self.X.getCSPumpTuple()
        send = c.sendLine
        flush = pump.flush

        self.doAnonymousLogin(c,s,pump)
        send('CWD src/freemind/doc'); flush()

        send('PWD'); flush()
        self.assertEquals(c.f.lines[-1], '257 "/src/freemind/doc" is current directory.')
    
        send('CDUP'); flush()
        send('PWD'); flush()
        self.assertEquals(c.f.lines[-1], '257 "/src/freemind" is current directory.')

        send('CDUP'); flush()
        send('PWD'); flush()
        self.assertEquals(c.f.lines[-1], '257 "/src" is current directory.')

        send('CDUP'); flush()
        send('PWD'); flush()
        self.assertEquals(c.f.lines[-1], '257 "/" is current directory.')


    def testPASV(self):
        # TODO: need to figure out how to test this over TCP connection
        pass

    def testRETR(self):
        c, s, p = self.X.getCSPumpTuple()
        self.doAnonymousLogin(c,s,p)
        dc, ds, dpump = self.X.getDtpCSPumpTuple()
        
        pc.sendLine('PASV'); ppump.flush()

        ds.sendLine('boo!'); dpump.flush()
        print dc.f.lines[-1]

#    testRETR.skip = 'skip it'


    def testWelcomeMessage(self):
        c, s, pump = self.X.getCSPumpTuple()
        pump.flush()
        self.assertEquals(c.f.lines[-1], ftp.RESPONSE[ftp.WELCOME_MSG])


