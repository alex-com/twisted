# Copyright (c) 2001-2004 Twisted Matrix Laboratories.
# See LICENSE for details.


"""
Test cases for twisted.mail.pop3 module.
"""

import StringIO
import string
import hmac
import base64
import itertools

from zope.interface import implements

from twisted.internet import defer

from twisted.trial import unittest, util
from twisted import mail
import twisted.mail.protocols
import twisted.mail.pop3
import twisted.internet.protocol
from twisted import internet
from twisted.mail import pop3
from twisted.protocols import loopback
from twisted.python import failure

from twisted import cred
import twisted.cred.portal
import twisted.cred.checkers
import twisted.cred.credentials

from twisted.test.proto_helpers import LineSendingProtocol


class UtilityTestCase(unittest.TestCase):
    """
    Test the various helper functions and classes used by the POP3 server
    protocol implementation.
    """

    def testLineBuffering(self):
        """
        Test creating a LineBuffer and feeding it some lines.  The lines should
        build up in its internal buffer for a while and then get spat out to
        the writer.
        """
        output = []
        input = iter(itertools.cycle(['012', '345', '6', '7', '8', '9']))
        c = pop3._IteratorBuffer(output.extend, input, 6)
        i = iter(c)
        self.assertEquals(output, []) # nothing is buffer
        i.next()
        self.assertEquals(output, []) # '012' is buffered
        i.next()
        self.assertEquals(output, []) # '012345' is buffered
        i.next()
        self.assertEquals(output, ['012', '345', '6']) # nothing is buffered
        for n in range(5):
            i.next()
        self.assertEquals(output, ['012', '345', '6', '7', '8', '9', '012', '345'])


    def testFinishLineBuffering(self):
        """
        Test that a LineBuffer flushes everything when its iterator is
        exhausted, and itself raises StopIteration.
        """
        output = []
        input = iter(['a', 'b', 'c'])
        c = pop3._IteratorBuffer(output.extend, input, 5)
        for i in c:
            pass
        self.assertEquals(output, ['a', 'b', 'c'])


    def testSuccessResponseFormatter(self):
        """
        Test that the thing that spits out POP3 'success responses' works
        right.
        """
        self.assertEquals(
            pop3.successResponse('Great.'),
            '+OK Great.\r\n')


    def testStatLineFormatter(self):
        """
        Test that the function which formats stat lines does so appropriately.
        """
        statLine = list(pop3.formatStatResponse([]))[-1]
        self.assertEquals(statLine, '+OK 0 0\r\n')

        statLine = list(pop3.formatStatResponse([10, 31, 0, 10101]))[-1]
        self.assertEquals(statLine, '+OK 4 10142\r\n')


    def testListLineFormatter(self):
        """
        Test that the function which formats the lines in response to a LIST
        command does so appropriately.
        """
        listLines = list(pop3.formatListResponse([]))
        self.assertEquals(
            listLines,
            ['+OK 0\r\n', '.\r\n'])

        listLines = list(pop3.formatListResponse([1, 2, 3, 100]))
        self.assertEquals(
            listLines,
            ['+OK 4\r\n', '1 1\r\n', '2 2\r\n', '3 3\r\n', '4 100\r\n', '.\r\n'])



    def testUIDListLineFormatter(self):
        """
        Test that the function which formats lines in response to a UIDL
        command does so appropriately.
        """
        UIDs = ['abc', 'def', 'ghi']
        listLines = list(pop3.formatUIDListResponse([], UIDs.__getitem__))
        self.assertEquals(
            listLines,
            ['+OK \r\n', '.\r\n'])

        listLines = list(pop3.formatUIDListResponse([123, 431, 591], UIDs.__getitem__))
        self.assertEquals(
            listLines,
            ['+OK \r\n', '1 abc\r\n', '2 def\r\n', '3 ghi\r\n', '.\r\n'])

        listLines = list(pop3.formatUIDListResponse([0, None, 591], UIDs.__getitem__))
        self.assertEquals(
            listLines,
            ['+OK \r\n', '1 abc\r\n', '3 ghi\r\n', '.\r\n'])



class MyVirtualPOP3(mail.protocols.VirtualPOP3):

    magic = '<moshez>'

    def authenticateUserAPOP(self, user, digest):
        user, domain = self.lookupDomain(user)
        return self.service.domains['baz.com'].authenticateUserAPOP(user, digest, self.magic, domain)

