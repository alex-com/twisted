# -*- test-case-name: twisted.test.test_stdio.StandardInputOutputTestCase.testHostAndPeer -*-
# Copyright (c) 2006 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Main program for the child process run by
L{twisted.test.test_stdio.StandardInputOutputTestCase.testHostAndPeer} to test
that ITransport.getHost() and ITransport.getPeer() work for process transports.
"""

from twisted.internet import stdio, protocol, reactor

class HostPeerChild(protocol.Protocol):
    def connectionMade(self):
        self.transport.write('\n'.join([
            str(self.transport.getHost()),
            str(self.transport.getPeer())]))
        self.transport.loseConnection()


    def connectionLost(self, reason):
        reactor.stop()


if __name__ == '__main__':
    stdio.StandardIO(HostPeerChild())
    reactor.run()
