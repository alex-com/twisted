# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Test for distrial options management.
"""

import os, sys, random, gc

from twisted.trial.unittest import TestCase
from twisted.trial.dist.options import DistOptions



class DistOptionsTestCase(TestCase):
    """
    Tests for L{DistOptions}.
    """

    def setUp(self):
        """
        Build an option object to be used in the tests.
        """
        self.options = DistOptions()


    def test_opt_testmodule(self):
        """
        Test the testmodule option.
        """
        slavetrialPath = __file__
        if os.path.splitext(slavetrialPath)[1] != ".py":
            # it doesn't handle pyc files
            slavetrialPath = "%s.py" % (os.path.splitext(slavetrialPath)[0],)
        self.options.opt_testmodule(slavetrialPath)
        self.assertEquals([slavetrialPath], list(self.options["tests"]))


    def test_opt_recursionlimit(self):
        """
        Test the recursion limit option.
        """
        limit = sys.getrecursionlimit()
        try:
            self.options.opt_recursionlimit(str(2 * limit))
            self.assertEquals(sys.getrecursionlimit(), 2 * limit)
            self.options.opt_recursionlimit(str(limit))
            self.assertEquals(sys.getrecursionlimit(), limit)
        finally:
            sys.setrecursionlimit(limit)


    def test_opt_random(self):
        """
        Test the random option.
        """
        randint = random.randint(0, 1000000)
        self.options.opt_random(str(randint))
        self.assertEquals(self.options["random"], randint)


    def test_getSlaveArguments(self):
        """
        Test getSlaveArguments output: it should discard some options and
        forward others.
        """
        limit = sys.getrecursionlimit()
        gcEnabled = gc.isenabled()
        try:
            self.options.parseOptions(["--recursionlimit", "2000", "--random",
                                       "4", "--disablegc"])
            args = self.options.getSlaveArguments()
            self.assertIn("--disablegc", args)
            args.remove("--disablegc")
            self.assertEquals(["--recursionlimit", "2000"], args)
        finally:
            sys.setrecursionlimit(limit)
            if gcEnabled:
                gc.enable()