class DummyDomain:

   def __init__(self):
       self.users = {}

   def addUser(self, name):
       self.users[name] = []

   def addMessage(self, name, message):
       self.users[name].append(message)

   def authenticateUserAPOP(self, name, digest, magic, domain):
       return pop3.IMailbox, ListMailbox(self.users[name]), lambda: None


class ListMailbox:

    def __init__(self, list):
        self.list = list

    def listMessages(self, i=None):
        if i is None:
            return map(len, self.list)
        return len(self.list[i])

    def getMessage(self, i):
        return StringIO.StringIO(self.list[i])

    def getUidl(self, i):
        return i

    def deleteMessage(self, i):
        self.list[i] = ''

    def sync(self):
        pass

class MyPOP3Downloader(pop3.POP3Client):

    def handle_WELCOME(self, line):
        pop3.POP3Client.handle_WELCOME(self, line)
        self.apop('hello@baz.com', 'world')

    def handle_APOP(self, line):
        parts = line.split()
        code = parts[0]
        data = (parts[1:] or ['NONE'])[0]
        if code != '+OK':
            print parts
            raise AssertionError, 'code is ' + code
        self.lines = []
        self.retr(1)

    def handle_RETR_continue(self, line):
        self.lines.append(line)

    def handle_RETR_end(self):
        self.message = '\n'.join(self.lines) + '\n'
        self.quit()

    def handle_QUIT(self, line):
        if line[:3] != '+OK':
            raise AssertionError, 'code is ' + line


class POP3TestCase(unittest.TestCase):

    message = '''\
Subject: urgent

Someone set up us the bomb!
'''

    expectedOutput = '''\
+OK <moshez>\015
+OK Authentication succeeded\015
+OK \015
1 0\015
.\015
+OK %d\015
Subject: urgent\015
\015
Someone set up us the bomb!\015
.\015
+OK \015
''' % len(message)

    def setUp(self):
        self.factory = internet.protocol.Factory()
        self.factory.domains = {}
        self.factory.domains['baz.com'] = DummyDomain()
        self.factory.domains['baz.com'].addUser('hello')
        self.factory.domains['baz.com'].addMessage('hello', self.message)

    def testMessages(self):
        client = LineSendingProtocol([
            'APOP hello@baz.com world',
            'UIDL',
            'RETR 1',
            'QUIT',
        ])
        server =  MyVirtualPOP3()
        server.service = self.factory
        def check(ignored):
            output = '\r\n'.join(client.response) + '\r\n'
            self.assertEquals(output, self.expectedOutput)
        return loopback.loopbackTCP(server, client).addCallback(check)

    def testLoopback(self):
        protocol =  MyVirtualPOP3()
        protocol.service = self.factory
        clientProtocol = MyPOP3Downloader()
        loopback.loopback(protocol, clientProtocol)
        self.failUnlessEqual(clientProtocol.message, self.message)
        protocol.connectionLost(failure.Failure(Exception("Test harness disconnect")))
    testLoopback.suppress = [util.suppress(message="twisted.mail.pop3.POP3Client is deprecated")]



class DummyPOP3(pop3.POP3):

    magic = '<moshez>'

    def authenticateUserAPOP(self, user, password):
        return pop3.IMailbox, DummyMailbox(), lambda: None

class DummyMailbox(pop3.Mailbox):

    messages = [
'''\
From: moshe
To: moshe

How are you, friend?
''']

    def __init__(self):
        self.messages = DummyMailbox.messages[:]

    def listMessages(self, i=None):
        if i is None:
            return map(len, self.messages)
        return len(self.messages[i])

    def getMessage(self, i):
        return StringIO.StringIO(self.messages[i])

    def getUidl(self, i):
        if i >= len(self.messages):
            raise ValueError()
        return str(i)

    def deleteMessage(self, i):
        self.messages[i] = ''


