from twisted.trial import unittest
from twisted.python import log

from twisted.internet import protocol, interfaces, reactor, defer
from twisted.protocols import loopback

from zope.interface import implements

from twisted.web2.client import http
from twisted.web2 import http_headers
from twisted.web2.http_headers import split
from twisted.web2 import iweb, responsecode

from twisted.web2.test.test_http import LoopbackRelay, HTTPTests, TestConnection

from twisted.python.util import tracer

import pdb

class FakeTransport:
    buffer = ''
    disconnected = False
    
    def write(self, bytes):
        self.buffer += bytes

    def writeSequence(self, seq):
        self.write(''.join(seq))

    def loseConnection(self):
        self.disconnected = True

    def registerProducer(self, producer, streaming):
        self.producer = producer
        self.streamingProducer = streaming
        if not streaming:
            producer.resumeProducing()
            
    def unregisterProducer(self):
        self.producer = None
        
# Halfway tests

class TestSentRequests(unittest.TestCase):
    def assertRequest(self, expectedLines):
        headers, content = self.proto.transport.buffer.split('\r\n\r\n', 1)
        status, headers = headers.split('\r\n', 1)
        headers = headers.split('\r\n')

        # check status line
        self.assertEquals(status, expectedLines[0])

        expectedHeaders, expectedContent = list(split(expectedLines[1:], ''))
        
        # check headers (header order isn't guraunteed so we use
        # self.assertIn
        for x in headers:
            self.assertIn(x, expectedHeaders)

        if expectedContent:
            self.assertEquals(content, expectedContent[0])
        
    def setUp(self):
        self.proto = http.HTTPClientProtocol()
        self.proto.transport = FakeTransport()
        self.proto.inputTimeOut = None
    
    def test_simpleRequest(self):
        # set up request
        req = http.ClientRequest('GET', '/', None, None)

        self.proto.submitRequest(req)
        
        self.assertRequest(['GET / HTTP/1.1',
                            'Connection: close',
                            ''])

    def test_addedHeaders(self):
        req = http.ClientRequest('GET', '/', {'Host': 'foo'}, None)

        self.proto.submitRequest(req)
        
        self.assertRequest(['GET / HTTP/1.1',
                            'Connection: close',
                            'Host: foo',
                            ''])

    def test_streamedContent(self):
        req = http.ClientRequest('GET', '/', None, 'Hello friends')

        self.proto.submitRequest(req)

        self.assertRequest(['GET / HTTP/1.1',
                            'Connection: close',
                            'Content-Length: 13',
                            '',
                            'Hello friends'])


    def test_persistConnection(self):
        req = http.ClientRequest('GET', '/', None, None)

        self.proto.submitRequest(req, closeAfter=False)
        
        self.assertRequest(['GET / HTTP/1.1',
                            'Connection: Keep-Alive',
                            ''])

# round trip tests
class TestServer(protocol.Protocol):
    data = ""
    done = False
    
    def dataReceived(self, data):
        self.data += data
        
    def write(self, data):
        self.transport.write(data)

    def connectionLost(self, reason):
        self.done = True
        self.transport.loseConnection()

    def loseConnection(self):
        self.done = True
        self.transport.loseConnection()

class ClientTests(HTTPTests):
    def connect(self, logFile=None, maxPipeline=4,
                inputTimeOut=60000, betweenRequestsTimeOut=600000):
        cxn = TestConnection()

        def makeTestRequest(*args):
            cxn.requests.append(TestRequest(*args))
            return cxn.requests[-1]
        
        cxn.client = http.HTTPClientProtocol()
    cxn.client.inputTimeOut = inputTimeOut
        cxn.server = TestServer()
    
        cxn.serverToClient = LoopbackRelay(cxn.client, logFile)
        cxn.clientToServer = LoopbackRelay(cxn.server, logFile)
        cxn.server.makeConnection(cxn.serverToClient)
        cxn.client.makeConnection(cxn.clientToServer)

        return cxn

    def writeToClient(self, cxn, data):
    cxn.server.write(data)
    self.iterate(cxn)

    def assertRecieved(self, cxn, expected):
    self.iterate(cxn)
    self.assertEquals(cxn.server.data, expected)

    def assertDone(self, cxn):
    self.iterate(cxn)
    self.assertEquals(cxn.server.done, True)

    def test_simpleRequest(self):
    cxn = self.connect(inputTimeOut=None)
    req = http.ClientRequest('GET', '/', None, None)

    def gotData(data):
        self.assertEquals(data, '1234567890')

    def gotResp(resp):
        self.assertEquals(resp.code, 200)

        self.assertEquals(tuple(
            resp.headers.getAllRawHeaders()),
                  (('Content-Length', ['10']),))

        return defer.maybeDeferred(resp.stream.read).addCallback(gotData)
        
    d = cxn.client.submitRequest(req).addCallback(gotResp)

    self.assertRecieved(cxn, 'GET / HTTP/1.1\r\nConnection: close\r\n\r\n')

    self.writeToClient(cxn, 'HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\n1234567890')

    return d

    def test_delayedContent(self):
    cxn = self.connect(inputTimeOut=None)
    req = http.ClientRequest('GET', '/', None, None)

    def gotData(data):
        self.assertEquals(data, '1234567890')

    def gotResp(resp):
        self.assertEquals(resp.code, 200)
        self.assertEquals(tuple(
            resp.headers.getAllRawHeaders()),
                  (('Content-Length', ['10']),))

        self.writeToClient(cxn, '1234567890')

        return defer.maybeDeferred(resp.stream.read).addCallback(gotData)

    d = cxn.client.submitRequest(req).addCallback(gotResp)

    self.assertRecieved(cxn, 'GET / HTTP/1.1\r\nConnection: close\r\n\r\n')

    self.writeToClient(cxn, 'HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\n')

    return d
