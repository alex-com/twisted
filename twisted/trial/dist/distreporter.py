# -*- test-case-name: twisted.trial.dist.test.test_distreporter -*-
#
# Copyright (c) 2007 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
The reporter is not made to support concurent test running, so we will
hold test results in here and only send them to the reporter once the
test is over
"""

import warnings

from zope.interface import implements
from twisted.trial.itrial import IReporter
from twisted.python.components import proxyForInterface



class UncleanWarningsReporterWrapper(proxyForInterface(IReporter)):
    """
    A wrapper for a reporter that converts L{util.DirtyReactorError}s
    to warnings.

    @ivar original: The original reporter.
    """
    implements(IReporter)

    def addError(self, test, error):
        """
        If the error is a L{util.DirtyReactorError}, instead of reporting it as
        a normal error, throw a warning.
        """
        if isinstance(error, str) and error.startswith('Reactor was unclean.'):
            warnings.warn(error)
        else:
            self.original.addError(test, error)



class DistReporter(proxyForInterface(IReporter)):
    """
    See module docstring.
    """

    implements(IReporter)

    def __init__(self, original):
        super(DistReporter, self).__init__(original)
        self.running = {}


    def startTest(self, test):
        """
        Queue test starting.
        """
        self.running[test.id()] = []
        self.running[test.id()].append((self.original.startTest, test))


    def addFailure(self, test, fail):
        """
        Queue adding a failure.
        """
        self.running[test.id()].append((self.original.addFailure,
                                        test, fail))


    def addError(self, test, error):
        """
        Queue error adding.
        """
        self.running[test.id()].append((self.original.addError,
                                        test, error))


    def addSkip(self, test, reason):
        """
        Queue adding a skip.
        """
        self.running[test.id()].append((self.original.addSkip,
                                        test, reason))


    def addUnexpectedSuccess(self, test, todo):
        """
        Queue adding an unexpected success.
        """
        self.running[test.id()].append((self.original.addUnexpectedSuccess,
                                        test, todo))


    def addExpectedFailure(self, test, error, todo):
        """
        Queue adding an unexpected failure.
        """
        self.running[test.id()].append((self.original.addExpectedFailure,
                                        test, error, todo))


    def addSuccess(self, test):
        """
        Queue adding a success.
        """
        self.running[test.id()].append((self.original.addSuccess, test))


    def stopTest(self, test):
        """
        Queue stopping the test, then unroll the queue.
        """
        self.running[test.id()].append((self.original.stopTest, test))
        for step in self.running[test.id()]:
            apply(step[0], step[1:])
        del self.running[test.id()]

