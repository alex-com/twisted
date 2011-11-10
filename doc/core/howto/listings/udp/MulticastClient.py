from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.python import log
import sys

# For a client to send multicast to a multicast server it needs to join
# the same multicast address
mcastaddr = '228.0.0.5'

class MulticastPingClient(DatagramProtocol):

    def startProtocol(self):
        log.msg("TTL: " + repr(self.transport.getTTL()))
        # Default TTL=1 to send over router hops TTL needs to be increased
        self.transport.setTTL(3)
        # send IGMP JOIN for multicast group addr so you can receive
        self.deferred=self.transport.joinGroup(mcastaddr)
        # send to 228.0.0.5:8005 - all listeners will receive - i.e multicast!
        # You could also send unicast to server via write('data',(addr,8005))
        self.transport.write('Client1: Ping',(mcastaddr, 8005))

    def datagramReceived(self, datagram, address):
        log.msg("Received: " + repr(datagram))

# listen on multicast 228.0.0.1:8005, just like the server
log.startLogging(sys.stdout)
reactor.listenMulticast(8005, MulticastPingClient())

reactor.run()
