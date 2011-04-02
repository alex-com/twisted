# -*- test-case-name: twisted.trial.dist.test.test_slavetrial -*-
#
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Implementation of amp slave commands.
"""

import sys, os
from cStringIO import StringIO

from twisted.python.failure import Failure
from twisted.internet.protocol import FileWrapper
from twisted.python.log import startLoggingWithObserver, textFromEventDict
from twisted.protocols.amp import AMP
from twisted.scripts.trial import _getSuite
from twisted.trial.runner import TrialSuite, TestLoader
from twisted.trial.dist.slavereporter import SlaveReporter
from twisted.trial.dist import slavecommands, mastercommands



class SlaveProtocol(AMP):
    """
    The slave-side disttrial protocol.
    """

    def __init__(self):
        self.loader = TestLoader()
        self.result = SlaveReporter(self)


    def run(self, testCase):
        """
        Run a test case by name.
        """
        try:
            case = self.loader.loadByName(testCase)
        except:
            # Couldn't find it, darn.
            self.callRemote(
                mastercommands.AddError, testName=testCase, error=Failure().getTraceback())
        else:
            TrialSuite([case]).run(self.result)
        self.callRemote(mastercommands.StopTest, testName=testCase)
        return {'success': True}

    slavecommands.Run.responder(run)


    def chDir(self, directory):
        """
        chdir into given directory.
        """
        os.chdir(directory)
        return {'success': True}

    slavecommands.ChDir.responder(chDir)



class SlaveLogObserver(object):
    """
    A log observer that forward its output to a L{AMP} protocol.
    """

    def __init__(self, protocol):
        """
        @param protocol: a connected L{AMP} protocol instance.
        @type protocol: L{AMP}
        """
        self.protocol = protocol


    def emit(self, eventDict):
        """
        Produce a log output.
        """
        text = textFromEventDict(eventDict)
        if text is None:
            return
        self.protocol.callRemote(mastercommands.TestWrite, out=text)



def main():
    """
    Main function to be run is __name__ == "__main__"
    """
    # Try to make sure nobody writes to stdout (and stderr?)
    sys.stderr = sys.__stderr__ = stderrIO = StringIO()
    sys.stdout = stdoutIO = StringIO()
    slaveProtocol = SlaveProtocol()

    slaveProtocol.makeConnection(FileWrapper(sys.__stdout__))

    observer = SlaveLogObserver(slaveProtocol)
    startLoggingWithObserver(observer.emit, False)

    while True:
        r = sys.__stdin__.read(1)
        if r == '':
            break
        else:
            slaveProtocol.dataReceived(r)
            sys.stdout.flush()
            sys.__stdout__.flush()
            sys.stderr.flush()
            if sys.stdout is not stdoutIO:
                # Something has changed value of stdout, just force it back
                # tp the value we expect
                sys.stdout = stdoutIO
            outValue = sys.stdout.getvalue()
            if outValue:
                slaveProtocol.callRemote(mastercommands.OutWrite,
                                         out=outValue)
            sys.stdout.reset()
            sys.stdout.truncate()
            if sys.stderr is not stderrIO:
                # See above comment about stdout
                sys.stderr = stderrIO
            errValue = sys.stderr.getvalue()
            if errValue:
                slaveProtocol.callRemote(mastercommands.ErrWrite,
                                         error=errValue)
            sys.stderr.reset()
            sys.stderr.truncate()


if __name__ == '__main__':
    main()
