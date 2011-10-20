# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.trial.dist.slavetrial}.
"""

import os

from twisted.protocols.amp import AMP
from twisted.test.proto_helpers import StringTransport
from twisted.trial.unittest import TestCase
from twisted.trial.dist.slavetrial import SlaveProtocol, SlaveLogObserver
from twisted.trial.dist import slavecommands, mastercommands



class FakeAMP(AMP):
    """
    A fake amp protocol.
    """



class SlaveProtocolTestCase(TestCase):
    """
    Tests for L{SlaveProtocol}.
    """

    def setUp(self):
        """
        Set up a transport, a result stream and a protocol instance
        """
        self.serverTr = StringTransport()
        self.clientTr = StringTransport()
        self.server = SlaveProtocol()
        self.server.makeConnection(self.serverTr)
        self.client = FakeAMP()
        self.client.makeConnection(self.clientTr)


    def test_run(self):
        """
        Check if running a test gets a valid response.
        """
        d = self.client.callRemote(slavecommands.Run, testCase="tmp")
        def check(result):
            self.assertTrue(result['success'])
        d.addCallback(check)
        self.server.dataReceived(self.clientTr.value())
        self.clientTr.clear()
        self.client.dataReceived(self.serverTr.value())
        self.serverTr.clear()
        return d


    def test_chDir(self):
        """
        Test that the chDir command does change the current path.
        """
        curdir = os.path.realpath(os.path.curdir)
        try:
            self.server.chDir('..')
            self.assertNotEquals(os.path.realpath(os.path.curdir), curdir)
        finally:
            self.server.chDir(curdir)



class SlaveLogObserverTestCase(TestCase):
    """
    Tests for L{SlaveLogObserver}
    """

    def test_emit(self):
        """
        Checl that L{SlaveLogObserver} forward data to
        L{mastercommands.TestWrite}.
        """
        calls = []
        class FakeClient(object):
            def callRemote(self, method, **kwargs):
                calls.append((method, kwargs))
        observer = SlaveLogObserver(FakeClient())
        observer.emit({'message': ['Some log']})
        self.assertEquals(calls,
            [(mastercommands.TestWrite, {'out': 'Some log'})])

