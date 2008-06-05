#!/usr/bin/python
# Copyright (c) 2001-2008 Twisted Matrix Laboratories.
# See LICENSE for details.

import sys

from twisted.internet.defer import Deferred
from twisted.names.srvconnect import SRVConnector
from twisted.words.xish import domish
from twisted.words.protocols.jabber import xmlstream, client
from twisted.words.protocols.jabber.jid import JID



class XMPPClientConnector(SRVConnector):
    def __init__(self, reactor, domain, factory):
        SRVConnector.__init__(self, reactor, 'xmpp-client', domain, factory)


    def pickServer(self):
        host, port = SRVConnector.pickServer(self)

        if not self.servers and not self.orderedServers:
            # no SRV record, fall back..
            port = 5222

        return host, port



class Client(object):
    def __init__(self, reactor, jid, secret):
        self.reactor = reactor
        f = client.XMPPClientFactory(jid, secret)
        f.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.connected)
        f.addBootstrap(xmlstream.STREAM_END_EVENT, self.disconnected)
        f.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self.authenticated)
        f.addBootstrap(xmlstream.INIT_FAILED_EVENT, self.init_failed)
        connector = XMPPClientConnector(reactor, jid.host, f)
        connector.connect()
        self.finished = Deferred()


    def rawDataIn(self, buf):
        print "RECV:", buf.decode('utf-8').encode('ascii', 'replace')


    def rawDataOut(self, buf):
        print "SEND:", buf.decode('utf-8').encode('ascii', 'replace')


    def connected(self, xs):
        print 'Connected.'

        self.xmlstream = xs

        # Log all traffic
        xs.rawDataInFn = self.rawDataIn
        xs.rawDataOutFn = self.rawDataOut


    def disconnected(self, xs):
        print 'Disconnected.'

        self.finished.callback(None)


    def authenticated(self, xs):
        print "Authenticated."

        presence = domish.Element((None, 'presence'))
        xs.send(presence)

        self.reactor.callLater(5, xs.sendFooter)


    def init_failed(self, failure):
        print "Initialization failed."
        print failure

        self.xmlstream.sendFooter()



def main(reactor, jid, secret):
    """
    Connect to the given Jabber ID and return a L{Deferred} which will be
    called back when the connection is over.

    @param reactor: The reactor to use for the connection.
    @param jid: A L{JID} to connect to.
    @param secret: A C{str}
    """
    return Client(reactor, JID(jid), secret).finished



def run():
    from twisted.internet import reactor
    from twisted.python.log import startLogging
    startLogging(sys.stdout)
    d = main(reactor, *sys.argv[1:])
    d.addCallback(lambda ign: reactor.stop())
    reactor.run()



if __name__ == '__main__':
    run()
