# -*- test-case-name: twisted.trial.dist.test.test_slave -*-
#
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
This module implements the slave classes
"""

import random, os

from zope.interface import implements

from twisted.internet.protocol import ProcessProtocol
from twisted.internet.interfaces import ITCPTransport
from twisted.protocols.amp import AMP
from twisted.trial.unittest import Todo
from twisted.trial.dist import slavecommands, mastercommands



class LocalSlaveAMP(AMP):
    """
    Local implementation of the master commands.
    """

    def __init__(self):
        super(LocalSlaveAMP, self).__init__()
        self.id = random.random()


    def addSuccess(self, testName):
        """
        Add a success to the reporter.
        """
        self.result.addSuccess(self.testCase)
        return {'success': True}

    mastercommands.AddSuccess.responder(addSuccess)


    def addError(self, testName, error):
        """
        Add an error to the reporter.
        """
        self.result.addError(self.testCase, error)
        return {'success': True}

    mastercommands.AddError.responder(addError)


    def addFailure(self, testName, fail):
        """
        Add a failure to the reporter.
        """
        self.result.addFailure(self.testCase, fail)
        return {'success': True}

    mastercommands.AddFailure.responder(addFailure)


    def addSkip(self, testName, reason):
        """
        Add a skip to the reporter.
        """
        self.result.addSkip(self.testCase, reason)
        return {'success': True}

    mastercommands.AddSkip.responder(addSkip)


    def addExpectedFailure(self, testName, error, todo):
        """
        Add an expected failure to the reporter.
        """
        _todo = Todo(todo)
        self.result.addExpectedFailure(self.testCase, error, _todo)
        return {'success': True}

    mastercommands.AddExpectedFailure.responder(addExpectedFailure)


    def addUnexpectedSuccess(self, testName, todo):
        """
        Add an unexpected success to the reporter.
        """
        self.result.addUnexpectedSuccess(self.testCase, todo)
        return {'success': True}

    mastercommands.AddUnexpectedSuccess.responder(addUnexpectedSuccess)


    def stopTest(self, testName):
        """
        Stop a test.
        """
        self.result.stopTest(self.testCase)
        self.makeReady(self)
        return {'success': True}

    mastercommands.StopTest.responder(stopTest)


    def errWrite(self, error):
        """
        Print an error from the slave.
        """
        self.errStream.write("error[%s]: %s" % (self.id, error))
        self.errStream.flush()
        return {'success': True}

    mastercommands.ErrWrite.responder(errWrite)


    def outWrite(self, out):
        """
        Print output from the slave.
        """
        self.outStream.write("output[%s]: %s" % (self.id, out))
        self.outStream.flush()
        return {'success': True}

    mastercommands.OutWrite.responder(outWrite)


    def testWrite(self, out):
        """
        Print test output from the slave.
        """
        self.testStream.write(out + '\n')
        self.testStream.flush()
        return {'success': True}

    mastercommands.TestWrite.responder(testWrite)


    def run(self, testCase, result, makeReady):
        """
        Run a test.
        """
        self.testCase = testCase
        self.result = result
        self.makeReady = makeReady
        self.result.startTest(testCase)
        self.callRemote(slavecommands.Run, testCase=testCase.id())


    def setOutStream(self, stream):
        """
        Set the stream to which standard output from the slave will get
        forwarded.
        """
        self.outStream = stream


    def setErrStream(self, stream):
        """
        Set the stream to which standard output from the slave will get
        forwarded.
        """
        self.errStream = stream


    def setTestStream(self, stream):
        """
        Set the stream used to log output from tests.
        """
        self.testStream = stream



class LocalSlave(ProcessProtocol):
    """
    Local process slave protocol. This slave runs as a local process and
    communicates via stdin/out

    @cvar logDirectory: directory where logs will reside
    """

    implements(ITCPTransport)

    def __init__(self, ampFactory, logDirectory):
        self.ampFactory = ampFactory
        self.logDirectory = logDirectory


    def write(self, data):
        """
        Forward data to transport.
        """
        self.writeLog.write(data)
        self.transport.write(data)


    def loseConnection(self):
        """
        Closes the transport.
        """
        self.transport.loseConnection()


    def connectionMade(self):
        """
        When connection is made, create the AMP protocol instance.
        """
        self.ampProtocol = self.ampFactory()
        self.ampProtocol.makeConnection(self)
        path = ''
        for token in self.logDirectory.split(os.path.sep):
            path = os.path.join(path, token)
            if not os.path.exists(path):
                os.mkdir(path)
        self.writeLog = file(os.path.join(self.logDirectory, "write.log"), 'w')
        self.outLog = file(os.path.join(self.logDirectory, "out.log"), 'w')
        self.errLog = file(os.path.join(self.logDirectory, "err.log"), 'w')
        self.testLog = file(os.path.join(self.logDirectory, "test.log"), 'w')
        self.ampProtocol.setOutStream(self.outLog)
        self.ampProtocol.setErrStream(self.errLog)
        self.ampProtocol.setTestStream(self.testLog)
        self.ampProtocol.callRemote(slavecommands.ChDir,
                                    directory=self.logDirectory)


    def connectionLost(self):
        self.writeLog.close()
        self.outLog.close()
        self.errLog.close()


    def getHost(self):
        """
        Return host string.
        """
        return "string"


    def getPeer(self):
        """
        Return a peer tuple.
        """
        return "string", "string"


    def outReceived(self, data):
        """
        Send data received from stdout to the AMP protocol's dataReceived.
        """
        self.outLog.write(data)
        self.ampProtocol.dataReceived(data)


    def errReceived(self, data):
        """
        Write error data to log.
        """
        self.errLog.write(data)

