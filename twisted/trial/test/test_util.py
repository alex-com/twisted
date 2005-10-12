# -*- test-case-name: twisted.trial.test.test_util -*-
from twisted.python import failure, log
from twisted.python.runtime import platformType
from twisted.internet import defer, reactor, threads, interfaces
from twisted.trial import unittest, util, runner
from twisted.trial.test import packages

import sys, os, time, signal

class UserError(Exception):
    pass

class TestUserMethod(unittest.TestCase):
    def setUp(self):
        self.janitor = util._Janitor()

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
        umw = util.UserMethodWrapper(self.errorfulMethod, self.janitor)
        self.failUnlessRaises(util.UserMethodError, umw)
        self.failUnless(umw.errors[0].check(UserError))
        self.failUnless(umw.endTime >= umw.startTime)

    def testDeferredError(self):
        umw = util.UserMethodWrapper(self.errorfulDeferred, self.janitor)
        self.failUnlessRaises(util.UserMethodError, umw)
        self.failUnless(umw.errors[0].check(UserError))
        self.failUnless(umw.endTime >= umw.startTime)


class WaitReentrancyTest(unittest.TestCase):

    if interfaces.IReactorThreads(reactor, None) is None:
        skip = ("This test probably doesn't really need threads "
                "but hell if I can figure out how to rewrite it "
                "without them.  Skipping in the absence of "
                "thread-support.")

    def _returnedDeferredThenWait(self):
        def threadedOperation():
            time.sleep(0.1)
            return "Beginning"
        d = threads.deferToThread(threadedOperation)
        return d.addCallback(self._cbDoWait)

    def _cbDoWait(self, result):
        self.assertEquals(result, "Beginning")
        d = defer.succeed("End")
        self.assertEquals(util.wait(d), "End")

    def testReturnedDeferredThenWait(self):
        d = self._returnedDeferredThenWait()
        self.assertRaises(util.WaitIsNotReentrantError, util.wait, d)

    def _reentrantWait(self):
        def threadedOperation(n):
            time.sleep(n)
            return n
        d1 = threads.deferToThread(threadedOperation, 0.125)
        d2 = threads.deferToThread(threadedOperation, 0.250)
        d1.addCallback(lambda ignored: util.wait(d2))
        util.wait(d1)

    def testReentrantWait(self):
        self.assertRaises(util.WaitIsNotReentrantError, self._reentrantWait)


class TestWait2(unittest.TestCase):
    NUM_FAILURES = 3

    def _generateFailure(self):
        try:
            raise RuntimeError, "i am a complete and utter failure"
        except RuntimeError:
            return failure.Failure()

    def _errorfulMethod(self):
        L = [self._generateFailure() for x in xrange(self.NUM_FAILURES)]
        raise util.MultiError(L)

    def testMultiError(self):
        self.assertRaises(util.MultiError, self._errorfulMethod)
        try:
            self._errorfulMethod()
        except util.MultiError, e:
            self.assert_(hasattr(e, 'failures'))
            self.assertEqual(len(e.failures), self.NUM_FAILURES)
            for f in e.failures:
                self.assert_(f.check(RuntimeError))

    def testMultiErrorAsFailure(self):
        self.assertRaises(util.MultiError, self._errorfulMethod)
        try:
            self._errorfulMethod()
        except util.MultiError:
            f = failure.Failure()
            self.assert_(hasattr(f, 'value'))
            self.assert_(hasattr(f.value, 'failures'))
            self.assertEqual(len(f.value.failures), self.NUM_FAILURES)
            for f in f.value.failures:
                self.assert_(f.check(RuntimeError))


class TestMktemp(unittest.TestCase):
    def testMktmp(self):
        tmp = self.mktemp()
        tmp1 = self.mktemp()
        exp = os.path.join('twisted.trial.test.test_trial', 'UtilityTestCase', 'testMktmp')
        self.failIfEqual(tmp, tmp1)
        self.failIf(os.path.exists(exp))


