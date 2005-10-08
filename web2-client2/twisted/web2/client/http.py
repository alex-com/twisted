from twisted.internet import defer, protocol
from twisted.protocols import basic, policies
from twisted.web2 import stream as stream_mod, http, http_headers, responsecode
from twisted.web2.channel import http as httpchan

class ClientRequest(object):
    def __init__(self, method, uri, headers, stream):
        self.method = method
        self.uri = uri
        if isinstance(headers, http_headers.Headers):
            self.headers = headers
        else:
            self.headers = http_headers.Headers(headers or {})
            
        if stream is not None:
            self.stream = stream_mod.IByteStream(stream)
        else:
            self.stream = None

class HTTPClientChannelRequest(httpchan.HTTPParser):
    parseCloseAsEnd = True
    outgoing_version = "HTTP/1.1"
    chunkedOut = False
    finished = False
    
    def __init__(self, channel, request, persistent=True):
        httpchan.HTTPParser.__init__(self, channel, persistent)
        self.request = request
        self.transport = self.channel.transport
        self.responseDefer = defer.Deferred()
        
    def submit(self):
        l = []
        request = self.request
        if request.method == "HEAD":
            # No incoming data will arrive.
            self.length = 0
        
        l.append('%s %s %s\r\n' % (request.method, request.uri,
                                   self.outgoing_version))
        if request.headers is not None:
            for name, valuelist in request.headers.getAllRawHeaders():
                for value in valuelist:
                    l.append("%s: %s\r\n" % (name, value))
        
        if request.stream is not None:
            if request.stream.length is not None:
                l.append("%s: %s\r\n" % ('Content-Length', request.stream.length))
            else:
                # Got a stream with no length. Send as chunked and hope, against
                # the odds, that the server actually supports chunked uploads.
                l.append("%s: %s\r\n" % ('Transfer-Encoding', 'chunked'))
                self.chunkedOut = True

        if not self.persistent:
            l.append("%s: %s\r\n" % ('Connection', 'close'))
        else:
            l.append("%s: %s\r\n" % ('Connection', 'Keep-Alive'))
        
        l.append("\r\n")
        self.transport.writeSequence(l)
        
        d = stream_mod.StreamProducer(request.stream).beginProducing(self)
        d.addCallback(self._finish).addErrback(self._error)

    def registerProducer(self, producer, streaming):
        """Register a producer.
        """
        self.transport.registerProducer(producer, streaming)

    def unregisterProducer(self):
        self.transport.unregisterProducer()
        
    def write(self, data):
        if not data:
            return
        elif self.chunkedOut:
            self.transport.writeSequence(("%X\r\n" % len(data), data, "\r\n"))
        else:
            self.transport.write(data)

    def _finish(self, x):
        """We are finished writing data."""
        if self.chunkedOut:
            # write last chunk and closing CRLF
            self.transport.write("0\r\n\r\n")
        
        self.finished = True
        self.channel.requestWriteFinished(self)
        del self.transport

    def _error(self, err):
        self.abortParse()
        self.responseDefer.errback(err)

    def _abortWithError(self, errcode, text):
        import sys, pdb
        print >> sys.stderr, "ERROR:", errcode, text
        pdb.set_trace()
        
    def gotInitialLine(self, initialLine):
        parts = initialLine.split(' ', 2)
        
        # Parse the initial request line
        if len(parts) != 3:
            self._abortWithError(responsecode.BAD_REQUEST, 'Bad response line: %s' % initialLine)

        strversion, self.code, message = parts
        
        try:
            protovers = http.parseVersion(strversion)
            if protovers[0] != 'http':
                raise ValueError()
        except ValueError:
            self._abortWithError(responsecode.BAD_REQUEST, "Unknown protocol: %s" % strversion)
        
        self.version = protovers[1:3]

        # Ensure HTTP 0 or HTTP 1.
        if self.version[0] != 1:
            self._abortWithError(responsecode.HTTP_VERSION_NOT_SUPPORTED, 'Only HTTP 1.x is supported.')

    ## FIXME: Actually creates Response, function is badly named!
    def createRequest(self):
        self.stream = stream_mod.ProducerStream()
        self.response = http.Response(self.code, self.inHeaders, self.stream)
        self.stream.registerProducer(self, True)
        
        del self.inHeaders

    ## FIXME: Actually processes Response, function is badly named!
    def processRequest(self):
        self.responseDefer.callback(self.response)
        
    def handleContentChunk(self, data):
        self.stream.write(data)

    def handleContentComplete(self):
        self.stream.finish()