class AnotherPOP3TestCase(unittest.TestCase):

    def runTest(self, lines, expected):
        dummy = DummyPOP3()
        client = LineSendingProtocol([
            "APOP moshez dummy",
            "LIST",
            "UIDL",
            "RETR 1",
            "RETR 2",
            "DELE 1",
            "RETR 1",
            "QUIT",
        ])
        expected_output = '+OK <moshez>\r\n+OK Authentication succeeded\r\n+OK 1\r\n1 44\r\n.\r\n+OK \r\n1 0\r\n.\r\n+OK 44\r\nFrom: moshe\r\nTo: moshe\r\n\r\nHow are you, friend?\r\n.\r\n-ERR Bad message number argument\r\n+OK \r\n-ERR message deleted\r\n+OK \r\n'
        loopback.loopback(dummy, client)
        self.failUnlessEqual(expected_output, '\r\n'.join(client.response) + '\r\n')
        dummy.connectionLost(failure.Failure(Exception("Test harness disconnect")))


    def testBuffer(self):
        lines = string.split('''\
APOP moshez dummy
LIST
UIDL
RETR 1
RETR 2
DELE 1
RETR 1
QUIT''', '\n')
        expected_output = '+OK <moshez>\r\n+OK Authentication succeeded\r\n+OK 1\r\n1 44\r\n.\r\n+OK \r\n1 0\r\n.\r\n+OK 44\r\nFrom: moshe\r\nTo: moshe\r\n\r\nHow are you, friend?\r\n.\r\n-ERR Bad message number argument\r\n+OK \r\n-ERR message deleted\r\n+OK \r\n'
        self.runTest(lines, expected_output)

    def testNoop(self):
        lines = ['APOP spiv dummy', 'NOOP', 'QUIT']
        expected_output = '+OK <moshez>\r\n+OK Authentication succeeded\r\n+OK \r\n+OK \r\n'
        self.runTest(lines, expected_output)

    def testAuthListing(self):
        p = DummyPOP3()
        p.factory = internet.protocol.Factory()
        p.factory.challengers = {'Auth1': None, 'secondAuth': None, 'authLast': None}
        client = LineSendingProtocol([
            "AUTH",
            "QUIT",
        ])

        loopback.loopback(p, client)
        self.failUnless(client.response[1].startswith('+OK'))
        self.assertEquals(client.response[2:6], ["AUTH1", "SECONDAUTH", "AUTHLAST", "."])

    def testIllegalPASS(self):
        dummy = DummyPOP3()
        client = LineSendingProtocol([
            "PASS fooz",
            "QUIT"
        ])
        expected_output = '+OK <moshez>\r\n-ERR USER required before PASS\r\n+OK \r\n'
        loopback.loopback(dummy, client)
        self.failUnlessEqual(expected_output, '\r\n'.join(client.response) + '\r\n')
        dummy.connectionLost(failure.Failure(Exception("Test harness disconnect")))

    def testEmptyPASS(self):
        dummy = DummyPOP3()
        client = LineSendingProtocol([
            "PASS ",
            "QUIT"
        ])
        expected_output = '+OK <moshez>\r\n-ERR USER required before PASS\r\n+OK \r\n'
        loopback.loopback(dummy, client)
        self.failUnlessEqual(expected_output, '\r\n'.join(client.response) + '\r\n')
        dummy.connectionLost(failure.Failure(Exception("Test harness disconnect")))


class TestServerFactory:
    implements(pop3.IServerFactory)

    def cap_IMPLEMENTATION(self):
        return "Test Implementation String"

    def cap_EXPIRE(self):
        return 60

    challengers = {"SCHEME_1": None, "SCHEME_2": None}

    def cap_LOGIN_DELAY(self):
        return 120

    pue = True
    def perUserExpiration(self):
        return self.pue

    puld = True
    def perUserLoginDelay(self):
        return self.puld


class TestMailbox:
    loginDelay = 100
    messageExpiration = 25


class CapabilityTestCase(unittest.TestCase):
    def setUp(self):
        s = StringIO.StringIO()
        p = pop3.POP3()
        p.factory = TestServerFactory()
        p.transport = internet.protocol.FileWrapper(s)
        p.connectionMade()
        p.do_CAPA()

        self.caps = p.listCapabilities()
        self.pcaps = s.getvalue().splitlines()

        s = StringIO.StringIO()
        p.mbox = TestMailbox()
        p.transport = internet.protocol.FileWrapper(s)
        p.do_CAPA()

        self.lpcaps = s.getvalue().splitlines()
        p.connectionLost(failure.Failure(Exception("Test harness disconnect")))

    def contained(self, s, *caps):
        for c in caps:
            self.assertIn(s, c)

    def testUIDL(self):
        self.contained("UIDL", self.caps, self.pcaps, self.lpcaps)

    def testTOP(self):
        self.contained("TOP", self.caps, self.pcaps, self.lpcaps)

    def testUSER(self):
        self.contained("USER", self.caps, self.pcaps, self.lpcaps)

    def testEXPIRE(self):
        self.contained("EXPIRE 60 USER", self.caps, self.pcaps)
        self.contained("EXPIRE 25", self.lpcaps)

    def testIMPLEMENTATION(self):
        self.contained(
            "IMPLEMENTATION Test Implementation String",
            self.caps, self.pcaps, self.lpcaps
        )

    def testSASL(self):
        self.contained(
            "SASL SCHEME_1 SCHEME_2",
            self.caps, self.pcaps, self.lpcaps
        )

    def testLOGIN_DELAY(self):
        self.contained("LOGIN-DELAY 120 USER", self.caps, self.pcaps)
        self.assertIn("LOGIN-DELAY 100", self.lpcaps)



