# Copyright (c) 2007 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Test for disttrial slave side.
"""


from cStringIO import StringIO

from twisted.trial.reporter import TestResult
from twisted.trial.unittest import TestCase
from twisted.trial.dist.slave import LocalSlave, LocalSlaveAMP
from twisted.trial.dist import mastercommands

from twisted.scripts import trial
from twisted.test.proto_helpers import StringTransport

from twisted.protocols.amp import AMP


class ResultHolder:
    result = None
    def hold(self, result):
        self.result = result


class LocalSlaveAMPTestCase(TestCase):
    """
    test case for disttrial's master-side local slave AMP protocol
    """

    def setUp(self):
        self.masterTr = StringTransport()
        self.masterAMP = LocalSlaveAMP()
        self.masterAMP.makeConnection(self.masterTr)
        self.result = TestResult()
        self.slaveTr = StringTransport()
        self.slave = AMP()
        self.slave.makeConnection(self.slaveTr)


    def test_runSuccess(self):
        """
        Run a test, and succeed.
        """
        resultHolder = ResultHolder()

        # get a test
        config = trial.Options()
        testName = "twisted.test.test_iutils.UtilsTestCase.testOutput"
        config['tests'].add(testName)
        test = trial._getSuite(config)._tests.pop()

        # run test
        self.masterAMP.run(test, self.result, lambda x: None)
        self.masterTr.clear()

        # succeed
        self.slave.callRemote(mastercommands.AddSuccess, testName=testName
            ).addCallback(lambda result: resultHolder.hold(result['success']))
        self.masterAMP.dataReceived(self.slaveTr.value())
        self.slaveTr.clear()

        self.slave.dataReceived(self.masterTr.value())

        self.assertTrue(resultHolder.result)


    def test_runExpectedFailure(self):
        """
        Run a test, and fail expectedly.
        """
        resultHolder = ResultHolder()

        config = trial.Options()
        testName = "twisted.test.test_iutils.UtilsTestCase.testOutput"
        config['tests'].add(testName)

        test = trial._getSuite(config)._tests.pop()
        self.masterAMP.run(test, self.result, lambda x: None)
        self.masterTr.clear()
        self.slave.callRemote(mastercommands.AddExpectedFailure,
                              testName=testName,
                              error='error',
                              todo='todoReason'
            ).addCallback(lambda result: resultHolder.hold(result['success']))
        self.masterAMP.dataReceived(self.slaveTr.value())
        self.slaveTr.clear()
        self.slave.dataReceived(self.masterTr.value())


        self.assertIn(test, map(lambda pair: pair[0],
                                self.result.expectedFailures))
        self.assertTrue(resultHolder.result)


    def test_runError(self):
        """
        Run a test, and encounter an error.
        """
        resultHolder = ResultHolder()

        config = trial.Options()
        testName = "twisted.test.test_iutils.UtilsTestCase.testOutput"
        config['tests'].add(testName)

        test = trial._getSuite(config)._tests.pop()
        self.masterAMP.run(test, self.result, lambda x: None)
        self.masterTr.clear()
        self.slave.callRemote(mastercommands.AddError,
                              testName=testName,
                              error='error').addCallback(
            lambda result: resultHolder.hold(result['success']))
        self.masterAMP.dataReceived(self.slaveTr.value())
        self.slaveTr.clear()
        self.slave.dataReceived(self.masterTr.value())
        self.assertIn(test, map(lambda pair: pair[0], self.result.errors))
        self.assertTrue(resultHolder.result)


    def test_runFailure(self):
        """
        Run a test, and fail.
        """
        resultHolder = ResultHolder()

        config = trial.Options()
        testName = "twisted.test.test_iutils.UtilsTestCase.testOutput"
        config['tests'].add(testName)

        test = trial._getSuite(config)._tests.pop()
        self.masterAMP.run(test, self.result, lambda x: None)
        self.masterTr.clear()
        self.slave.callRemote(mastercommands.AddFailure,
                              testName=testName,
                              fail='fail').addCallback(
            lambda result: resultHolder.hold(result['success']))
        self.masterAMP.dataReceived(self.slaveTr.value())
        self.slaveTr.clear()
        self.slave.dataReceived(self.masterTr.value())
        self.assertIn(test, map(lambda pair: pair[0], self.result.failures))
        self.assertTrue(resultHolder.result)


    def test_runSkip(self):
        """
        Run a test, but skip it.
        """
        resultHolder = ResultHolder()

        config = trial.Options()
        testName = "twisted.test.test_iutils.UtilsTestCase.testOutput"
        config['tests'].add(testName)

        test = trial._getSuite(config)._tests.pop()
        self.masterAMP.run(test, self.result, lambda x: None)
        self.masterTr.clear()
        self.slave.callRemote(mastercommands.AddSkip, testName=testName,
                              reason='reason').addCallback(
            lambda result: resultHolder.hold(result['success']))
        self.masterAMP.dataReceived(self.slaveTr.value())
        self.slaveTr.clear()
        self.slave.dataReceived(self.masterTr.value())
        self.assertIn(test, map(lambda pair: pair[0], self.result.skips))
        self.assertTrue(resultHolder.result)


    def test_runUnexpectedSuccesses(self):
        """
        Run a test, and succeed!?! unexpectedly.
        """
        resultHolder = ResultHolder()

        config = trial.Options()
        testName = "twisted.test.test_iutils.UtilsTestCase.testOutput"
        config['tests'].add(testName)

        test = trial._getSuite(config)._tests.pop()
        self.masterAMP.run(test, self.result, lambda x: None)
        self.masterTr.clear()
        self.slave.callRemote(mastercommands.AddUnexpectedSuccess,
                              testName=testName,
                              todo='todo').addCallback(
            lambda result: resultHolder.hold(result['success']))
        self.masterAMP.dataReceived(self.slaveTr.value())
        self.slaveTr.clear()
        self.slave.dataReceived(self.masterTr.value())
        self.assertIn(test, map(lambda pair: pair[0],
                                self.result.unexpectedSuccesses))
        self.assertTrue(resultHolder.result)


    def test_runStopTest(self):
        """
        Run a test, and stop.
        """
        resultHolder = ResultHolder()

        class ReadyHolder:
            target = None
            def makeReady(self, target):
                self.target = target

        config = trial.Options()
        testName = "twisted.test.test_iutils.UtilsTestCase.testOutput"
        config['tests'].add(testName)
        test = trial._getSuite(config)._tests.pop()

        readyHolder = ReadyHolder()
        self.masterAMP.run(test, self.result, readyHolder.makeReady)
        self.masterTr.clear()
        self.slave.callRemote(mastercommands.StopTest,
                              testName=testName).addCallback(
            lambda result: resultHolder.hold(result['success']))
        self.masterAMP.dataReceived(self.slaveTr.value())
        self.slaveTr.clear()

        self.slave.dataReceived(self.masterTr.value())

        self.assertEquals(readyHolder.target, self.masterAMP)


    def test_errWrite(self):
        """
        Test that errWrite returns successfully.
        """
        resultHolder = ResultHolder()

        self.masterAMP.setErrStream(StringIO())
        # write error
        self.slave.callRemote(mastercommands.ErrWrite, error="testError"
            ).addCallback(lambda result: resultHolder.hold(result['success']))
        self.masterAMP.dataReceived(self.slaveTr.value())
        self.slaveTr.clear()

        self.slave.dataReceived(self.masterTr.value())

        self.assertTrue(resultHolder.result)


    def test_outWrite(self):
        """
        Test that OutWrite returns successfully.
        """
        resultHolder = ResultHolder()

        self.masterAMP.setOutStream(StringIO())
        # write output
        self.slave.callRemote(mastercommands.OutWrite, out="testOutput"
            ).addCallback(lambda result: resultHolder.hold(result['success']))
        self.masterAMP.dataReceived(self.slaveTr.value())
        self.slaveTr.clear()

        self.slave.dataReceived(self.masterTr.value())

        self.assertTrue(resultHolder.result)



class LocalSlaveTestCase(TestCase):

    def setUp(self):
        class FakeAMProtocol(AMP):
            id = 0
            dataString = ""
            def dataReceived(self, data):
                self.dataString += data
            def setOutStream(self, stream):
                self.outStream = stream
            def setErrStream(self, stream):
                self.errStream = stream
            def setTestStream(self, stream):
                self.testStream = stream
        self.FakeAMProtocol = FakeAMProtocol


    def test_outReceived(self):
        """
        Test that output from a slave gets received faithfully.
        """
        class FakeTransport:
            dataString = ""
            def write(self, data):
                self.dataString += data
        fakeTransport = FakeTransport()
        localSlave = LocalSlave(self.FakeAMProtocol, '.')
        localSlave.makeConnection(fakeTransport)
        data = "The quick brown fox jumps over the lazy dog"
        localSlave.outReceived(data)
        self.assertEquals(data, localSlave.ampProtocol.dataString)


    def test_errReceived(self):
        """
        Test that errors from a slave get logged.
        """
        class FakeTransport:
            dataString = ""
            def write(self, data):
                self.dataString += data
        fakeTransport = FakeTransport()
        localSlave = LocalSlave(self.FakeAMProtocol, '.')
        localSlave.makeConnection(fakeTransport)
        _errLog = localSlave.errLog
        localSlave.errLog = StringIO()
        try:

            data = "The quick brown fox jumps over the lazy dog"
            localSlave.errReceived(data)
            self.assertEquals(data, localSlave.errLog.getvalue())
        finally:
            localSlave.errLog = _errLog


    def test_write(self):
        """
        Test that write writes faithfully.
        """
        class FakeTransport:
            dataString = ""
            def write(self, data):
                self.dataString += data

        localSlave = LocalSlave(self.FakeAMProtocol, '.')
        firstFakeTransport = FakeTransport()
        localSlave.makeConnection(firstFakeTransport)
        replacementTransport = FakeTransport()
        localSlave.transport = replacementTransport
        data = "The quick brown fox jumps over the lazy dog"
        localSlave.write(data)
        self.assertEquals(data, replacementTransport.dataString)


    def test_loseConnection(self):
        """
        Test that loConnection forwards loseConnection to the transport.
        """
        class Transport:
            calls = 0
            data = ""
            def loseConnection(self):
                self.calls += 1
            def write(self, data):
                self.data += data
        transport = Transport()
        localSlave = LocalSlave(self.FakeAMProtocol, '.')
        localSlave.makeConnection(transport)
        localSlave.loseConnection()

        self.assertEquals(transport.calls, 1)


    def test_connectionLost(self):
        """
        Check that losing the connection close the log streams.
        """
        class FakeStream:
            callNumber = 0
            def close(self):
                self.callNumber += 1
        class Transport:
            calls = 0
            data = ""
            def loseConnection(self):
                self.calls += 1
            def write(self, data):
                self.data += data
        transport = Transport()
        localSlave = LocalSlave(self.FakeAMProtocol, '.')
        localSlave.makeConnection(transport)
        localSlave.writeLog = FakeStream()
        localSlave.outLog = FakeStream()
        localSlave.errLog = FakeStream()
        localSlave.connectionLost()
        self.assertEquals(localSlave.writeLog.callNumber, 1)
        self.assertEquals(localSlave.outLog.callNumber, 1)
        self.assertEquals(localSlave.errLog.callNumber, 1)
