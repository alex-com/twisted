# -*- test-case-name: twisted.test.test_trial.FunctionallyTestTrial -*-

# Copyright (c) 2001-2004 Twisted Matrix Laboratories.
# See LICENSE for details.


from __future__ import nested_scopes

__version__ = "$Revision: 1.17 $"[11:-2]

from twisted.trial.reporter import SKIP, EXPECTED_FAILURE, FAILURE, ERROR, UNEXPECTED_SUCCESS, SUCCESS
from twisted.python import reflect, failure, log, procutils, util as pyutil, compat
from twisted.python.runtime import platformType
from twisted.internet import defer, reactor, protocol, error
from twisted.protocols import loopback
from twisted.spread import banana, jelly
from twisted.trial import unittest, reporter, util, runner, itrial, remote
from twisted.trial.unittest import failUnless, failUnlessIn, failIfIn, failUnlessRaises
from twisted.trial.unittest import failUnlessEqual, failIf, failIfIdentical, failUnlessSubstring
from twisted.trial.unittest import failUnlessSubstring, failIfSubstring, assert_
from twisted.test import trialtest1, trialtest2
from StringIO import StringIO

import zope.interface as zi

from pprint import pprint
import sys, os, os.path as osp
from os.path import join as opj

import cPickle as pickle

    
class LogObserver:
    channels = compat.adict(
        foobar = True
    )
    def __init__(self, outputter=None):
        self.outputter = outputter
        if outputter is None:
            self.outputter = lambda events, k: pyutil.println(''.join(events[k]))

    def setOutputter(self, f):
        if not callable(f):
            raise TypeError, "argument to setOutputter must be a callable object"
        self.outputter = f

    def install(self):
        log.addObserver(self)
        return self

    def remove(self):
        # hack to get around trial's brokeness
        if self in log.theLogPublisher.observers:
            log.removeObserver(self)

    def __call__(self, events):
        for k in events:
            if self.channels.get(k, None):
                #self.outputter(events, k)
                print repr(events)

class UserError(Exception):
    pass

class TestUserMethod(unittest.TestCase):
    def setUp(self):
        self.janitor = util.Janitor()

    def errorfulMethod(self):
        raise UserError, 'i am a user error'

    def errorfulDeferred(self):
        f = None
        try:
            self.errorfulMethod()
        except:
            f = failure.Failure()
        return defer.fail(f)
    
    def testErrorHandling(self):
        """wrapper around user code"""
        umw = runner.UserMethodWrapper(self.errorfulMethod, self.janitor)
        failUnlessRaises(runner.UserMethodError, umw)
        failUnless(umw.errors[0].check(UserError))
        failUnless(umw.endTime > umw.startTime)

    def testDeferredError(self):
        umw = runner.UserMethodWrapper(self.errorfulDeferred, self.janitor)
        failUnlessRaises(runner.UserMethodError, umw)
        failUnless(umw.errors[0].check(UserError))
        failUnless(umw.endTime > umw.startTime)
        

class BogusReporter(reporter.Reporter):
    def __init__(self):
        pass
    stream = log.NullFile()
    tbformat = 'plain'
    bogus = lambda *a, **kw: None
    upDownError = startModule = endModule = bogus
    startClass = endClass = startTest = endTest = cleanupErrors = bogus


class TestMktemp(unittest.TestCase):
    def testMktmp(self):
        tmp = self.mktemp()
        tmp1 = self.mktemp()
        exp = os.path.join('twisted.test.test_trial', 'UtilityTestCase', 'testMktmp')
        self.failIfEqual(tmp, tmp1)
        self.failIf(os.path.exists(exp))


class ChProcessProtoocol(protocol.ProcessProtocol):
    sawTheEnd = None
    def __init__(self, done):
        self.done = done
        self.ended = defer.Deferred()
        self.out, self.err = [], []
        
    def outReceived(self, data):
        self.out.append(data)
##         for line in data.split('\n'):
##             print "LINE: %s" % (line,)

    def errReceived(self, data):
        self.err.append(data)
##         for line in data.split('\n'):
##             sys.stderr.write("\n\tchild stderr: %s" % (line,))
##             sys.stderr.flush()

    def processEnded(self, status):
        lines = ''.join(self.out).split('\n')
        lines.reverse()
        for line in lines:
            if (line.find("Ran") != -1) and (line.find("tests") != -1):
                self.done.callback(self)
                return
        self.done.errback(status)

class SpawningMixin:
    def spawnChild(self, args):
        env = {}
        env['PATH'] = os.environ.get('PATH', '')
        env["PYTHONPATH"] = os.environ.get("PYTHONPATH", "")
        
        done = defer.Deferred()
        self.cpp = ChProcessProtoocol(done)
        self.process = procutils.spawnPythonProcess(self.cpp, args, env, packages=('twisted',))
        return done


