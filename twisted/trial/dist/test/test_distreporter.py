# Copyright (c) 2007 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{distreporter}.
"""

from cStringIO import StringIO

from twisted.trial.dist import distreporter
from twisted.trial.unittest import TestCase
from twisted.trial.reporter import TreeReporter



class DistReporterTestCase(TestCase):
    """
    Some basic test of L{distreporter.DistReporter} behavior.
    """

    def setUp(self):
        self.stream = StringIO()
        self.distReporter = distreporter.DistReporter(
            TreeReporter(self.stream))
        self.test = TestCase()


    def test_startSuccessStop(self):
        """
        Check that output only gets sent to the stream after the test has
        stopped
        """
        self.distReporter.startTest(self.test)
        self.assertEquals(self.stream.tell(), 0)
        self.distReporter.addSuccess(self.test)
        self.assertEquals(self.stream.tell(), 0)
        self.distReporter.stopTest(self.test)
        self.assertNotEquals(self.stream.tell(), 0)


    def test_startErrorStop(self):
        """
        Check that output only gets sent to the stream after the test has
        stopped
        """
        self.distReporter.startTest(self.test)
        self.assertEquals(self.stream.tell(), 0)
        self.distReporter.addSuccess(self.test)
        self.assertEquals(self.stream.tell(), 0)
        self.distReporter.stopTest(self.test)
        self.assertNotEquals(self.stream.tell(), 0)


    def test_forwardedMethod(self):
        """
        Check that calling methods add calls to the running queue of the test.
        """
        self.distReporter.startTest(self.test)
        self.distReporter.addFailure(self.test, "foo")
        self.distReporter.addError(self.test, "bar")
        self.distReporter.addSkip(self.test, "egg")
        self.distReporter.addUnexpectedSuccess(self.test, "spam")
        self.distReporter.addExpectedFailure(self.test, "err", "foo")
        self.assertEquals(len(self.distReporter.running[self.test.id()]), 6)



class UncleanReporterTestCase(TestCase):
    """
    Tests for L{UncleanWarningsReporterWrapper}.
    """

    def test_addError(self):
        """
        Test that C{addError} filters unclean error, and prints warning
        instead.
        """
        stream = StringIO()
        reporter = distreporter.UncleanWarningsReporterWrapper(
            TreeReporter(stream))
        test = TestCase()
        reporter.addError(test, RuntimeError("foo"))
        reporter.addError(test, "unclean")
        errMsg = "Reactor was unclean. Problems!"
        self.assertWarns(UserWarning, errMsg, distreporter.__file__,
                         reporter.addError, test, errMsg)
