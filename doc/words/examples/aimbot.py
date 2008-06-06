#!/usr/bin/python
# Copyright (c) 2001-2008 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
AIM echo bot.
"""

from getpass import getpass

from twisted.words.protocols import toc
from twisted.internet import protocol
import twisted.words.im.tocsupport as ts

class AIMBot(toc.TOCClient):
    """
    AOL Instant Messenger echo bot.
    """

    def gotConfig(self, mode, buddylist, permit, deny):
        """
        called when the server sends us config info
        """
        # add someone to our deny list?
        self.add_deny([])

        # add ourself to our buddy list
        self.add_buddy([self.screenname])

        # finish up the signon procedure
        self.signon()


    def updateBuddy(self, username, online, evilness, signontime, idletime,
                    userclass, away):
        """
        called when a buddy changes state
        """
        print "status changed for", username


    def hearWarning(self, warnlvl, screenname):
        """
        called when someone warns us
        """
        print screenname, "warned us"

    def hearError(self, errcode, *args):
        """
        called when server sends error
        """
        print "recieved error:", errcode


    def hearMessage(self, username, message, autoreply):
        """
        called when a message is recieved
        """
        # remove the incoming message' html
        msg = ts.dehtml(message)

        print "got message:", msg

        # construct the reply, and turn it into html
        reply = ts.html("echo: %s" % msg)

        self.say(username, reply)



def main(reactor, screenname):
    password = getpass("Password for %s: " % (screenname,))
    cc = protocol.ClientCreator(reactor, AIMBot, screenname, password)
    cc.connectTCP("toc.oscar.aol.com", 9898)



if __name__ == '__main__':
    react(main, sys.argv[1:])