class FunctionalTest(unittest.TestCase, SpawningMixin):
    """functionally test trial in cases where it would be too difficult to test in the
       same process
    """
    cpp = None

    def setUpClass(self):
        locs = procutils.which('trial')
        if locs:
            self.trial = locs[0]
        elif platformType == "win32":
            installedPath = os.path.join(os.path.dirname(sys.executable), "scripts", "trial.py")
            if os.path.exists(installedPath):
                self.trial = installedPath
            else:
                import twisted
                sibPath = pyutil.sibpath(twisted.__file__, "bin")
                sibPath = os.path.join(sibPath, "trial")
                if os.path.exists(sibPath):
                    self.trial = sibPath
                else:
                    raise RuntimeError, "can't find 'trial' in PATH"
        else:
            raise RuntimeError, "can't find 'trial' in PATH"
        self.args = ['python', self.trial, "-o"]

    def tearDown(self):
        pass

    def _failIfIn(self, astring):
        out = ''.join(self.cpp.out)
        failIfSubstring(astring, out,
                     "%r not found in child process output:\n\n%s" % (astring,
                        '\n'.join(['\tOUT: %s' % line for line in out.split('\n')])))

    def _failUnlessIn(self, astring):
        out = ''.join(self.cpp.out)
        failUnlessSubstring(astring, out,
                     "%r not found in child process output:\n\n%s" % (astring,
                        '\n'.join(['\tOUT: %s' % line for line in out.split('\n')])))

    def testBrokenSetUp(self):
        args = self.args + ['twisted.test.trialtest1.TestFailureInSetUp']

        def _cb(cpp):
            self._failUnlessIn("[ERROR]: test_foo")
            self._failIfIn(trialtest1.TEAR_DOWN_MSG) # if setUp is broken, tearDown should not run
        return self.spawnChild(args).addCallback(_cb)
    
    def testBrokenTearDown(self):
        args = self.args + ['twisted.test.trialtest1.TestFailureInTearDown']

        def _cb(cpp):
            self._failUnlessIn("[ERROR]: test_foo")
        return self.spawnChild(args).addCallback(_cb)
        
    def testBrokenSetUpClass(self):
        args = self.args + ['twisted.test.trialtest1.TestFailureInSetUpClass']
        
        def _cb(cpp):
            # if setUp is broken, tearDownClass should not run
            #
            self._failUnlessIn(reporter.SET_UP_CLASS_WARN)
            self._failIfIn(trialtest1.TEAR_DOWN_CLASS_MSG)
        return self.spawnChild(args).addCallback(_cb)

    def testBrokenTearDownClass(self):
        args = self.args + ['twisted.test.trialtest1.TestFailureInTearDownClass']

        def _cb(cpp):
            self._failUnlessIn(reporter.TEAR_DOWN_CLASS_WARN)
        return self.spawnChild(args).addCallback(_cb)

    def testHiddenException(self):
        args = self.args + ['twisted.test.trialtest1.DemoTest.testHiddenException']
        def _cb(cpp):
            self._failUnlessIn(trialtest1.HIDDEN_EXCEPTION_MSG)
        return self.spawnChild(args).addCallback(_cb)

    def testLeftoverSockets(self):
        args = self.args + ['twisted.test.trialtest1.ReactorCleanupTests.test_socketsLeftOpen']
        def _cb(cpp):
            self._failUnlessIn(util.DIRTY_REACTOR_MSG)
            # when it becomes an error to leave selectables in the reactor
            # uncomment the following line: 
            #self._failUnlessIn(reporter.UNCLEAN_REACTOR_WARN)
            #self._failUnlessIn("[ERROR]: test_socketsLeftOpen")
        return self.spawnChild(args).addCallback(_cb)

    def testLeftoverPendingCalls(self):
        args = self.args + ['twisted.test.trialtest1.ReactorCleanupTests.test_leftoverPendingCalls']

        def _cb(cpp):
            self._failUnlessIn("[ERROR]: test_leftoverPendingCalls")
            self._failUnlessIn(util.PENDING_TIMED_CALLS_MSG)
        return self.spawnChild(args).addCallback(_cb)
    
    def testPyUnitSupport(self):
        args = self.args + ['twisted.test.trialtest2.TestPyUnitSupport']
        def _cb(cpp):
            for msg in trialtest2.MESSAGES:
                self._failUnlessIn(msg)
        return self.spawnChild(args).addCallback(_cb)

    def testTests(self):
        args = self.args + ['twisted.test.trialtest3.TestTests']
        def _cb(cpp):
            self._failUnlessIn("[OK]")
            self._failUnlessIn("PASSED")
        return self.spawnChild(args).addCallback(_cb)

    def testBenchmark(self):
        args = self.args + ['twisted.test.trialtest3.TestBenchmark']
        def _cb(cpp):
            self._failUnlessIn("[OK]")
            self._failUnlessIn("PASSED")
        return self.spawnChild(args).addCallback(_cb)

    def testClassTimeoutAttribute(self):
        args = self.args + ['twisted.test.trialtest3.TestClassTimeoutAttribute']
        def _cb(cpp):
            self._failUnlessIn("[OK]")
            self._failUnlessIn("PASSED")
        return self.spawnChild(args).addCallback(_cb)

    def testCorrectNumberTestReporting(self):
        """make sure trial reports the correct number of tests run (issue 770)"""
        args = self.args + ['twisted.test.trialtest4']
        def _cb(cpp):
            self._failUnlessIn("Ran 1 tests in")
        return self.spawnChild(args).addCallback(_cb)
        
FunctionalTest.timeout = 30.0
