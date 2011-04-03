# -*- test-case-name: twisted.trial.dist.test.test_disttrial -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
This module containts the disttrial runner, the disttrial class responsible for
coordinating all of disttrial's behavior at the highest level.  It also contains
a L{run} function to provide a simple interface to that class for the command
line tool.
"""

import sys, os, random

from twisted.python.usage import UsageError
from twisted.python.modules import theSystemPath
from twisted.internet.defer import Deferred, gatherResults
from twisted.python.filepath import FilePath

from twisted.trial.util import _unusedTestDirectory
from twisted.trial.runner import TrialSuite, TestLoader
from twisted.trial.unittest import _iterateTests
from twisted.trial.dist.slave import LocalSlave, LocalSlaveAMP
from twisted.trial.dist.options import DistOptions
from twisted.trial.dist.distreporter import DistReporter
from twisted.trial.dist.distreporter import UncleanWarningsReporterWrapper



class DistTrialRunner(object):
    """
    A specialized runner for disttrial. The runner launches a number of local
    slave processes which will run tests.

    @ivar slaveNumber: the number of slaves to be spawned.
    @type slaveNumber: C{int}

    @ivar stream: stream which the reporter will use.

    @ivar reporterFactory: the reporter class to be used.

    @ivar loaderFactory: a class loader for test, to be customized in tests.
    """

    loaderFactory = TestLoader

    def _makeResult(self):
        """
        Make reporter factory, and wrap it with a disttrial reporter.
        """
        reporter = self.reporterFactory(self.stream, realtime=self.rterrors)
        if self.uncleanWarnings:
            reporter = UncleanWarningsReporterWrapper(reporter)
        return self.distReporterFactory(reporter)


    def __init__(self, distReporterFactory,
                 reporterFactory, _tests, slaveNumber=4,
                 mode=None,
                 stream=sys.__stdout__,
                 realTimeErrors=False,
                 uncleanWarnings=False,
                 workingDirectory='_trial_temp'):
        self.slaveNumber = slaveNumber
        self._tests = _tests
        self.distReporterFactory = distReporterFactory
        self.reporterFactory = reporterFactory
        self.mode = mode
        self.stream = stream
        self.rterrors = realTimeErrors
        self.uncleanWarnings = uncleanWarnings
        self._result = None
        self.workingDirectory = workingDirectory
        self._logFileObserver = None
        self._logFileObject = None
        self._logWarnings = False

        testdir, testDirLock = _unusedTestDirectory(
            FilePath(self.workingDirectory))


    def writeResults(self, result):
        """
        write test run final outcome to result

        @param result: a C{TestResult} which will print errors and the summary
        """
        result.done()


    def createLocalSlaves(self, quantity):
        """
        Create local slave protocol instances and return them

        @param quantity: the number of local slaves to be created

        @return: a list of C{quantity} C{LocalSlave} instances
        """
        return [LocalSlave(LocalSlaveAMP, os.path.join(
            self.workingDirectory, str(x))) for x in range(quantity)]


    def launchSlaveProcesses(self, spawner, protocols):
        """
        Spawn processes from a list of process protocols

        @param spawner: A function which will spawn a local process, given a
            command and a processProtocol

        @param protocols: An iterable of C{ProcessProtocol} instances
        """
        slavetrialPath = theSystemPath[
            'twisted.trial.dist.slavetrial'].filePath.path
        for s in protocols:
            spawner(s, sys.executable,
                    args=[sys.executable, slavetrialPath],
                    env=os.environ)


    def run(self, test, reactor, slaveArguments):
        """
        Spawn local slave processes and load tests. After that, run them.

        @param test: a test or tests suite to be run

        @param reactor: the reactor to use, to be customized in tests.
        @type reactor: a provider of
            L{twisted.internet.interfaces.IReactorProcess}

        @param slaveArguments: arguments to pass to slave load.
        @type slaveArguments: C{list}
        """
        result = self._makeResult()
        suite = TrialSuite([test])
        self.stream.write("Running %d tests.\n" % (suite.countTestCases(),))

        if not suite.countTestCases():
            # Take a shortcut if there is no test
            suite.run(result.original)
            self.writeResults(result)
            return result

        slaves = self.createLocalSlaves(self.slaveNumber)
        self.launchSlaveProcesses(reactor.spawnProcess, slaves)

        ampSlaves = [s.ampProtocol for s in slaves]
        testCases = iter(list(_iterateTests(suite)))

        def driveSlave(slave, testCases, complete=None):
            if complete is None:
                complete = Deferred()
            def proceed(ignored):
                driveSlave(slave, testCases, complete)
            try:
                case = testCases.next()
            except StopIteration:
                complete.callback(None)
            else:
                slave.run(case, result, proceed)

            return complete

        workers = []
        for slave in ampSlaves:
            workers.append(driveSlave(slave, testCases))

        gatherResults(workers).addCallback(lambda x: reactor.stop())
        reactor.run()

        self.writeResults(result)
        return result


    def _getSuite(self, config):
        """
        Return the test suite loaded.
        """
        loader = self._getLoader(config)
        recurse = not config['no-recurse']
        return loader.loadByNames(config['tests'], recurse)


    def _getLoader(self, config):
        """
        Return a custom loader.
        """
        loader = self.loaderFactory()
        if config['random']:
            randomer = random.Random()
            randomer.seed(config['random'])
            loader.sorter = lambda x : randomer.random()
            print 'Running tests shuffled with seed %d\n' % config['random']
        return loader


    def getConfig():
        """
        Get configuration from sys.argv

        @return: a C{trial.Options} instance generated from command-line
            options

        @raise SystemExit: raise this if the command-line options are not
            parseable
        """
        if len(sys.argv) == 1:
            sys.argv.append("--help")
        config = DistOptions()
        try:
            config.parseOptions()
        except UsageError, ue:
            raise SystemExit("%s: %s" % (sys.argv[0], ue))
        return config

    getConfig = staticmethod(getConfig)


    def getTrialRunner(cls, config):
        """
        Generate a trial runner from the config.
        """
        return cls(DistReporter, config['reporter'], config['tests'],
            int(config['localnumber']),
            realTimeErrors=config['rterrors'],
            uncleanWarnings=config['unclean-warnings'],
            workingDirectory=config['temp-directory'])

    getTrialRunner = classmethod(getTrialRunner)


    def _run(self, config, trialRunner):
        """
        Given a TrialRunner instance and a config, generate a test suite from
        the config and run it with the runner

        @param config: a C{trial.Options} instance which determines a test
            suite

        @param trialRunner: a C{DistTrialRunner} instance which runs a test
            suite

        @return: 0 if the test sun was successful, 1 otherwise
        @rtype: C{int}
        """
        suite = self._getSuite(config)
        from twisted.internet import reactor
        testResult = self.run(suite, reactor, config.getSlaveArguments())
        return not testResult.wasSuccessful()



def run():
    """
    Main run function to fire disttrial.
    """
    config = DistTrialRunner.getConfig()
    trialRunner = DistTrialRunner.getTrialRunner(config)
    status = trialRunner._run(config, trialRunner)
    sys.exit(status)

