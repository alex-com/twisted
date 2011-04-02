# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.trial.dist.disttrial}.
"""

import os, sys
from cStringIO import StringIO

from twisted.internet.protocol import ProcessProtocol
from twisted.python.failure import Failure
from twisted.python.compat import set

from twisted.trial.unittest import TestCase
from twisted.trial.reporter import Reporter, TreeReporter
from twisted.trial.runner import TrialSuite, ErrorHolder

from twisted.trial.dist.disttrial import DistTrialRunner
from twisted.trial.dist.distreporter import DistReporter
from twisted.trial.dist.distreporter import UncleanWarningsReporterWrapper
from twisted.trial.dist.slave import LocalSlave



class DistTrialRunnerTestCase(TestCase):
    """
    Tests for L{DistTrialRunner}.
    """

    def setUp(self):
        """
        Create a runner for testing.
        """
        self.runner = DistTrialRunner(DistReporter,
                                      TreeReporter,
                                      ["twisted"])
        self.runner.stream = StringIO()


    def test_writeResults(self):
        """
        Test that write results writes to the stream specified in the initiator.
        """
        stringIO = StringIO()
        result = DistReporter(Reporter(stringIO))
        self.runner.writeResults(result)
        self.assertTrue(stringIO.tell() > 0)


    def test_createLocalSlaves(self):
        """
        Test that createLocalSlaves creates L{LocalSlave} instances and the
        right quantity.
        """
        quantity = 4
        slaves = self.runner.createLocalSlaves(quantity)
        for s in slaves:
            self.assertIsInstance(s, LocalSlave)
        self.assertEquals(len(slaves), quantity)


    def test_launchSlaveProcesses(self):
        """
        Test that, given spawnProcess, launchSlaveProcess launches a python
        process with a existing path as its argument.
        """
        protocols = [ProcessProtocol() for i in range(4)]
        arguments = []
        def fakeSpawnProcess(processProtocol, executable, args=(), env={},
                             path=None,uid=None, gid=None, usePTY=0,
                             childFDs=None):
            arguments.append(executable)
            arguments.append(args[0])
            arguments.append(args[1])
        self.runner.launchSlaveProcesses(fakeSpawnProcess, protocols)
        self.assertEquals(arguments[0], arguments[1])
        self.assertTrue(os.path.exists(arguments[2]))


    def test_run(self):
        """
        Test that run starts the rector exactly once and spawns each of the
        slaves exactly once.
        """
        class FakeTransport(object):
            def write(self, data):
                pass
        class FakeReactor(object):
            spawnCount = 0
            stopCount = 0
            runCount = 0
            def spawnProcess(self, slave, *args, **kwargs):
                slave.makeConnection(FakeTransport())
                self.spawnCount += 1
            def stop(self):
                self.stopCount += 1
            def run(self):
                self.runCount += 1
        fakeReactor = FakeReactor()
        self.runner.run(TestCase(), fakeReactor, "")
        self.assertEquals(fakeReactor.runCount, 1)
        self.assertEquals(fakeReactor.spawnCount, self.runner.slaveNumber)


    def test_runUncleanWarnings(self):
        """
        Test that running with the unclean-warnings option use the correct
        reporter.
        """
        class FakeTransport(object):
            def write(self, data):
                pass
        class FakeReactor(object):
            spawnCount = 0
            stopCount = 0
            runCount = 0
            def spawnProcess(self, slave, *args, **kwargs):
                slave.makeConnection(FakeTransport())
                self.spawnCount += 1
            def stop(self):
                self.stopCount += 1
            def run(self):
                self.runCount += 1
        fakeReactor = FakeReactor()
        self.runner.uncleanWarnings = True
        result = self.runner.run(TestCase(), fakeReactor, "")
        self.assertIsInstance(result, DistReporter)
        self.assertIsInstance(result.original,
                              UncleanWarningsReporterWrapper)


    def test_runWithoutTest(self):
        """
        When the suite contains no test, the runner should take a shortcut path
        without launching any process.
        """
        fakeReactor = object()
        suite = TrialSuite()
        result = self.runner.run(suite, fakeReactor, "")
        self.assertIsInstance(result, DistReporter)
        output = self.runner.stream.getvalue()
        self.assertIn("Running 0 test", output)
        self.assertIn("PASSED", output)


    def test_runWithoutTestButWithAnError(self):
        """
        Even if there is no test, the suite can contain an error (most likely,
        an import error): this should make the run fail, and the error should
        be printed.
        """
        fakeReactor = object()
        error = ErrorHolder("an error", Failure(RuntimeError("foo bar")))
        result = self.runner.run(error, fakeReactor, "")
        self.assertIsInstance(result, DistReporter)
        output = self.runner.stream.getvalue()
        self.assertIn("Running 0 test", output)
        self.assertIn("foo bar", output)
        self.assertIn("an error", output)
        self.assertIn("errors=1", output)
        self.assertIn("FAILED", output)



class DistTrialTestCase(TestCase):
    """
    Test of L{distrial} utility functions.
    """

    def test_getConfig(self):
        """
        Test that config interprets sys.argv as expected.
        """
        _argv = sys.argv
        try:
            sys.argv = ["disttrial.py", "twisted"]
            config = DistTrialRunner.getConfig()
            self.assertEquals(config["tests"], set(["twisted"]))
        finally:
            sys.argv = _argv


    def test_getTrialRunner(self):
        """
        Test that C{getTrialRunner} returns an appropriate object.
        """
        config = {"reporter": TreeReporter,
                  "tests": set(["twisted"]),
                  "localnumber": "4",
                  "temp-directory": "_trial_temp",
                  "rterrors": False,
                  "unclean-warnings": False}
        trialRunner = DistTrialRunner.getTrialRunner(config)
        self.assertEquals(trialRunner.reporterFactory,
                          TreeReporter)
        self.assertEquals(set(["twisted"]), trialRunner._tests)


    def test_getSuite(self):
        """
        Test C{_getSuite} method.
        """
        config = {"reporter": TreeReporter,
                  "tests": set(["twisted"]),
                  "localnumber": "4",
                  "temp-directory": "_trial_temp",
                  "rterrors": False,
                  "unclean-warnings": False,
                  "random": 0,
                  "no-recurse": False}
        called = []
        class MockLoader(object):
            def loadByNames(self, tests, recurse):
                called.append([tests, recurse])
                return called
        trialRunner = DistTrialRunner.getTrialRunner(config)
        trialRunner.loaderFactory = MockLoader
        result = trialRunner._getSuite(config)
        # We should get what is returned by loadByNames
        self.assertIdentical(called, result)
        self.assertEquals(called, [[set(["twisted"]), True]])

