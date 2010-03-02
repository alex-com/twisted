# Copyright (c) 2007-2010 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for sendfile.
"""

import socket, errno

from twisted.trial.unittest import TestCase
from twisted.internet.defer import gatherResults, Deferred, DeferredList
from twisted.internet import protocol, reactor, tcp, error

try:
    from twisted.python._sendfile import sendfile
except ImportError:
    sendfile = None



class SendfileTestCase(TestCase):
    """
    Tests for L{twisted.python._sendfile}.
    """

    def setUp(self):
        """
        Create a listening server port and a list with which to keep track
        of created sockets.
        """
        self.serverSocket = socket.socket()
        self.serverSocket.bind(('127.0.0.1', 0))
        self.serverSocket.listen(1)
        self.connections = [self.serverSocket]
        filename = self.mktemp()
        f = open(filename, 'w+')
        f.write('x' * 1000)
        f.close()
        self.file = open(filename, 'r')


    def tearDown(self):
        """
        Close any sockets which were opened by the test.
        """
        for skt in self.connections:
            skt.close()
        self.file.close()


    def _connectedPair(self):
        """
        Return the two sockets which make up a new TCP connection.
        """
        client = socket.socket()
        client.setblocking(False)
        try:
            client.connect(('127.0.0.1', self.serverSocket.getsockname()[1]))
        except socket.error, e:
            self.assertEquals(e.args[0], errno.EINPROGRESS)
        server, addr = self.serverSocket.accept()

        self.connections.extend((client, server))
        return client, server


    def test_basic(self):
        """
        Test the basic behavior for sendfile.
        """
        server, client = self._connectedPair()
        s, o = sendfile(server.fileno(), self.file.fileno(), 0, 100)
        self.assertEquals(s, 100)
        self.assertEquals(o, 100)
        data = client.recv(500)
        self.assertEquals(len(data), 100)

        s, o = sendfile(server.fileno(), self.file.fileno(), o, 150)
        self.assertEquals(s, 150)
        self.assertEquals(o, 250)
        data = client.recv(500)
        self.assertEquals(len(data), 150)


    def test_afterSend(self):
        """
        Verify that a send after sendfile behaves correctly.
        """
        server, client = self._connectedPair()
        server.send('y' * 10)
        s, o = sendfile(server.fileno(), self.file.fileno(), 0, 100)
        self.assertEquals(s, 100)
        self.assertEquals(o, 100)
        data = client.recv(200)
        if len(data) < 100:
            data += client.recv(200)
        self.assertEquals(len(data), 110)
        self.assertEquals(data[:10], 'y' * 10)
        self.assertEquals(data[10:20], 'x' * 10)



class SendfileProto(protocol.Protocol):
    """
    Protocol used on the server using sendfile.

    @ivar d: deferred fired when the first connection is made.
    """
    d = None

    def connectionMade(self):
        """
        Fire the connetion deferred.
        """
        self.d.callback(self)



class SendfileClientProto(protocol.Protocol):
    """
    Protocol used on the client receiving data of the sendfile server.

    @ivar buffer: hold data received.
    @ivar d: deferred fired when all expected data has been received.
    @ivar expected: amount of data expected.
    """
    buffer = ""
    d = None
    expected = 0

    def dataReceived(self, data):
        """
        Store the data, and fire the deferred if all data has been received.
        """
        self.buffer += data
        if len(self.buffer) >= self.expected and self.d:
            d = self.d
            self.d = None
            d.callback(self.buffer)



class SendfileIntegrationTestCase(TestCase):
    """
    Test sendfile integration within twisted.
    """

    def setUp(self):
        """
        Create a file to send, and start a server.
        """
        filename = self.mktemp()
        f = open(filename, 'w+')
        f.write('x' * 1000000)
        f.close()
        self.file = open(filename, 'r')

        factory = protocol.ServerFactory()
        factory.protocol = SendfileProto
        self.port = reactor.listenTCP(0, factory)

        self.client = None


    def tearDown(self):
        """
        Close client connection, close the file, and stop the server.
        """
        if self.client is not None:
            self.client.transport.loseConnection()
        self.file.close()
        return self.port.stopListening()


    def _test(self, expected=1000000, onMade=lambda proto: None):
        """
        Helper for testing sendfile.

        @return: a list of 3 deferreds: the deferred fired at connection,
            the deferred fired by L{SendfileClientProto} when transfer is
            complete, and the deferred that result from the sendfile call on
            the transport.
        @rtype: C{list} of L{Deferred}s.
        """
        portNum = self.port.getHost().port
        d2 = Deferred()
        SendfileClientProto.d = d2
        SendfileClientProto.expected = expected
        d3 = Deferred()
        SendfileProto.d = d3
        def cb(proto):
            onMade(proto)
            return proto.transport.sendfile(self.file)
        d3.addCallback(cb)

        clientCreator = protocol.ClientCreator(reactor, SendfileClientProto)
        d = clientCreator.connectTCP("127.0.0.1", portNum)
        def gotClient(client):
            self.client = client

        d.addCallback(gotClient)
        return [d, d2, d3]


    def test_basic(self):
        """
        Test a classic sendfile over the wire: the transfer should complete
        successfully with all the data.
        """
        def cb(res):
            self.assertEquals(len(res[1]), 1000000)
        return gatherResults(self._test()).addCallback(cb)


    def test_pendingData(self):
        """
        Test a sendfile after some data already written: the data written
        before the sendfile should arrive before.
        """
        def onMade(proto):
            proto.transport.write('y' * 10)
        def cb(res):
            data = res[1]
            self.assertEquals(len(data), 1000010)
            self.assertEquals(data[:10], 'y' * 10)
            self.assertEquals(data[10:20], 'x' * 10)

        return gatherResults(self._test(1000010, onMade)).addCallback(cb)


    def test_error(self):
        """
        Test errors during sendfile call: simulate an error during the sendfile
        call, and check that the sendfile L{Deferred} forward the error.
        """
        def sendError(*args):
            raise IOError("That's bad!")
        d = Deferred()
        l = self._test(100000)
        l.append(d)
        def gotData(data):
            self.assertTrue(len(data) >= 100000)
            self.patch(tcp, "sendfile", sendError)
            self.client.connectionLost = lost
            return d
        def lost(result):
            try:
                self.assertIsInstance(result.value, error.ConnectionDone)
                self.assertTrue(len(self.client.buffer) < 1000000)
            except:
                d.errback()
            else:
                d.callback(None)
        l[1].addCallback(gotData)
        def check(res):
            for i in (0, 1, 3):
                self.assertTrue(res[i][0])
            res[2][1].trap(IOError)
            self.assertFalse(res[2][0])
        return DeferredList(l, consumeErrors=True
            ).addCallback(check)

    if sendfile is None:
        test_error.skip = "sendfile not available"


    def test_errorAtFirstSight(self):
        """
        Test when sendfile fails at first call, and that it fallbacks to
        producer chain.
        """
        oldSendfile = tcp.sendfile
        def sendError(*args):
            raise IOError("That's bad!")
        tcp.sendfile = sendError
        def restoreSendfile(res):
            tcp.sendfile = oldSendfile
            return res
        return gatherResults(self._test()).addBoth(restoreSendfile)

    if sendfile is None:
        test_errorAtFirstSight.skip = "sendfile not available"



class SendfileInfoTestCase(TestCase):
    """
    Tests for L{tcp.SendfileInfo}.
    """

    def test_invalidFile(self):
        """
        Test with invalid input file: a plain string should raise an
        C{AttributeError}, a file closed a L{ValueError}.
        """
        self.assertRaises(AttributeError, tcp.SendfileInfo, "blah")
        filename = self.mktemp()
        f = open(filename, 'w+')
        f.write('x')
        f.close()
        self.assertRaises(ValueError, tcp.SendfileInfo, f)


    def test_lengthDetection(self):
        """
        Test that file length detection works and preserves file position.
        """
        filename = self.mktemp()
        f = open(filename, 'w+')
        f.write('x' * 42)
        f.close()
        f = open(filename, 'r')
        f.seek(7)
        try:
            sfi = tcp.SendfileInfo(f)
            self.assertEquals(sfi.count, 42)
            self.assertEquals(f.tell(), 7)
        finally:
            f.close()


if sendfile is None:
   SendfileTestCase.skip = "sendfile not available"
