# -*- test-case-name: twisted.trial.test.test_trial -*-
#
# Copyright (c) 2001-2004 Twisted Matrix Laboratories.
# See LICENSE for details.
#
# Maintainer: Jonathan Lange <jml@twistedmatrix.com>

"""Defines classes that handle the results of tests.

API Stability: Unstable
"""

import sys, types, os
import time
import warnings

from twisted.python import reflect, failure, log
from twisted.internet import defer
from twisted.trial import itrial, util
import zope.interface as zi

pyunit = __import__('unittest')


class BrokenTestCaseWarning(Warning):
    """emitted as a warning when an exception occurs in one of
    setUp, tearDown, setUpClass, or tearDownClass"""


class TestResult(pyunit.TestResult, object):
    def __init__(self):
        super(TestResult, self).__init__()
        self.skips = []
        self.expectedFailures = []
        self.unexpectedSuccesses = []
        self.successes = []
        self._timings = []

    def _somethingStarted(self):
        """Note that something has started."""
        self._timings.append(time.time())

    def _somethingStopped(self):
        """Note that something has finished, and get back its duration.
        
        The value is also stored in self._last_time to ease multiple 
        accesses.
        """
        self._last_time = time.time() - self._timings.pop()
        return self._last_time

    def startTest(self, test):
        super(TestResult, self).startTest(test)
        self._somethingStarted()

    def stopTest(self, method):
        super(TestResult, self).stopTest(method)
        self._somethingStopped()

    def addFailure(self, test, fail):
        if isinstance(fail, tuple):
            fail = failure.Failure(*fail)
        self.failures.append((test, fail))

    def addError(self, test, error):
        if isinstance(error, tuple):
            error = failure.Failure(*error)
        self.errors.append((test, error))

    def addSkip(self, test, reason):
        self.skips.append((test, reason))

    def addUnexpectedSuccess(self, test, todo):
        self.unexpectedSuccesses.append((test, todo))

    def addExpectedFailure(self, test, error, todo):
        self.expectedFailures.append((test, error, todo))

    def addSuccess(self, test):
        self.successes.append((test,))

    def upDownError(self, method, error, warn, printStatus):
        pass

    def cleanupErrors(self, errs):
        pass

    def startTrial(self, count):
        pass

    def endTrial(self, suite):
        pass
    
    def startSuite(self, name):
        pass

    def endSuite(self, name):
        pass