class TestWaitInterrupt(unittest.TestCase):

    def raiseKeyInt(self, ignored):
        # XXX Abstraction violation, I suppose.  However: signals are
        # unreliable, so using them to simulate a KeyboardInterrupt
        # would be sketchy too; os.kill() is not available on Windows,
        # so we can't use that and let this run on Win32; raising
        # KeyboardInterrupt itself is wholely unrealistic, as the
        # reactor would normally block SIGINT for its own purposes and
        # not allow a KeyboardInterrupt to happen at all!
        if interfaces.IReactorThreads.providedBy(reactor):
            reactor.callInThread(reactor.sigInt)
        else:
            reactor.callLater(0, reactor.sigInt)
        return defer.Deferred()

    def setUp(self):
        self.shutdownCalled = False

    def testKeyboardInterrupt(self):
        # Test the KeyboardInterrupt is *not* caught by wait -- we
        # want to allow users to Ctrl-C test runs.  And the use of the
        # useWaitError should not matter in this case.
        d = defer.Deferred()
        d.addCallback(self.raiseKeyInt)
        reactor.callLater(0, d.callback, None)
        self.assertRaises(KeyboardInterrupt, util.wait, d, useWaitError=False)

    def _shutdownCalled(self):
        self.shutdownCalled = True

    def test_interruptDoesntShutdown(self):
        reactor.addSystemEventTrigger('after', 'shutdown',
                                      self._shutdownCalled)
        d = defer.Deferred()
        d.addCallback(self.raiseKeyInt)
        reactor.callLater(0, d.callback, None)
        try:
            util.wait(d, useWaitError=False)
        except KeyboardInterrupt:
            self.failIf(self.shutdownCalled,
                        "System shutdown triggered")
        else:
            self.fail("KeyboardInterrupt wasn't raised")

 
# glyph's contributed test
# http://twistedmatrix.com/bugs/file317/failing.py

class FakeException(Exception):
    pass

def die():
    try:
        raise FakeException()
    except:
        log.err()

class MyTest(unittest.TestCase):
    def testFlushAfterWait(self):
        die()
        util.wait(defer.succeed(''))
        log.flushErrors(FakeException)

    def testFlushByItself(self):
        die()
        log.flushErrors(FakeException)


class TestIntrospection(unittest.TestCase):
    def test_containers(self):
        import suppression
        parents = util.getPythonContainers(
            suppression.TestSuppression2.testSuppressModule)
        expected = [ suppression.TestSuppression2,
                     suppression ]
        for a, b in zip(parents, expected):
            self.failUnlessEqual(a, b)
                     

class TestFindObject(unittest.TestCase):
    def setUp(self):
        packages.setUp('_TestFindObject')
        self.oldPath = sys.path[:]
        sys.path.append('_TestFindObject')

    def tearDown(self):
        importedModules = ['goodpackage',
                           'goodpackage.test_sample',
                           'package', 'package2',
                           'package.test_bad_module',
                           'package2.test_module',
                           'sample']
        for moduleName in importedModules:
            if sys.modules.has_key(moduleName):
                del sys.modules[moduleName]
        sys.path = self.oldPath
        packages.tearDown('_TestFindObject')

    def test_importPackage(self):
        package1 = util.findObject('package')
        import package as package2
        self.failUnlessEqual(package1, (True, package2))

    def test_importModule(self):
        test_sample2 = util.findObject('goodpackage.test_sample')
        from goodpackage import test_sample
        self.failUnlessEqual((True, test_sample), test_sample2)

    def test_importError(self):
        self.failUnlessRaises(ZeroDivisionError,
                              util.findObject, 'package.test_bad_module')

    def test_sophisticatedImportError(self):
        self.failUnlessRaises(ImportError,
                              util.findObject, 'package2.test_module')

    def test_importNonexistentPackage(self):
        self.failUnlessEqual(util.findObject('doesntexist')[0], False)

    def test_findNonexistentModule(self):
        self.failUnlessEqual(util.findObject('package.doesntexist')[0], False)

    def test_findNonexistentObject(self):
        self.failUnlessEqual(util.findObject(
            'goodpackage.test_sample.doesnt')[0], False)
        self.failUnlessEqual(util.findObject(
            'goodpackage.test_sample.AlphabetTest.doesntexist')[0], False)

    def test_findObjectExist(self):
        alpha1 = util.findObject('goodpackage.test_sample.AlphabetTest')
        from goodpackage import test_sample
        self.failUnlessEqual(alpha1, (True, test_sample.AlphabetTest))
        
