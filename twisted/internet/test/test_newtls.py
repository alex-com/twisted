# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.internet._newtls}.
"""

from twisted.trial import unittest
from twisted.internet.test.reactormixins import ReactorBuilder
from twisted.internet import protocol
from twisted.internet.defer import Deferred
try:
    from twisted.internet import _newtls
except ImportError:
    _newtls = None
try:
    from twisted.protocols import tls
except ImportError:
    tls = None
from twisted.internet.test.test_tls import ContextGeneratingMixin, TLSMixin



class FakeProducer(object):
    """
    A producer that does nothing.
    """

    def pauseProducing(self):
        pass


    def resumeProducing(self):
        pass


    def stopProducing(self):
        pass



class ProducerProtocol(protocol.Protocol):
    """
    Register a producer, unregister it, and verify the producer hooks up to
    innards of C{TLSMemoryBIOProtocol}.
    """

    def __init__(self, producer, result, doneDeferred):
        self.producer = producer
        self.result = result
        self.done = doneDeferred


    def connectionMade(self):
        if not isinstance(self.transport.protocol,
                          tls.TLSMemoryBIOProtocol):
            # Either the test or the code have a bug...
            raise RuntimeError("TLSMemoryBIOProtocol not hooked up.")

        self.transport.registerProducer(self.producer, True)
        # The producer was registered with the TLSMemoryBIOProtocol:
        self.result.append(self.transport.protocol._producer._producer)

        self.transport.unregisterProducer()
        # The producer was unregistered from the TLSMemoryBIOProtocol:
        self.result.append(self.transport.protocol._producer)
        self.transport.loseConnection()


    def connectionLost(self, reason):
        self.done.callback(None)
        del self.done



class ProducerTestsMixin(ReactorBuilder, TLSMixin, ContextGeneratingMixin):
    """
    Test the new TLS code integrates C{TLSMemoryBIOProtocol} correctly.
    """

    if not tls:
        skip = "Could not import twisted.protocols.tls"

    def test_producerSSLFromStart(self):
        """
        C{registerProducer} and C{unregisterProducer} on TLS transports
        created as SSL from the get go are passed to the
        C{TLSMemoryBIOProtocol}, not the underlying transport directly.
        """
        result = []
        done = Deferred()
        producer = FakeProducer()

        serverFactory = protocol.ServerFactory
        serverFactory.protocol = protocol.Protocol
        reactor = self.buildReactor()
        serverPort = reactor.listenSSL(0, protocol.ServerFactory(),
                                       self.getServerContext(),
                                       interface="127.0.0.1")
        self.addCleanup(serverPort.stopListening)

        factory = protocol.ClientFactory()
        factory.buildProtocol = lambda addr: ProducerProtocol(producer,
                                                              result, done)
        reactor.connectSSL("127.0.0.1", serverPort.getHost().port, factory,
                           self.getClientContext())

        def gotResult(_):
            reactor.stop()
        done.addCallback(gotResult)
        self.runReactor(reactor)

        self.assertEqual(result, [producer, None])


    def test_producerAfterStartTLS(self):
        """
        C{registerProducer} and C{unregisterProducer} on TLS transports
        created by C{startTLS} are passed to the C{TLSMemoryBIOProtocol}, not
        the underlying transport directly.
        """
        result = []
        done = Deferred()
        clientContext = self.getClientContext()
        serverContext = self.getServerContext()

        producer = FakeProducer()

        class StartTLSProtocol(protocol.Protocol):
            def connectionMade(self):
                self.transport.startTLS(serverContext)

        serverFactory = protocol.ServerFactory
        serverFactory.protocol = StartTLSProtocol
        reactor = self.buildReactor()
        serverPort = reactor.listenTCP(0, protocol.ServerFactory(),
                                       interface="127.0.0.1")
        self.addCleanup(serverPort.stopListening)

        class TLSProducerProtocol(ProducerProtocol):
            def connectionMade(self):
                self.transport.startTLS(clientContext)
                ProducerProtocol.connectionMade(self)

        factory = protocol.ClientFactory()
        factory.buildProtocol = lambda addr: TLSProducerProtocol(producer,
                                                                 result, done)
        reactor.connectTCP("127.0.0.1", serverPort.getHost().port, factory)

        def gotResult(_):
            reactor.stop()
        done.addCallback(gotResult)
        self.runReactor(reactor)

        self.assertEqual(result, [producer, None])


globals().update(ProducerTestsMixin.makeTestCaseClasses())
