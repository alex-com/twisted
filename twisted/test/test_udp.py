# -*- test-case-name: twisted.test.test_udp -*-
# Copyright (c) 2001-2009 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for implementations of L{IReactorUDP} and L{IReactorMulticast}.
"""

from twisted.trial import unittest, util

from twisted.internet.defer import Deferred, gatherResults, maybeDeferred
from twisted.internet import protocol, reactor, error, defer, interfaces
from twisted.internet.udp import Port
from twisted.python import runtime
from twisted.python.runtime import platformType
import socket


class Mixin:

    started = 0
    stopped = 0

    startedDeferred = None

    def __init__(self):
        self.packets = []

    def startProtocol(self):
        self.started = 1
        if self.startedDeferred is not None:
            d, self.startedDeferred = self.startedDeferred, None
            d.callback(None)

    def stopProtocol(self):
        self.stopped = 1


class Server(Mixin, protocol.DatagramProtocol):
    packetReceived = None
    refused = 0


    def datagramReceived(self, data, addr):
        self.packets.append((data, addr))
        if self.packetReceived is not None:
            d, self.packetReceived = self.packetReceived, None
            d.callback(None)



class Client(Mixin, protocol.ConnectedDatagramProtocol):

    packetReceived = None
    refused = 0

    def datagramReceived(self, data):
        self.packets.append(data)
        if self.packetReceived is not None:
            d, self.packetReceived = self.packetReceived, None
            d.callback(None)

    def connectionFailed(self, failure):
        if self.startedDeferred is not None:
            d, self.startedDeferred = self.startedDeferred, None
            d.errback(failure)
        self.failure = failure

    def connectionRefused(self):
        if self.startedDeferred is not None:
            d, self.startedDeferred = self.startedDeferred, None
            d.errback(error.ConnectionRefusedError("yup"))
        self.refused = 1


class GoodClient(Server):

    def connectionRefused(self):
        if self.startedDeferred is not None:
            d, self.startedDeferred = self.startedDeferred, None
            d.errback(error.ConnectionRefusedError("yup"))
        self.refused = 1



class BadClientError(Exception):
    """
    Raised by BadClient at the end of every datagramReceived call to try and
    screw stuff up.
    """



class BadClient(protocol.DatagramProtocol):
    """
    A DatagramProtocol which always raises an exception from datagramReceived.
    Used to test error handling behavior in the reactor for that method.
    """
    d = None

    def setDeferred(self, d):
        """
        Set the Deferred which will be called back when datagramReceived is
        called.
        """
        self.d = d


    def datagramReceived(self, bytes, addr):
        if self.d is not None:
            d, self.d = self.d, None
            d.callback(bytes)
        raise BadClientError("Application code is very buggy!")



class MockSocket(object):
    def __init__(self, retvals):
        self.retvals = retvals
    def recvfrom(self, size):
        ret = self.retvals.pop(0)
        if isinstance(ret, socket.error):
            raise ret
        return ret, None



class MockProtocol(object):
    def datagramReceived(self, data, addr):
        pass



class UDPTestCase(unittest.TestCase):

    def testOldAddress(self):
        server = Server()
        d = server.startedDeferred = defer.Deferred()
        p = reactor.listenUDP(0, server, interface="127.0.0.1")
        def cbStarted(ignored):
            addr = p.getHost()
            self.assertEquals(addr, ('INET_UDP', addr.host, addr.port))
            return p.stopListening()
        return d.addCallback(cbStarted)
    testOldAddress.suppress = [
        util.suppress(message='IPv4Address.__getitem__',
                      category=DeprecationWarning)]


    def testStartStop(self):
        server = Server()
        d = server.startedDeferred = defer.Deferred()
        port1 = reactor.listenUDP(0, server, interface="127.0.0.1")
        def cbStarted(ignored):
            self.assertEquals(server.started, 1)
            self.assertEquals(server.stopped, 0)
            return port1.stopListening()
        def cbStopped(ignored):
            self.assertEquals(server.stopped, 1)
        return d.addCallback(cbStarted).addCallback(cbStopped)

    def testRebind(self):
        # Ensure binding the same DatagramProtocol repeatedly invokes all
        # the right callbacks.
        server = Server()
        d = server.startedDeferred = defer.Deferred()
        p = reactor.listenUDP(0, server, interface="127.0.0.1")

        def cbStarted(ignored, port):
            return port.stopListening()

        def cbStopped(ignored):
            d = server.startedDeferred = defer.Deferred()
            p = reactor.listenUDP(0, server, interface="127.0.0.1")
            return d.addCallback(cbStarted, p)

        return d.addCallback(cbStarted, p)


    def testBindError(self):
        server = Server()
        d = server.startedDeferred = defer.Deferred()
        port = reactor.listenUDP(0, server, interface='127.0.0.1')

        def cbStarted(ignored):
            self.assertEquals(port.getHost(), server.transport.getHost())

            server2 = Server()
            self.assertRaises(
                error.CannotListenError,
                reactor.listenUDP, port.getHost().port, server2,
                interface='127.0.0.1')
        d.addCallback(cbStarted)

        def cbFinished(ignored):
            return port.stopListening()
        d.addCallback(cbFinished)
        return d

    def testSendPackets(self):
        server = Server()
        serverStarted = server.startedDeferred = defer.Deferred()
        port1 = reactor.listenUDP(0, server, interface="127.0.0.1")

        client = GoodClient()
        clientStarted = client.startedDeferred = defer.Deferred()

        def cbServerStarted(ignored):
            self.port2 = reactor.listenUDP(0, client, interface="127.0.0.1")
            return clientStarted

        d = serverStarted.addCallback(cbServerStarted)

        def cbClientStarted(ignored):
            client.transport.connect("127.0.0.1",
                                     server.transport.getHost().port)
            cAddr = client.transport.getHost()
            sAddr = server.transport.getHost()

            serverSend = client.packetReceived = defer.Deferred()
            server.transport.write("hello", (cAddr.host, cAddr.port))

            clientWrites = [
                ("a",),
                ("b", None),
                ("c", (sAddr.host, sAddr.port))]

            def cbClientSend(ignored):
                if clientWrites:
                    nextClientWrite = server.packetReceived = defer.Deferred()
                    nextClientWrite.addCallback(cbClientSend)
                    client.transport.write(*clientWrites.pop(0))
                    return nextClientWrite

            # No one will ever call .errback on either of these Deferreds,
            # but there is a non-trivial amount of test code which might
            # cause them to fail somehow.  So fireOnOneErrback=True.
            return defer.DeferredList([
                cbClientSend(None),
                serverSend],
                fireOnOneErrback=True)

        d.addCallback(cbClientStarted)

        def cbSendsFinished(ignored):
            cAddr = client.transport.getHost()
            sAddr = server.transport.getHost()
            self.assertEquals(
                client.packets,
                [("hello", (sAddr.host, sAddr.port))])
            clientAddr = (cAddr.host, cAddr.port)
            self.assertEquals(
                server.packets,
                [("a", clientAddr),
                 ("b", clientAddr),
                 ("c", clientAddr)])

        d.addCallback(cbSendsFinished)

        def cbFinished(ignored):
            return defer.DeferredList([
                defer.maybeDeferred(port1.stopListening),
                defer.maybeDeferred(self.port2.stopListening)],
                fireOnOneErrback=True)

        d.addCallback(cbFinished)
        return d


    def testConnectionRefused(self):
        # assume no one listening on port 80 UDP
        client = GoodClient()
        clientStarted = client.startedDeferred = defer.Deferred()
        port = reactor.listenUDP(0, client, interface="127.0.0.1")

        server = Server()
        serverStarted = server.startedDeferred = defer.Deferred()
        port2 = reactor.listenUDP(0, server, interface="127.0.0.1")

        d = defer.DeferredList(
            [clientStarted, serverStarted],
            fireOnOneErrback=True)

        def cbStarted(ignored):
            connectionRefused = client.startedDeferred = defer.Deferred()
            client.transport.connect("127.0.0.1", 80)

            for i in range(10):
                client.transport.write(str(i))
                server.transport.write(str(i), ("127.0.0.1", 80))

            return self.assertFailure(
                connectionRefused,
                error.ConnectionRefusedError)

        d.addCallback(cbStarted)

        def cbFinished(ignored):
            return defer.DeferredList([
                defer.maybeDeferred(port.stopListening),
                defer.maybeDeferred(port2.stopListening)],
                fireOnOneErrback=True)

        d.addCallback(cbFinished)
        return d

    def testBadConnect(self):
        client = GoodClient()
        port = reactor.listenUDP(0, client, interface="127.0.0.1")
        self.assertRaises(ValueError, client.transport.connect,
                          "localhost", 80)
        client.transport.connect("127.0.0.1", 80)
        self.assertRaises(RuntimeError, client.transport.connect,
                          "127.0.0.1", 80)
        return port.stopListening()



    def testDatagramReceivedError(self):
        """
        Test that when datagramReceived raises an exception it is logged but
        the port is not disconnected.
        """
        finalDeferred = defer.Deferred()

        def cbCompleted(ign):
            """
            Flush the exceptions which the reactor should have logged and make
            sure they're actually there.
            """
            errs = self.flushLoggedErrors(BadClientError)
            self.assertEquals(len(errs), 2, "Incorrectly found %d errors, expected 2" % (len(errs),))
        finalDeferred.addCallback(cbCompleted)

        client = BadClient()
        port = reactor.listenUDP(0, client, interface='127.0.0.1')

        def cbCleanup(result):
            """
            Disconnect the port we started and pass on whatever was given to us
            in case it was a Failure.
            """
            return defer.maybeDeferred(port.stopListening).addBoth(lambda ign: result)
        finalDeferred.addBoth(cbCleanup)

        addr = port.getHost()

        # UDP is not reliable.  Try to send as many as 60 packets before giving
        # up.  Conceivably, all sixty could be lost, but they probably won't be
        # unless all UDP traffic is being dropped, and then the rest of these
        # UDP tests will likely fail as well.  Ideally, this test (and probably
        # others) wouldn't even use actual UDP traffic: instead, they would
        # stub out the socket with a fake one which could be made to behave in
        # whatever way the test desires.  Unfortunately, this is hard because
        # of differences in various reactor implementations.
        attempts = range(60)
        succeededAttempts = []

        def makeAttempt():
            """
            Send one packet to the listening BadClient.  Set up a 0.1 second
            timeout to do re-transmits in case the packet is dropped.  When two
            packets have been received by the BadClient, stop sending and let
            the finalDeferred's callbacks do some assertions.
            """
            if not attempts:
                try:
                    self.fail("Not enough packets received")
                except:
                    finalDeferred.errback()

            self.failIfIdentical(client.transport, None, "UDP Protocol lost its transport")

            packet = str(attempts.pop(0))
            packetDeferred = defer.Deferred()
            client.setDeferred(packetDeferred)
            client.transport.write(packet, (addr.host, addr.port))

            def cbPacketReceived(packet):
                """
                A packet arrived.  Cancel the timeout for it, record it, and
                maybe finish the test.
                """
                timeoutCall.cancel()
                succeededAttempts.append(packet)
                if len(succeededAttempts) == 2:
                    # The second error has not yet been logged, since the
                    # exception which causes it hasn't even been raised yet.
                    # Give the datagramReceived call a chance to finish, then
                    # let the test finish asserting things.
                    reactor.callLater(0, finalDeferred.callback, None)
                else:
                    makeAttempt()

            def ebPacketTimeout(err):
                """
                The packet wasn't received quickly enough.  Try sending another
                one.  It doesn't matter if the packet for which this was the
                timeout eventually arrives: makeAttempt throws away the
                Deferred on which this function is the errback, so when
                datagramReceived callbacks, so it won't be on this Deferred, so
                it won't raise an AlreadyCalledError.
                """
                makeAttempt()

            packetDeferred.addCallbacks(cbPacketReceived, ebPacketTimeout)
            packetDeferred.addErrback(finalDeferred.errback)

            timeoutCall = reactor.callLater(
                0.1, packetDeferred.errback,
                error.TimeoutError(
                    "Timed out in testDatagramReceivedError"))

        makeAttempt()
        return finalDeferred


    def testPortRepr(self):
        client = GoodClient()
        p = reactor.listenUDP(0, client)
        portNo = str(p.getHost().port)
        self.failIf(repr(p).find(portNo) == -1)
        def stoppedListening(ign):
            self.failIf(repr(p).find(portNo) != -1)
        d = defer.maybeDeferred(p.stopListening)
        d.addCallback(stoppedListening)
        return d


    def testRawSocketReads(self):
        if platformType == 'win32':
            from errno import WSAEWOULDBLOCK as EWOULDBLOCK
            from errno import WSAECONNREFUSED as ECONNREFUSED
        else:
            from errno import EWOULDBLOCK, ECONNREFUSED

        port = Port(None, MockProtocol())

        # Normal result, no errors
        port.socket = MockSocket(["result", "123", socket.error(EWOULDBLOCK)])
        port.doRead()

        # Try an immediate "connection refused"
        port.socket = MockSocket([socket.error(ECONNREFUSED)])
        port.doRead()

        # Some good data, followed by an unknown error
        port.socket = MockSocket(["good", socket.error(1337)])
        self.assertRaises(socket.error, port.doRead)


class ReactorShutdownInteraction(unittest.TestCase):
    """Test reactor shutdown interaction"""

    def setUp(self):
        """Start a UDP port"""
        self.server = Server()
        self.port = reactor.listenUDP(0, self.server, interface='127.0.0.1')

    def tearDown(self):
        """Stop the UDP port"""
        return self.port.stopListening()

    def testShutdownFromDatagramReceived(self):
        """Test reactor shutdown while in a recvfrom() loop"""

        # udp.Port's doRead calls recvfrom() in a loop, as an optimization.
        # It is important this loop terminate under various conditions.
        # Previously, if datagramReceived synchronously invoked
        # reactor.stop(), under certain reactors, the Port's socket would
        # synchronously disappear, causing an AttributeError inside that
        # loop.  This was mishandled, causing the loop to spin forever.
        # This test is primarily to ensure that the loop never spins
        # forever.

        finished = defer.Deferred()
        pr = self.server.packetReceived = defer.Deferred()

        def pktRece(ignored):
            # Simulate reactor.stop() behavior :(
            self.server.transport.connectionLost()
            # Then delay this Deferred chain until the protocol has been
            # disconnected, as the reactor should do in an error condition
            # such as we are inducing.  This is very much a whitebox test.
            reactor.callLater(0, finished.callback, None)
        pr.addCallback(pktRece)

        def flushErrors(ignored):
            # We are breaking abstraction and calling private APIs, any
            # number of horrible errors might occur.  As long as the reactor
            # doesn't hang, this test is satisfied.  (There may be room for
            # another, stricter test.)
            self.flushLoggedErrors()
        finished.addCallback(flushErrors)
        self.server.transport.write('\0' * 64, ('127.0.0.1',
                                    self.server.transport.getHost().port))
        return finished



class MulticastTestCase(unittest.TestCase):

    def setUp(self):
        self.server = Server()
        self.client = Client()
        # multicast won't work if we listen over loopback, apparently
        self.port1 = reactor.listenMulticast(0, self.server)
        self.port2 = reactor.listenMulticast(0, self.client)
        self.client.transport.connect(
            "127.0.0.1", self.server.transport.getHost().port)


    def tearDown(self):
        return gatherResults([
            maybeDeferred(self.port1.stopListening),
            maybeDeferred(self.port2.stopListening)])


    def testTTL(self):
        for o in self.client, self.server:
            self.assertEquals(o.transport.getTTL(), 1)
            o.transport.setTTL(2)
            self.assertEquals(o.transport.getTTL(), 2)


    def test_loopback(self):
        """
        Test that after loopback mode has been set, multicast packets are
        delivered to their sender.
        """
        self.assertEquals(self.server.transport.getLoopbackMode(), 1)
        addr = self.server.transport.getHost()
        joined = self.server.transport.joinGroup("225.0.0.250")

        def cbJoined(ignored):
            d = self.server.packetReceived = Deferred()
            self.server.transport.write("hello", ("225.0.0.250", addr.port))
            return d
        joined.addCallback(cbJoined)

        def cbPacket(ignored):
            self.assertEqual(len(self.server.packets), 1)
            self.server.transport.setLoopbackMode(0)
            self.assertEquals(self.server.transport.getLoopbackMode(), 0)
            self.server.transport.write("hello", ("225.0.0.250", addr.port))

            # This is fairly lame.
            d = Deferred()
            reactor.callLater(0, d.callback, None)
            return d
        joined.addCallback(cbPacket)

        def cbNoPacket(ignored):
            self.assertEqual(len(self.server.packets), 1)
        joined.addCallback(cbNoPacket)

        return joined


    def test_interface(self):
        """
        Test C{getOutgoingInterface} and C{setOutgoingInterface}.
        """
        self.assertEqual(
            self.client.transport.getOutgoingInterface(), "0.0.0.0")
        self.assertEqual(
            self.server.transport.getOutgoingInterface(), "0.0.0.0")

        d1 = self.client.transport.setOutgoingInterface("127.0.0.1")
        d2 = self.server.transport.setOutgoingInterface("127.0.0.1")
        result = gatherResults([d1, d2])

        def cbInterfaces(ignored):
            self.assertEqual(
                self.client.transport.getOutgoingInterface(), "127.0.0.1")
            self.assertEqual(
                self.server.transport.getOutgoingInterface(), "127.0.0.1")
        result.addCallback(cbInterfaces)
        return result


    def test_joinLeave(self):
        """
        Test that multicast a group can be joined and left.
        """
        d = self.client.transport.joinGroup("225.0.0.250")

        def clientJoined(ignored):
            return self.client.transport.leaveGroup("225.0.0.250")
        d.addCallback(clientJoined)

        def clientLeft(ignored):
            return self.server.transport.joinGroup("225.0.0.250")
        d.addCallback(clientLeft)

        def serverJoined(ignored):
            return self.server.transport.leaveGroup("225.0.0.250")
        d.addCallback(serverJoined)

        return d


    def test_joinFailure(self):
        """
        Test that an attempt to join an address which is not a multicast
        address fails with L{error.MulticastJoinError}.
        """
        # 127.0.0.1 is not a multicast address, so joining it should fail.
        return self.assertFailure(
            self.client.transport.joinGroup("127.0.0.1"),
            error.MulticastJoinError)
    if runtime.platform.isWindows() and not runtime.platform.isVista():
        test_joinFailure.todo = "Windows' multicast is wonky"


    def test_multicast(self):
        """
        Test that a multicast group can be joined and messages sent to and
        received from it.
        """
        c = Server()
        p = reactor.listenMulticast(0, c)
        addr = self.server.transport.getHost()

        joined = self.server.transport.joinGroup("225.0.0.250")

        def cbJoined(ignored):
            d = self.server.packetReceived = Deferred()
            c.transport.write("hello world", ("225.0.0.250", addr.port))
            return d
        joined.addCallback(cbJoined)

        def cbPacket(ignored):
            self.assertEquals(self.server.packets[0][0], "hello world")
        joined.addCallback(cbPacket)

        def cleanup(passthrough):
            result = maybeDeferred(p.stopListening)
            result.addCallback(lambda ign: passthrough)
            return result
        joined.addCallback(cleanup)

        return joined


    def test_multiListen(self):
        """
        Test that multiple sockets can listen on the same multicast port and
        that they both receive multicast messages directed to that address.
        """
        firstClient = Server()
        firstPort = reactor.listenMulticast(
            0, firstClient, listenMultiple=True)

        portno = firstPort.getHost().port

        secondClient = Server()
        secondPort = reactor.listenMulticast(
            portno, secondClient, listenMultiple=True)

        joined = self.server.transport.joinGroup("225.0.0.250")

        def serverJoined(ignored):
            d1 = firstClient.packetReceived = Deferred()
            d2 = secondClient.packetReceived = Deferred()
            firstClient.transport.write("hello world", ("225.0.0.250", portno))
            return gatherResults([d1, d2])
        joined.addCallback(serverJoined)

        def gotPackets(ignored):
            self.assertEquals(firstClient.packets[0][0], "hello world")
            self.assertEquals(secondClient.packets[0][0], "hello world")
        joined.addCallback(gotPackets)

        def cleanup(passthrough):
            result = gatherResults([
                maybeDeferred(firstPort.stopListening),
                maybeDeferred(secondPort.stopListening)])
            result.addCallback(lambda ign: passthrough)
            return result
        joined.addBoth(cleanup)
        return joined
    if runtime.platform.isWindows():
        test_multiListen.skip = ("on non-linux platforms it appears multiple "
                                 "processes can listen, but not multiple sockets "
                                 "in same process?")

if not interfaces.IReactorUDP(reactor, None):
    UDPTestCase.skip = "This reactor does not support UDP"
    ReactorShutdownInteraction.skip = "This reactor does not support UDP"
if not interfaces.IReactorMulticast(reactor, None):
    MulticastTestCase.skip = "This reactor does not support multicast"

def checkForLinux22():
    import os
    if os.path.exists("/proc/version"):
        s = open("/proc/version").read()
        if s.startswith("Linux version"):
            s = s.split()[2]
            if s.split(".")[:2] == ["2", "2"]:
                f = MulticastTestCase.testInterface.im_func
                f.todo = "figure out why this fails in linux 2.2"
checkForLinux22()
