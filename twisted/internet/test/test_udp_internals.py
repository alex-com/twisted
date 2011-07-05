# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for the internal implementation details of L{twisted.internet.udp}.
"""

import socket

from twisted.trial import unittest
from twisted.test.proto_helpers import StringUDPSocket
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.udp import Port
from twisted.python.runtime import platformType

if platformType == 'win32':
    from errno import WSAEWOULDBLOCK as EWOULDBLOCK
    from errno import WSAECONNREFUSED as ECONNREFUSED
else:
    from errno import EWOULDBLOCK
    from errno import ECONNREFUSED



class KeepReads(DatagramProtocol):
    """
    Accumulate reads in a list.
    """

    def __init__(self):
        self.reads = []


    def datagramReceived(self, data, addr):
        self.reads.append(data)



class ErrorsTestCase(unittest.TestCase):
    """
    Error handling tests for C{udp.Port}.
    """

    def test_socketReadNormal(self):
        """
        Socket reads with some good data followed by a socket error which is
        "known" (i.e. in the errno module) cause reading to stop.
        """
        protocol = KeepReads()
        port = Port(None, protocol)

        # Normal result, no errors
        port.socket = StringUDPSocket(
            ["result", "123", socket.error(EWOULDBLOCK), "456",
             socket.error(EWOULDBLOCK)])
        port.doRead()
        # Read stops on error:
        self.assertEqual(protocol.reads, ["result", "123"])
        port.doRead()
        self.assertEqual(protocol.reads, ["result", "123", "456"])


    def test_readImmediateError(self):
        """
        Socket reads with an immediate connection refusal are ignored, and
        reading stops.
        """
        protocol = KeepReads()
        port = Port(None, protocol)

        # Try an immediate "connection refused"
        port.socket = StringUDPSocket(["a", socket.error(ECONNREFUSED), "b",
                                       socket.error(EWOULDBLOCK)])
        port.doRead()
        # Read stops on error:
        self.assertEqual(protocol.reads, ["a"])
        # Read again:
        port.doRead()
        self.assertEqual(protocol.reads, ["a", "b"])


    def test_readUnknownError(self):
        """
        Socket reads with an unknown socket error (i.e. one not in the errno
        module) are raised.
        """
        protocol = KeepReads()
        port = Port(None, protocol)

        # Some good data, followed by an unknown error
        port.socket = StringUDPSocket(["good", socket.error(1337 ** 20)])
        self.assertRaises(socket.error, port.doRead)
        self.assertEqual(protocol.reads, ["good"])