class Reporter(TestResult):
    zi.implements(itrial.IReporter)

    separator = '-' * 79
    doubleSeparator = '=' * 79

    def __init__(self, stream=sys.stdout, tbformat='default', args=None,
                 realtime=False):
        super(Reporter, self).__init__()
        self.stream = stream
        self.tbformat = tbformat
        self.args = args
        self.realtime = realtime
        self.couldNotImport = []

    def startTest(self, test):
        super(Reporter, self).startTest(test)
        self._somethingStarted()

    def reportImportError(self, name, exc):
        self.couldNotImport.append((name, exc))

    def addFailure(self, test, fail):
        super(Reporter, self).addFailure(test, fail)
        if self.realtime:
            self.write(self._formatFailureTraceback(fail))

    def addError(self, test, error):
        super(Reporter, self).addError(test, error)
        if self.realtime:
            self.write(self._formatFailureTraceback(error))

    def write(self, format, *args):
        s = str(format)
        assert isinstance(s, type(''))
        if args:
            self.stream.write(s % args)
        else:
            self.stream.write(s)
        self.stream.flush()

    def writeln(self, format, *args):
        self.write(format, *args)
        self.write('\n')

    def upDownError(self, method, error, warn, printStatus):
        super(Reporter, self).upDownError(method, error, warn, printStatus)
        if warn:
            tbStr = self._formatFailureTraceback(error)
            log.msg(tbStr)
            msg = ("caught exception in %s, your TestCase is broken\n\n%s"
                   % (method, tbStr))
            warnings.warn(msg, BrokenTestCaseWarning, stacklevel=2)

    def cleanupErrors(self, errs):
        super(Reporter, self).cleanupErrors(errs)
        warnings.warn("%s\n%s" % ("REACTOR UNCLEAN! traceback(s) follow: ",
                                  self._formatFailureTraceback(errs)),
                      BrokenTestCaseWarning)

    def _trimFrame(self, fail):
        if len(fail.frames) < 3:
            return fail.frames
        oldFrames = fail.frames[:]
        fail.frames = fail.frames[2:]
        f = fail.frames[-1]
        if (f[0].startswith('fail')
            and os.path.splitext(os.path.basename(f[1]))[0] == 'unittest'):
            fail.frames = fail.frames[:-1]
        return oldFrames

    def _formatFailureTraceback(self, fail):
        if isinstance(fail, str):
            return fail.rstrip() + '\n'
        oldFrames = self._trimFrame(fail)
        result = fail.getTraceback(detail=self.tbformat, elideFrameworkCode=True)
        if self.tbformat == 'default':
            # Apparently trial's tests don't like the 'Traceback:' line.
            result = '\n'.join(result.split('\n')[1:])
        fail.frames = oldFrames
        return result

    def printExpectedFailures(self):
        for test, error, todo in self.expectedFailures:
            self.writeln(self.doubleSeparator)
            self.writeln('%s: %s' % ("[TODO]", test.id()))
            self.writeln('')
            self.writeln(todo.reason)
            self.write(self._formatFailureTraceback(error))

    def printErrorList(self, flavour, errors):
        for test, error in errors:
            self.writeln(self.doubleSeparator)
            self.writeln('%s: %s' % (flavour, test.id()))
            self.writeln('')
            self.write(self._formatFailureTraceback(error))

    def printUnexpectedSuccesses(self):
        for test, todo in self.unexpectedSuccesses:
            self.writeln(self.doubleSeparator)
            self.writeln('%s: %s' % ('[SUCCESS!?!]', test.id()))
            self.writeln('')
            self.writeln('Reason: %r' % (todo.reason))
            if todo.errors:
                self.writeln('Expected errors: %s' % (', '.join(todo.errors),))
            self.writeln('')

    def printImportErrors(self):
        for name, error in self.couldNotImport:
            self.writeln(self.doubleSeparator)
            self.writeln('IMPORT ERROR:')
            self.writeln('')
            self.writeln('Could not import: %s' % (name,))
            if isinstance(error, failure.Failure):
                what = self._formatFailureTraceback(error)
            elif type(error) == types.TupleType:
                what = error.args[0]
            else:
                what = "%s\n" % error
            self.writeln(what)

    def printErrors(self):
        self.printErrorList("[SKIPPED]", self.skips)
        self.printExpectedFailures()
        self.printErrorList("[FAIL]", self.failures)
        self.printErrorList("[ERROR]", self.errors)
        self.printUnexpectedSuccesses()
        self.printImportErrors()

    def _reportStatus(self, tsuite):
        summaries = []
        for stat in ("skips", "expectedFailures", "failures", "errors",
                     "unexpectedSuccesses", "successes"):
            num = len(getattr(self, stat))
            if num:
                summaries.append('%s=%d' % (stat, num))
        summary = (summaries and ' ('+', '.join(summaries)+')') or ''
        if not self.wasSuccessful():
            status = "FAILED"
        else:
            status = "PASSED"
        self.write("%s%s\n", status, summary)

    def startTrial(self, count):
        """Inform the user how many tests are being run."""
        super(Reporter, self).startTrial(count)
        self.write("Running %d tests.\n", count)
        self._somethingStarted()

    def endTrial(self, suite):
        super(Reporter, self).endTrial(suite)
        self.write("\n")
        self.printErrors()
        self.write("%s\n" % self.separator)
        self.write('Ran %d tests in %.3fs\n', self.testsRun,
                   self._somethingStopped())
        self.write('\n')
        self._reportStatus(suite)


class MinimalReporter(Reporter):
    def endTrial(self, suite):
        numTests = self.testsRun
        t = (self._somethingStopped(), numTests, numTests,
             len(self.couldNotImport), len(self.errors),
             len(self.failures), len(self.skips))
        self.stream.write(' '.join(map(str,t))+'\n')


