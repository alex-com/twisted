
from twisted.conch import avatar, interfaces as iconch, error as econch
from twisted.conch.ssh import factory, keys, session
from twisted.cred import credentials, checkers, portal

import insults

class TerminalUser(avatar.ConchUser):
    def __init__(self):
        avatar.ConchUser.__init__(self)
        self.channelLookup['session'] = session.SSHSession

class TerminalRealm:
    def requestAvatar(self, avatarId, mind, *interfaces):
        for i in interfaces:
            if i is iconch.IConchUser:
                return (iconch.IConchUser, TerminalUser(), lambda: None)
        raise NotImplementedError()

class _Ugg:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, name):
        raise AttributeError(self.name, "has no attribute", name)

class TerminalSessionTransport:
    protocolFactory = insults.ServerProtocol

    def __init__(self, proto, avatar):
        self.proto = proto
        self.avatar = avatar
        self.chainedProtocol = self.protocolFactory()

        self.proto.makeConnection(_Ugg(write=self.chainedProtocol.dataReceived,
                                       name="SSH Proto Transport"))
        self.chainedProtocol.makeConnection(_Ugg(write=self.proto.write,
                                                 name="Chained Proto Transport"))

class TerminalSession:
    transportFactory = TerminalSessionTransport

    def __init__(self, avatar):
        self.avatar = avatar

    def getPty(self, term, windowSize, attrs):
        pass

    def openShell(self, proto):
        self.transportFactory(proto, self.avatar)

    def execCommand(self, proto, cmd):
        raise econch.ConchError("Cannot execute commands")

    def closed(self):
        pass

class ConchFactory(factory.SSHFactory):
    publicKey = 'ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAGEArzJx8OYOnJmzf4tfBEvLi8DVPrJ3/c9k2I/Az64fxjHf9imyRJbixtQhlH9lfNjUIx+4LmrJH5QNRsFporcHDKOTwTTYLh5KmRpslkYHRivcJSkbh/C+BR3utDS555mV'

    publicKeys = {
        'ssh-rsa' : keys.getPublicKeyString(data = publicKey)
    }
    del publicKey

    privateKey = """-----BEGIN RSA PRIVATE KEY-----
MIIByAIBAAJhAK8ycfDmDpyZs3+LXwRLy4vA1T6yd/3PZNiPwM+uH8Yx3/YpskSW
4sbUIZR/ZXzY1CMfuC5qyR+UDUbBaaK3Bwyjk8E02C4eSpkabJZGB0Yr3CUpG4fw
vgUd7rQ0ueeZlQIBIwJgbh+1VZfr7WftK5lu7MHtqE1S1vPWZQYE3+VUn8yJADyb
Z4fsZaCrzW9lkIqXkE3GIY+ojdhZhkO1gbG0118sIgphwSWKRxK0mvh6ERxKqIt1
xJEJO74EykXZV4oNJ8sjAjEA3J9r2ZghVhGN6V8DnQrTk24Td0E8hU8AcP0FVP+8
PQm/g/aXf2QQkQT+omdHVEJrAjEAy0pL0EBH6EVS98evDCBtQw22OZT52qXlAwZ2
gyTriKFVoqjeEjt3SZKKqXHSApP/AjBLpF99zcJJZRq2abgYlf9lv1chkrWqDHUu
DZttmYJeEfiFBBavVYIF1dOlZT0G8jMCMBc7sOSZodFnAiryP+Qg9otSBjJ3bQML
pSTqy7c3a2AScC/YyOwkDaICHnnD3XyjMwIxALRzl0tQEKMXs6hH8ToUdlLROCrP
EhQ0wahUTCk1gKA4uPD6TMTChavbh4K63OvbKg==
-----END RSA PRIVATE KEY-----"""
    privateKeys = {
        'ssh-rsa' : keys.getPrivateKeyObject(data = privateKey)
    }
    del privateKey

    def __init__(self):
        self.portal = portal.Portal(TerminalRealm(), [checkers.InMemoryUsernamePasswordDatabaseDontUse(username='password')])
