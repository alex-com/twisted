# Copyright (c) 2009-2010 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.internet.abstract.FileDescriptor}.
"""

from twisted.internet.abstract import FileDescriptor
from twisted.trial.unittest import TestCase



class FileDescriptorTests(TestCase):
    def test_writeWithUnicodeRaisesException(self):
        """
        Test that L{twisted.internet.abstract.FileDescriptor.write} doesn't accept unicode data.
        """
        fileDescriptor = FileDescriptor()
        self.assertRaises(TypeError, fileDescriptor.write, u'foo')

    def test_writeSequenceWithUnicodeRaisesException(self):
        """
        Test that L{twisted.internet.abstract.FileDescriptor.writeSequence doesn't accept unicode data.
        See http://twistedmatrix.com/trac/ticket/3896
        """
        fileDescriptor = FileDescriptor()
        self.assertRaises(TypeError, fileDescriptor.writeSequence, [u'foo', u'bar', u'baz'])


