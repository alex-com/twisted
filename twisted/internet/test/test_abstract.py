# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.internet.abstract}, a collection of APIs for implementing
reactors.
"""

from twisted.trial.unittest import TestCase

from twisted.internet.abstract import isIPv6Address

class IPv6AddressTests(TestCase):
    """
    Tests for L{isIPv6Address}, a function for determining if a particular
    string is an IPv6 address literal.
    """
    def test_empty(self):
        """
        The empty string is not an IPv6 address literal.
        """
        self.assertFalse(isIPv6Address(""))


    def test_colon(self):
        """
        A single C{":"} is not an IPv6 address literal.
        """
        self.assertFalse(isIPv6Address(":"))


    def test_loopback(self):
        """
        C{"::1"} is the IPv6 loopback address literal.
        """
        self.assertTrue(isIPv6Address("::1"))
