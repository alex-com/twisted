from twisted.internet import defer, protocol
from twisted.protocols import basic
from twisted.python import log
basic.DEBUG = True

FAILURE = 'Failure'
SUCCESS = 'Success'

BAD_ARGUMENT = 'Bad argument'
NO_SUCH_METHOD = 'No such method'
DONT_PIPELINE = 'No pipelining allowed'

##
## Basic StupidRPC
##

class StupidRPC(basic.NetstringReceiver):
    waitingForArgs = None
    dispatching = False

    def connectionMade(self):
        self.gotArgs = []

    def clean(self):
        self.dispatching = False
        self.gotArgs = []
        self.currMeth = None

    def sendSuccess(self, result):
        if not self.dispatching:
            log.msg("warning: sending success when not dispatching")
        self.clean()
        self.sendString('Success')
        self.sendString(result)
    
    def sendFailure(self, type, result=''):
        if not self.dispatching:
            log.msg("warning: sending failure when not dispatching")
        self.clean()
        self.sendString('Failure')
        self.sendString(type)
        self.sendString(result)

    def stringReceived(self, line):
        if self.dispatching:
            self.sendFailure(DONT_PIPELINE)
            self.loseConnection()

        if self.waitingForArgs:
            # An argument
            coercer = self.waitingForArgs.pop(0)
            try:
                v = coercer(line)
            except:
                f = failure.Failure()
                log.err(f)
                self.sendFailure(BAD_ARGUMENT, f.getErrorTraceback())
            else:
                self.gotArgs.append(v)
                if not self.waitingForArgs:
                    # that was all the args we needed
                    args = self.gotArgs
                    self.dispatching = True
                    self.currMeth(*args)

        else:
            # Beginning of a method call
            self.currMeth = self.findMethod(line)
            if not self.currMeth:
                self.sendFailure(NO_SUCH_METHOD)
            else:
                self.waitingForArgs = list(self.currMeth.sig)

    def findMethod(self, name):
        return getattr(self, 'remote_' + name, None)


##
## Cred integration
##

AUTH_SUCCESS = 'Authentication Successful'
AUTH_FAILURE = 'Authentication Failure'

from twisted.cred import credentials
from twisted.python import components

class IStupid(components.Interface):
    """remote_ methods"""

class AuthServer(StupidRPC):

    root = None

    def findMethod(self, name):
        if self.root:
            return getattr(self.root, 'remote_'+name, None)
        else:
            return StupidRPC.findMethod(self, name)


    def remote_auth(self, name, password):
        print "trying to login with ", repr(name), repr(password)
        d = self.factory.portal.login(
            credentials.UsernamePassword(name, password),
            None,
            IStupid)
        d.addCallback(self._cbGotRoot)
        d.addErrback(self._ebNoRoot)
    remote_auth.sig = (str, str)

    def _cbGotRoot(self, root):
        print "HELLO CBGOTROOT"
        self.root = root
        root.proto = self
        self.sendSuccess(AUTH_SUCCESS)

    def _ebNoRoot(self, f):
        print "HELLOEBNOROOT"
        log.err(f)
        self.sendFailure(AUTH_FAILURE)

##
## Capability Server
##

def ipify(ipstr):
    assert len(ipstr) < 16
    assert ipstr.count('.') == 3
    return ipstr

class CapServer:

    def remote_bindPort(self, interface, portno):
        print "HEY!", interface
        self.proto.sendSuccess("<3")
    remote_bindPort.sig = (ipify, int)


def makeAuthFactory(rootFactory, checker):
    """
    Convenience.
    """
    from twisted.cred import portal
    f = protocol.Factory()
    f.protocol = AuthServer
    class Realm:
        def requestAvatar(self, name, mind, iface):
            assert iface is IStupid, iface
            return rootFactory()
    f.portal = portal.Portal(Realm())
    f.portal.registerChecker(checker)
    return f

def main():
    import sys
    from twisted.internet import reactor
    from twisted.cred import checkers
    reactor.listenTCP(1025,makeAuthFactory(CapServer,
                           checkers.InMemoryUsernamePasswordDatabaseDontUse(radix='secret')))

    log.startLogging(sys.stdout)
    reactor.run()

if __name__ == '__main__':
    main()
