# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.internet._newtls}.
"""

from twisted.trial import unittest
from twisted.internet import protocol, reactor
from twisted.internet.defer import Deferred
try:
    from twisted.internet import _newtls
except ImportError:
    _newtls = None
try:
    from twisted.protocols import tls
except ImportError:
    tls = None
from twisted.internet.test.test_tls import ContextGeneratingMixin



class IntegrationTests(unittest.TestCase, ContextGeneratingMixin):
    """
    Test the new TLS code integrates C{TLSMemoryBIOProtocol} correctly.
    """

    if not tls:
        skip = "Could not import twisted.protocols.tls"

    def test_producerAfterStartTLS(self):
        """
        C{registerProducer} and C{unregisterProducer} on TLS transports
        created by C{startTLS} are passed to the C{TLSMemoryBioProtocol}, not
        the underlying transport directly.

        This is a whitebox test, heavily tied to implementation details of
        C{startTLS}.
        """
        result = []
        done = Deferred()
        clientContext = self.getClientContext()

        class FakeProducer(object):
            def pauseProducing(self):
                pass
            def resumeProducing(self):
                pass
            def stopProducing(self):
                pass
        producer = FakeProducer()

        class ProducerProtocol(protocol.Protocol):
            def connectionMade(self):
                from twisted.python import log
                log.msg("connectionmade")
                self.transport.startTLS(clientContext)
                if not isinstance(self.transport.protocol,
                                  tls.TLSMemoryBIOProtocol):
                    # Either the test or the code have a bug...
                    raise RuntimeError("TLSMemoryBioProtocol not hooked up.")
                producer.transport = self.transport
                self.transport.registerProducer(producer, True)

                # The producer was registered with the TLSMemoryBioProtocol:
                result.append(self.transport.protocol._producer._producer)
                self.transport.unregisterProducer()
                # The producer was unregistered from the TLSMemoryBioProtocol:
                result.append(self.transport.protocol._producer)

                self.transport.loseConnection()
                log.msg("connectionmade done" + str(result))

            def connectionLost(self, reason):
                done.callback(None)

        serverFactory = protocol.ServerFactory
        serverFactory.protocol = protocol.Protocol
        serverPort = reactor.listenSSL(0, protocol.ServerFactory(),
                                       self.getServerContext())
        self.addCleanup(serverPort.stopListening)
        factory = protocol.ClientFactory()
        factory.protocol = ProducerProtocol
        reactor.connectTCP(
            serverPort.getHost().host, serverPort.getHost().port,
            factory)

        def gotResult(_):
            self.assertEqual(result, [producer, None])
        return done.addCallback(gotResult)
