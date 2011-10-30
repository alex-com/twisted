# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.tap.ftp}.
"""

from twisted.trial.unittest import TestCase

from twisted.tap.ftp import Options
from twisted.python import versions
from twisted.python.filepath import FilePath


class FTPOptionsTestCase(TestCase):
    """
    Tests for the command line option parser used for C{twistd ftp}.
    """

    def test_passwordfileDeprecation(self):
        """
        Test that the --passwordfile option will emit a warning stating that
        said option is deprecated.
        """
        passwd = FilePath(self.mktemp())
        passwd.setContent("usernameTest:passwordTest")
        options = Options()
        self.callDeprecated(
            versions.Version("Twisted", 11, 1, 0),
            options.opt_password_file, passwd.path)
