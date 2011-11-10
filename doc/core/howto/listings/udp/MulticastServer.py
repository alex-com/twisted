from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.python.log import msg, err, startLogging
import sys

# Multicast address has to be in range 224.0.0.0 - 239.255.255.255
# Multicast addr in range 224.0.0.0-255 DON'T pass 1st router with ANY TTL(ie > 1)
# Multicast addr 224.0.0.1 (all hosts) is joined by kernel so NO IGMP sent
mcastaddr = "228.0.0.5"

class MulticastPingPong(DatagramProtocol):

    def __init__(self, text):
        self.text = text

    def startProtocol(self):
        # Need to set the TTL so multicast will cross router hops
        self.transport.setTTL(5)
        # Join a specific multicast group, which is the IP we will respond to
        self.deferred=self.transport.joinGroup(mcastaddr)

    def datagramReceived(self, datagram, address):
        msg("Datagram %s received from %s" % (repr(datagram), repr(address)))
        if datagram == 'Client1: Ping':
            self.transport.write("Srv: " + self.text, (mcastaddr, 8005))


startLogging(sys.stdout)
# start multicast listener on multiple interfaces
# To avoid using startProtocol, the following is sufficient:
# reactor.listenMulticast(8005, MulticastPingPong()).joinGroup(mcastaddr)

reactor.listenMulticast(8005, MulticastPingPong("Mcast Pong"), listenMultiple=True)
reactor.run()
