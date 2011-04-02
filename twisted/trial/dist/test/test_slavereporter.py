# Copyright (c) 2007 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.trial.dist.slavereporter}.
"""

from twisted.python.failure import Failure
from twisted.trial.unittest import TestCase, Todo
from twisted.trial.dist.slavereporter import SlaveReporter
from twisted.trial.dist import mastercommands



class SlaveReporterTestCase(TestCase):
    """
    Tests for L{SlaveReporter}.
    """

    def setUp(self):
        class FakeAMProtocol:
            id = 0
            lastCall = None
            def callRemote(self, command, **kwargs):
                self.lastCall = command
        self.fakeAMProtocol = FakeAMProtocol()
        self.slaveReporter = SlaveReporter(self.fakeAMProtocol)
        self.test = TestCase()


    def test_addSuccess(self):
        """
        Test that adding a success sends the right command to the AMP protocol.
        """
        self.slaveReporter.addSuccess(self.test)
        self.assertEquals(self.fakeAMProtocol.lastCall,
                          mastercommands.AddSuccess)


    def test_addError(self):
        """
        Test that adding an error sends the right command to the AMP protocol.
        """
        self.slaveReporter.addError(self.test, Failure(RuntimeError('error')))
        self.assertEquals(self.fakeAMProtocol.lastCall,
                          mastercommands.AddError)


    def test_addErrorTuple(self):
        """
        Adding an error as a C{sys.exc_info}-style tuple sends an
        L{AddError} message.
        """
        self.slaveReporter.addError(
            self.test, (RuntimeError, RuntimeError('error'), None))
        self.assertEquals(self.fakeAMProtocol.lastCall,
                          mastercommands.AddError)


    def test_addFailure(self):
        """
        Test that adding a failure sends the right command to the AMP protocol.
        """
        self.slaveReporter.addFailure(self.test, Failure(RuntimeError('fail')))
        self.assertEquals(self.fakeAMProtocol.lastCall,
                          mastercommands.AddFailure)


    def test_addFailureTuple(self):
        """
        Adding a failure as a C{sys.exc_info}-style tuple sends an
        L{AddFailure} message.
        """
        self.slaveReporter.addFailure(
            self.test, (RuntimeError, RuntimeError('fail'), None))
        self.assertEquals(self.fakeAMProtocol.lastCall,
                          mastercommands.AddFailure)


    def test_addSkip(self):
        """
        Test that adding a skip sends the right command to the AMP protocol.
        """
        self.slaveReporter.addSkip(self.test, 'reason')
        self.assertEquals(self.fakeAMProtocol.lastCall,
                          mastercommands.AddSkip)


    def test_addExpectedFailure(self):
        """
        Test that adding an expected failure sends the right command to the AMP
        protocol.
        """
        self.slaveReporter.addExpectedFailure(
            self.test, Failure(RuntimeError('error')), Todo('todo'))
        self.assertEquals(self.fakeAMProtocol.lastCall,
                          mastercommands.AddExpectedFailure)


    def test_addUnexpectedSuccess(self):
        """
        Test that adding an unexpected success sends the right command to the
        AMP protocol.
        """
        self.slaveReporter.addUnexpectedSuccess(self.test, Todo('todo'))
        self.assertEquals(self.fakeAMProtocol.lastCall,
                          mastercommands.AddUnexpectedSuccess)
