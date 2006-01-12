from twisted.trial import unittest

from twisted.web2.client import http
from twisted.web2.http_headers import split

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
    def assertRequest(self, req, expectedLines):
        d = self.proto.submitRequest(req)

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

        self.assertRequest(req, ['GET / HTTP/1.1',
                                 'Connection: Keep-Alive',
                                 ''])

    def test_addedHeaders(self):
        req = http.ClientRequest('GET', '/', {'Host': 'foo'}, None)

        self.assertRequest(req, ['GET / HTTP/1.1',
                                 'Connection: Keep-Alive',
                                 'Host: foo',
                                 ''])

    def test_streamedContent(self):
        req = http.ClientRequest('GET', '/', None, 'Hello friends')

        self.assertRequest(req, ['GET / HTTP/1.1',
                                 'Connection: Keep-Alive',
                                 'Content-Length: 13',
                                 '',
                                 'Hello friends'])


    def test_lastRequest(self):
        req = http.ClientRequest('GET', '/', None, None)

        self.proto.readPersistent = False

        self.assertRequest(req, ['GET / HTTP/1.1',
                                 'Connection: close',
                                 ''])