class HTTPClientProtocol(basic.LineReceiver, policies.TimeoutMixin, object):
    chanRequest = None
    maxHeaderLength = 10240
    first = 1
    
    def __init__(self):
        pass

    def lineReceived(self, line):
        if self.first:
            self.first = 0
            self.chanRequest.gotInitialLine(line)
        else:
            self.chanRequest.lineReceived(line)

    def rawDataReceived(self, data):
        self.chanRequest.rawDataReceived(data)
        
    def submitRequest(self, request):
        assert self.chanRequest is None
        d = defer.Deferred()
        chanRequest = HTTPClientChannelRequest(self, request, False)
        self.chanRequest = chanRequest
        chanRequest.submit()
        return chanRequest.responseDefer

    def requestReadFinished(self, request, persistent):
        pass

    def requestWriteFinished(self, request):
        pass

    def connectionLost(self, reason):
        pass
    
    
# class HTTPClientProtocol(basic.LineReceiver, policies.TimeoutMixin, object):
#     maxHeaderLength = 10240 
    
#     def __init__(self):
#         self.chanRequests = []
        
#     def submitRequest(self, request):
#         assert not self.chanRequests or self.chanRequests[-1].finished
        
#         self.manager.clientBusy(self)
        
#         d = defer.Deferred()
#         chanRequest = HTTPClientChannelRequest(self, request, self.persistent)
#         self.chanRequests.append(chanRequest)
#         chanRequest.submit()
#         return chanRequest.responseDefer
    
#     def requestReadFinished(self, request, persistent):
#         assert self.chanRequests[0] is request
        
#         self.persistent = persistent
#         del self.chanRequests[0]
#         if persistent and not self.chanRequests:
#             self.manager.clientIdle(self)
        
#     def requestWriteFinished(self, request):
#         if len(self.chanRequests) == 1:
#             self.manager.clientPipelining(self)

#     def connectionLost(self, reason):
#         pass


# class HTTPClientManager(object):
#     def clientBusy(self, proto):
#         pass
    
#     def clientIdle(self, proto):
#         pass

#     def clientPipelining(self, proto):
#         pass
    
#     def clientGone(self, proto):
#         pass
    
# class HTTPClientProtocolFactory(protocol.ClientFactory, HTTPClientManager):
#     protocol = HTTPClientProtocol
    
#     def __init__(self, request):
#         self.request = request
#         self.deferred = defer.Deferred()
        
#     def buildProtocol(self, addr):
#         return self.protocol(self)
        
#     def clientConnectionFailed(self, connector, reason):
#         self.sendFailureResponse(reason)

#     def sendFailureResponse(self, reason):
#         response = http.Response(code=responsecode.BAD_GATEWAY, stream=str(reason.value))
#         self.deferred.callback(response)


def testConn(host):
    from twisted.internet import reactor
    d = protocol.ClientCreator(reactor, HTTPClientProtocol).connectTCP(host, 80)
    def sendReq(proto):
        return proto.submitRequest(ClientRequest("GET", "/", {'Host':host}, None))
    d.addCallback(sendReq)
    def gotResp(resp):
        def print_(n):
            print "DATA:", `n`
        def printdone(n):
            print "DONE"
        print "GOT RESPONSE: ", resp
        stream_mod.readStream(resp.stream, print_).addCallback(printdone)
    d.addCallback(gotResp)
    del d
    reactor.run()