class GlobalCapabilitiesTestCase(unittest.TestCase):
    def setUp(self):
        s = StringIO.StringIO()
        p = pop3.POP3()
        p.factory = TestServerFactory()
        p.factory.pue = p.factory.puld = False
        p.transport = internet.protocol.FileWrapper(s)
        p.connectionMade()
        p.do_CAPA()

        self.caps = p.listCapabilities()
        self.pcaps = s.getvalue().splitlines()

        s = StringIO.StringIO()
        p.mbox = TestMailbox()
        p.transport = internet.protocol.FileWrapper(s)
        p.do_CAPA()

        self.lpcaps = s.getvalue().splitlines()
        p.connectionLost(failure.Failure(Exception("Test harness disconnect")))

    def contained(self, s, *caps):
        for c in caps:
            self.assertIn(s, c)

    def testEXPIRE(self):
        self.contained("EXPIRE 60", self.caps, self.pcaps, self.lpcaps)

    def testLOGIN_DELAY(self):
        self.contained("LOGIN-DELAY 120", self.caps, self.pcaps, self.lpcaps)



class TestRealm:
    def requestAvatar(self, avatarId, mind, *interfaces):
        if avatarId == 'testuser':
            return pop3.IMailbox, DummyMailbox(), lambda: None
        assert False



class SASLTestCase(unittest.TestCase):
    def testValidLogin(self):
        p = pop3.POP3()
        p.factory = TestServerFactory()
        p.factory.challengers = {'CRAM-MD5': cred.credentials.CramMD5Credentials}
        p.portal = cred.portal.Portal(TestRealm())
        ch = cred.checkers.InMemoryUsernamePasswordDatabaseDontUse()
        ch.addUser('testuser', 'testpassword')
        p.portal.registerChecker(ch)

        s = StringIO.StringIO()
        p.transport = internet.protocol.FileWrapper(s)
        p.connectionMade()

        p.lineReceived("CAPA")
        self.failUnless(s.getvalue().find("SASL CRAM-MD5") >= 0)

        p.lineReceived("AUTH CRAM-MD5")
        chal = s.getvalue().splitlines()[-1][2:]
        chal = base64.decodestring(chal)
        response = hmac.HMAC('testpassword', chal).hexdigest()

        p.lineReceived(base64.encodestring('testuser ' + response).rstrip('\n'))
        self.failUnless(p.mbox)
        self.failUnless(s.getvalue().splitlines()[-1].find("+OK") >= 0)
        p.connectionLost(failure.Failure(Exception("Test harness disconnect")))



