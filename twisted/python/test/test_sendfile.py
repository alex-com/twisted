# Copyright (c) 2007-2010 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for sendfile.
"""

import socket, errno

from twisted.trial.unittest import TestCase

try:
    from twisted.python._sendfile import sendfile
except ImportError:
    sendfile = None



class SendfileTestCase(TestCase):
    """
    Tests for L{twisted.python._sendfile}.
    """

    if sendfile is None:
       skip = "sendfile not available"

    def setUp(self):
        """
        Create a listening server port and a list with which to keep track
        of created sockets.
        """
        self.serverSocket = socket.socket()
        self.serverSocket.bind(('127.0.0.1', 0))
        self.serverSocket.listen(1)
        self.connections = [self.serverSocket]
        filename = self.mktemp()
        f = open(filename, 'w+')
        f.write('x' * 1000)
        f.close()
        self.file = open(filename, 'r')


    def tearDown(self):
        """
        Close any sockets which were opened by the test.
        """
        for skt in self.connections:
            skt.close()
        self.file.close()


    def _connectedPair(self):
        """
        Return the two sockets which make up a new TCP connection.
        """
        client = socket.socket()
        client.setblocking(False)
        try:
            client.connect(('127.0.0.1', self.serverSocket.getsockname()[1]))
        except socket.error, e:
            self.assertEquals(e.args[0], errno.EINPROGRESS)
        server, addr = self.serverSocket.accept()

        self.connections.extend((client, server))
        return client, server


    def test_basic(self):
        """
        Test the basic behavior for sendfile.
        """
        server, client = self._connectedPair()
        s, o = sendfile(server.fileno(), self.file.fileno(), 0, 100)
        self.assertEquals(s, 100)
        self.assertEquals(o, 100)
        data = client.recv(500)
        self.assertEquals(len(data), 100)

        s, o = sendfile(server.fileno(), self.file.fileno(), o, 150)
        self.assertEquals(s, 150)
        self.assertEquals(o, 250)
        data = client.recv(500)
        self.assertEquals(len(data), 150)


    def test_afterSend(self):
        """
        Verify that a send after sendfile behaves correctly.
        """
        server, client = self._connectedPair()
        server.send('y' * 10)
        s, o = sendfile(server.fileno(), self.file.fileno(), 0, 100)
        self.assertEquals(s, 100)
        self.assertEquals(o, 100)
        data = client.recv(200)
        if len(data) < 100:
            data += client.recv(200)
        self.assertEquals(len(data), 110)
        self.assertEquals(data[:10], 'y' * 10)
        self.assertEquals(data[10:20], 'x' * 10)
