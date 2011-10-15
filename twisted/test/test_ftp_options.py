# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.tap.ftp}.
"""

from twisted.trial.unittest import TestCase

from twisted.python.usage import UsageError
from twisted.tap.ftp import Options, makeService
from twisted.python import deprecate, versions
from twisted.python.filepath import FilePath


class FTPOptionsTestCase(TestCase):
    """
    Tests for the command line option parser used for I{twistd mail}.
    """
            
    def testPasswordfileDeprecation(self):
        """
        Test that the --passwordfile option will emit a correct warning.
        """
        passwd = FilePath(self.mktemp())
        passwd.setContent("usernameTest:passwordTest")
        options = Options()
        self.callDeprecated(
            versions.Version("Twisted", 11, 1, 0),
            options.opt_password_file, passwd.path)