class CommandTestCase(unittest.TestCase):
    """
    Tests for all the commands a POP3 server is allowed to receive.
    """

    extraMessage = '''\
From: guy
To: fellow

More message text for you.
'''


    def setUp(self):
        """
        Make a POP3 server protocol instance hooked up to a simple mailbox and
        a transport that buffers output to a StringIO.
        """
        p = pop3.POP3()
        p.mbox = DummyMailbox()
        p.schedule = list
        self.pop3Server = p

        s = StringIO.StringIO()
        p.transport = internet.protocol.FileWrapper(s)
        p.connectionMade()
        s.truncate(0)
        self.pop3Transport = s


    def tearDown(self):
        """
        Disconnect the server protocol so it can clean up anything it might
        need to clean up.
        """
        self.pop3Server.connectionLost(failure.Failure(Exception("Test harness disconnect")))


    def _flush(self):
        """
        Do some of the things that the reactor would take care of, if the
        reactor were actually running.
        """
        # Oh man FileWrapper is pooh.
        self.pop3Server.transport._checkProducer()


    def testLIST(self):
        """
        Test the two forms of list: with a message index number, which should
        return a short-form response, and without a message index number, which
        should return a long-form response, one line per message.
        """
        p = self.pop3Server
        s = self.pop3Transport

        p.lineReceived("LIST 1")
        self._flush()
        self.assertEquals(s.getvalue(), "+OK 1 44\r\n")
        s.truncate(0)

        p.lineReceived("LIST")
        self._flush()
        self.assertEquals(s.getvalue(), "+OK 1\r\n1 44\r\n.\r\n")


    def testLISTWithBadArgument(self):
        """
        Test that non-integers and out-of-bound integers produce appropriate
        error responses.
        """
        p = self.pop3Server
        s = self.pop3Transport

        p.lineReceived("LIST a")
        self.assertEquals(
            s.getvalue(),
            "-ERR Invalid message-number: 'a'\r\n")
        s.truncate(0)

        p.lineReceived("LIST 0")
        self.assertEquals(
            s.getvalue(),
            "-ERR Invalid message-number: 0\r\n")
        s.truncate(0)

        p.lineReceived("LIST 2")
        self.assertEquals(
            s.getvalue(),
            "-ERR Invalid message-number: 2\r\n")
        s.truncate(0)


    def testUIDL(self):
        """
        Test the two forms of the UIDL command.  These are just like the two
        forms of the LIST command.
        """
        p = self.pop3Server
        s = self.pop3Transport

        p.lineReceived("UIDL 1")
        self.assertEquals(s.getvalue(), "+OK 0\r\n")
        s.truncate(0)

        p.lineReceived("UIDL")
        self._flush()
        self.assertEquals(s.getvalue(), "+OK \r\n1 0\r\n.\r\n")


    def testUIDLWithBadArgument(self):
        """
        Test that UIDL with a non-integer or an out-of-bounds integer produces
        the appropriate error response.
        """
        p = self.pop3Server
        s = self.pop3Transport

        p.lineReceived("UIDL a")
        self.assertEquals(
            s.getvalue(),
            "-ERR Bad message number argument\r\n")
        s.truncate(0)

        p.lineReceived("UIDL 0")
        self.assertEquals(
            s.getvalue(),
            "-ERR Bad message number argument\r\n")
        s.truncate(0)

        p.lineReceived("UIDL 2")
        self.assertEquals(
            s.getvalue(),
            "-ERR Bad message number argument\r\n")
        s.truncate(0)


    def testSTAT(self):
        """
        Test the single form of the STAT command, which returns a short-form
        response of the number of messages in the mailbox and their total size.
        """
        p = self.pop3Server
        s = self.pop3Transport

        p.lineReceived("STAT")
        self._flush()
        self.assertEquals(s.getvalue(), "+OK 1 44\r\n")


    def testRETR(self):
        """
        Test downloading a message.
        """
        p = self.pop3Server
        s = self.pop3Transport

        p.lineReceived("RETR 1")
        self._flush()
        self.assertEquals(
            s.getvalue(),
            "+OK 44\r\n"
            "From: moshe\r\n"
            "To: moshe\r\n"
            "\r\n"
            "How are you, friend?\r\n"
            ".\r\n")
        s.truncate(0)


    def testRETRWithBadArgument(self):
        """
        Test that trying to download a message with a bad argument, either not
        an integer or an out-of-bounds integer, fails with the appropriate
        error response.
        """
        p = self.pop3Server
        s = self.pop3Transport

        p.lineReceived("RETR a")
        self.assertEquals(
            s.getvalue(),
            "-ERR Bad message number argument\r\n")
        s.truncate(0)

        p.lineReceived("RETR 0")
        self.assertEquals(
            s.getvalue(),
            "-ERR Bad message number argument\r\n")
        s.truncate(0)

        p.lineReceived("RETR 2")
        self.assertEquals(
            s.getvalue(),
            "-ERR Bad message number argument\r\n")
        s.truncate(0)


    def testTOP(self):
        """
        Test downloading the headers and part of the body of a message.
        """
        p = self.pop3Server
        s = self.pop3Transport
        p.mbox.messages.append(self.extraMessage)

        p.lineReceived("TOP 1 0")
        self._flush()
        self.assertEquals(
            s.getvalue(),
            "+OK Top of message follows\r\n"
            "From: moshe\r\n"
            "To: moshe\r\n"
            "\r\n"
            ".\r\n")


    def testTOPWithBadArgument(self):
        """
        Test that trying to download a message with a bad argument, either a
        message number which isn't an integer or is an out-of-bounds integer or
        a number of lines which isn't an integer or is a negative integer,
        fails with the appropriate error response.
        """
        p = self.pop3Server
        s = self.pop3Transport
        p.mbox.messages.append(self.extraMessage)

        p.lineReceived("TOP 1 a")
        self.assertEquals(
            s.getvalue(),
            "-ERR Bad line count argument\r\n")
        s.truncate(0)

        p.lineReceived("TOP 1 -1")
        self.assertEquals(
            s.getvalue(),
            "-ERR Bad line count argument\r\n")
        s.truncate(0)

        p.lineReceived("TOP a 1")
        self.assertEquals(
            s.getvalue(),
            "-ERR Bad message number argument\r\n")
        s.truncate(0)

        p.lineReceived("TOP 0 1")
        self.assertEquals(
            s.getvalue(),
            "-ERR Bad message number argument\r\n")
        s.truncate(0)

        p.lineReceived("TOP 3 1")
        self.assertEquals(
            s.getvalue(),
            "-ERR Bad message number argument\r\n")
        s.truncate(0)


    def testLAST(self):
        """
        Test the exceedingly pointless LAST command, which tells you the
        highest message index which you have already downloaded.
        """
        p = self.pop3Server
        s = self.pop3Transport
        p.mbox.messages.append(self.extraMessage)

        p.lineReceived('LAST')
        self.assertEquals(
            s.getvalue(),
            "+OK 0\r\n")
        s.truncate(0)


    def testRetrieveUpdatesHighest(self):
        """
        Test that issuing a RETR command updates the LAST response.
        """
        p = self.pop3Server
        s = self.pop3Transport
        p.mbox.messages.append(self.extraMessage)

        p.lineReceived('RETR 2')
        self._flush()
        s.truncate(0)
        p.lineReceived('LAST')
        self.assertEquals(
            s.getvalue(),
            '+OK 2\r\n')
        s.truncate(0)


    def testTopUpdatesHighest(self):
        """
        Test that issuing a TOP command updates the LAST response.
        """
        p = self.pop3Server
        s = self.pop3Transport
        p.mbox.messages.append(self.extraMessage)

        p.lineReceived('TOP 2 10')
        self._flush()
        s.truncate(0)
        p.lineReceived('LAST')
        self.assertEquals(
            s.getvalue(),
            '+OK 2\r\n')


    def testHighestOnlyProgresses(self):
        """
        Test that downloading a message with a smaller index than the current
        LAST response doesn't change the LAST response.
        """
        p = self.pop3Server
        s = self.pop3Transport
        p.mbox.messages.append(self.extraMessage)

        p.lineReceived('RETR 2')
        self._flush()
        p.lineReceived('TOP 1 10')
        self._flush()
        s.truncate(0)
        p.lineReceived('LAST')
        self.assertEquals(
            s.getvalue(),
            '+OK 2\r\n')


    def testResetClearsHighest(self):
        """
        Test that issuing RSET changes the LAST response to 0.
        """
        p = self.pop3Server
        s = self.pop3Transport
        p.mbox.messages.append(self.extraMessage)

        p.lineReceived('RETR 2')
        self._flush()
        p.lineReceived('RSET')
        s.truncate(0)
        p.lineReceived('LAST')
        self.assertEquals(
            s.getvalue(),
            '+OK 0\r\n')




