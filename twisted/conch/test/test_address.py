# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{SSHTransportAddrress} in ssh/address.py
"""

from twisted.trial import unittest
from twisted.internet.address import IPv4Address
from twisted.internet.test.test_address import AddressTestCaseMixin

from twisted.conch.ssh import address

class SSHTransportAddressTestCase(unittest.TestCase, AddressTestCaseMixin):
    def _stringRepresentation(self, stringFunction):
        """
        The string representation of L{SSHTransportAddress} should be
        "SSHTransportAddress(<stringFunction on address>)".
        """
        addr = self.buildAddress()
        stringValue = stringFunction(addr)
        addressValue = stringFunction(addr.address)
        self.assertEqual(stringValue,
                         "SSHTransportAddress(%s)" % addressValue)

    def buildAddress(self):
        """
        Create an arbitrary new L{SSHTransportAddress}.  A new instance is
        created for each call, but always for the same address.
        """
        return address.SSHTransportAddress(IPv4Address("TCP", "127.0.0.1", 22))

    def buildDifferentAddress(self):
        """
        Like L{buildAddress}, but with a different fixed address.
        """
        return address.SSHTransportAddress(IPv4Address("TCP", "127.0.0.2", 22))
        
