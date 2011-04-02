# -*- test-case-name: twisted.trial.dist.test.test_slavereporter -*-
#
# Copyright (c) 2007 Twisted Matrix Laboratories.
# See LICENSE for details.

from twisted.python.failure import Failure
from twisted.trial.reporter import TestResult
from twisted.trial.dist import mastercommands



class SlaveReporter(TestResult):
    """
    Reporter for disttrial's slaves. We send things not through a stream, but
    through an L{AMP} protocol's L{callRemote} method
    """

    def __init__(self, amprotocol):
        super(SlaveReporter, self).__init__()
        self.amprotocol = amprotocol

    def _getFailure(self, error):
        """
        Convert a C{sys.exc_info()}-style tuple to a L{Failure}, if necessary.
        """
        if isinstance(error, tuple):
            return Failure(error[1], error[0], error[2])
        return error

    def addSuccess(self, test):
        """
        Send a Success over.
        """
        super(SlaveReporter, self).addSuccess(test)
        self.amprotocol.callRemote(mastercommands.AddSuccess,
                                   testName=test.id())


    def addError(self, test, error):
        """
        Send an error over.
        """
        super(SlaveReporter, self).addError(test, error)
        failure = self._getFailure(error)
        self.amprotocol.callRemote(mastercommands.AddError, testName=test.id(),
                                   error=failure.getErrorMessage())


    def addFailure(self, test, fail):
        """
        Send a Failure over.
        """
        super(SlaveReporter, self).addFailure(test, fail)
        reason = self._getFailure(fail)
        self.amprotocol.callRemote(mastercommands.AddFailure,
                                   testName=test.id(),
                                   fail=reason.getErrorMessage())


    def addSkip(self, test, reason):
        """
        Send a skip over.
        """
        super(SlaveReporter, self).addSkip(test, reason)
        self.amprotocol.callRemote(mastercommands.AddSkip,
                                   testName=test.id(), reason=str(reason))


    def addExpectedFailure(self, test, error, todo):
        """
        Send an expected failure over.
        """
        super(SlaveReporter, self).addExpectedFailure(test, error, todo)
        self.amprotocol.callRemote(mastercommands.AddExpectedFailure,
                                   testName=test.id(),
                                   error=error.getErrorMessage(),
                                   todo=todo.reason)


    def addUnexpectedSuccess(self, test, todo):
        """
        Send an unexpected success over.
        """
        super(SlaveReporter, self).addUnexpectedSuccess(test, todo)
        self.amprotocol.callRemote(mastercommands.AddUnexpectedSuccess,
                                   testName=test.id(), todo=todo.reason)


    def printSummary(self):
        """
        _Don't_ print a summary
        """
        return