class SyncDeferredMailbox(DummyMailbox):
    """
    Mailbox which has a listMessages implementation which returns a Deferred
    which has already fired.
    """
    def listMessages(self, n=None):
        return defer.succeed(DummyMailbox.listMessages(self, n))



class SyncDeferredCommandTestCase(CommandTestCase):
    """
    Run all of the L{CommandTestCase} tests with a synchronous-Deferred
    returning IMailbox implementation.
    """
    def setUp(self):
        CommandTestCase.setUp(self)
        self.pop3Server.mbox = SyncDeferredMailbox()



class AsyncDeferredMailbox(DummyMailbox):
    """
    Mailbox which has a listMessages implementation which returns a Deferred
    which has not yet fired.
    """
    def __init__(self):
        self.waiting = []
        DummyMailbox.__init__(self)


    def listMessages(self, n=None):
        d = defer.Deferred()
        # See AsyncDeferredMailbox._flush
        self.waiting.append((d, DummyMailbox.listMessages(self, n)))
        return d



class AsyncDeferredCommandTestCase(CommandTestCase):
    """
    Run all of the L{CommandTestCase} tests with an asynchronous-Deferred
    returning IMailbox implementation.
    """
    def setUp(self):
        CommandTestCase.setUp(self)
        self.pop3Server.mbox = AsyncDeferredMailbox()


    def _flush(self):
        """
        Fire whatever Deferreds we've built up in our mailbox.
        """
        while self.pop3Server.mbox.waiting:
            d, a = self.pop3Server.mbox.waiting.pop()
            d.callback(a)
        CommandTestCase._flush(self)
