# -*- test-case-name: twisted.test.test_stdio.StandardInputOutputTestCase.testHalfClose -*-
# Copyright (c) 2006 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Main program for the child process run by
L{twisted.test.test_stdio.StandardInputOutputTestCase.testHalfClose} to test
that process transports work with IHalfCloseableProtocols.
"""

import sys

from twisted.internet import stdio, protocol, reactor
from twisted.python import log


class ProducerChild(protocol.Protocol):
    _paused = False

    ???

    def connectionLost(self, reason):
        reactor.stop()


if __name__ == '__main__':
    stdio.StandardIO(ProducerChild())
    reactor.run()