class TextReporter(Reporter):
    def addSuccess(self, test):
        super(TextReporter, self).addSuccess(test)
        self.write('.')

    def addError(self, *args):
        super(TextReporter, self).addError(*args)
        self.write('E')

    def addFailure(self, *args):
        super(TextReporter, self).addFailure(*args)
        self.write('F')

    def addSkip(self, *args):
        super(TextReporter, self).addSkip(*args)
        self.write('S')

    def addExpectedFailure(self, *args):
        super(TextReporter, self).addExpectedFailure(*args)
        self.write('T')

    def addUnexpectedSuccess(self, *args):
        super(TextReporter, self).addUnexpectedSuccess(*args)
        self.write('!')


class VerboseTextReporter(Reporter):
    # This is actually the bwverbose option

    def startTest(self, tm):
        self.write('%s ... ', tm.id())
        super(VerboseTextReporter, self).startTest(tm)
        
    def addSuccess(self, test):
        super(VerboseTextReporter, self).addSuccess(test)
        self.write('[OK]')

    def addError(self, *args):
        super(VerboseTextReporter, self).addError(*args)
        self.write('[ERROR]')

    def addFailure(self, *args):
        super(VerboseTextReporter, self).addFailure(*args)
        self.write('[FAILURE]')

    def addSkip(self, *args):
        super(VerboseTextReporter, self).addSkip(*args)
        self.write('[SKIPPED]')

    def addExpectedFailure(self, *args):
        super(VerboseTextReporter, self).addExpectedFailure(*args)
        self.write('[TODO]')

    def addUnexpectedSuccess(self, *args):
        super(VerboseTextReporter, self).addUnexpectedSuccess(*args)
        self.write('[SUCCESS!?!]')

    def stopTest(self, test):
        super(VerboseTextReporter, self).stopTest(test)
        self.write('\n')


class TimingTextReporter(VerboseTextReporter):
    def stopTest(self, method):
        self.write("(%.03f secs)\n" % self._last_time)
        super(TimingTextReporter, self).stopTest(method)


class TreeReporter(Reporter):
    currentLine = ''
    indent = '  '
    columns = 79

    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37

    def __init__(self, stream=sys.stdout, tbformat='default', args=None,
                 realtime=False):
        super(TreeReporter, self).__init__(stream, tbformat, args, realtime)
        self.indentLevel = 0

    def addSuccess(self, test):
        super(TreeReporter, self).addSuccess(test)
        self.endLine('[OK]', self.GREEN)

    def addError(self, *args):
        super(TreeReporter, self).addError(*args)
        self.endLine('[ERROR]', self.RED)

    def addFailure(self, *args):
        super(TreeReporter, self).addFailure(*args)
        self.endLine('[FAIL]', self.RED)

    def addSkip(self, *args):
        super(TreeReporter, self).addSkip(*args)
        self.endLine('[SKIPPED]', self.BLUE)

    def addExpectedFailure(self, *args):
        super(TreeReporter, self).addExpectedFailure(*args)
        self.endLine('[TODO]', self.BLUE)

    def addUnexpectedSuccess(self, *args):
        super(TreeReporter, self).addUnexpectedSuccess(*args)
        self.endLine('[SUCCESS!?!]', self.RED)

    def write(self, format, *args):
        if args:
            format = format % args
        self.currentLine = format
        super(TreeReporter, self).write(self.currentLine)

    def startSuite(self, name):
        self.indentLevel += 1
        self.write('%s%s\n' % (self.indent * self.indentLevel, name))

    def endSuite(self, name):
        self.indentLevel -= 1

    def cleanupErrors(self, errs):
        self.write(self.color('    cleanup errors', self.RED))
        self.endLine('[ERROR]', self.RED)
        super(TreeReporter, self).cleanupErrors(errs)

    def upDownError(self, method, error, warn, printStatus):
        self.write(self.color("  %s" % method, self.RED))
        if printStatus:
            self.endLine(['ERROR'], self.RED)
        super(TreeReporter, self).upDownError(method, error, warn, printStatus)
        
    def startTest(self, method):
        self.write('%s%s ... ' % (self.indent * (self.indentLevel + 1),
                                  method.shortDescription()))
        super(TreeReporter, self).startTest(method)

    def color(self, text, color):
        return '%s%s;1m%s%s0m' % ('\x1b[', color, text, '\x1b[')

    def endLine(self, message, color):
        spaces = ' ' * (self.columns - len(self.currentLine) - len(message))
        super(TreeReporter, self).write(spaces)
        super(TreeReporter, self).write("%s\n" % (self.color(message, color),))
