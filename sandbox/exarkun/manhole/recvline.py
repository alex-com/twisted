
import string

import insults

from twisted.python import log

class RecvLine(insults.TerminalProtocol):
    width = 80
    height = 24

    TABSTOP = 4

    lineDelimiter = '\n'

    ps = ('>>> ', '... ')
    pn = 0

    def connectionMade(self):
        # A list containing the characters making up the current line
        self.lineBuffer = []

        # A zero-based (wtf else?) index into self.lineBuffer.
        # Indicates the current cursor position.
        self.lineBufferIndex = 0

        t = self.transport
        # A map of keyIDs to bound instance methods.
        self.keyHandlers = {
            t.LEFT_ARROW: self.handle_LEFT,
            t.RIGHT_ARROW: self.handle_RIGHT,
            self.lineDelimiter: self.handle_RETURN,
            '\x7f': self.handle_BACKSPACE,
            '\t': self.handle_TAB,
            t.DELETE: self.handle_DELETE,
            t.INSERT: self.handle_INSERT,
            t.HOME: self.handle_HOME,
            t.END: self.handle_END}

        self.initializeScreen()

    def initializeScreen(self):
        # Hmm, state sucks.  Oh well.
        # For now we will just take over the whole terminal.
        self.transport.reset()
        self.transport.write(self.ps[self.pn])
        self.setInsertMode()

    def setInsertMode(self):
        self.mode = 'insert'
        self.transport.setMode([insults.IRM])

    def setTypeoverMode(self):
        self.mode = 'typeover'
        self.transport.resetMode([insults.IRM])

    def terminalSize(self, width, height):
        # XXX - Clear the previous input line, redraw it at the new cursor position
        self.transport.reset()
        self.width = width
        self.height = height
        self.transport.write(self.ps[self.pn] + ''.join(self.lineBuffer))

    def unhandledControlSequence(self, seq):
        print "Don't know about", repr(seq)

    def setMode(self, modes):
        print 'Setting', modes

    def resetMode(self, modes):
        print 'Resetting', modes

    def keystrokeReceived(self, keyID):
        m = self.keyHandlers.get(keyID)
        if m is not None:
            m()
        elif keyID in string.printable:
            self.characterReceived(keyID)
        else:
            log.msg("Received unhandled keyID: %r" % (keyID,))

    def characterReceived(self, ch):
        if self.mode == 'insert':
            self.lineBuffer.insert(self.lineBufferIndex, ch)
        else:
            self.lineBuffer[self.lineBufferIndex:self.lineBufferIndex+1] = [ch]
        self.lineBufferIndex += 1
        self.transport.write(ch)

    def handle_TAB(self):
        n = self.TABSTOP - (len(self.lineBuffer) % self.TABSTOP)
        self.transport.cursorForward(n)
        self.lineBufferIndex += n
        self.lineBuffer.extend(' ' * n)

    def handle_LEFT(self):
        if self.lineBufferIndex > 0:
            self.lineBufferIndex -= 1
            self.transport.cursorBackward()

    def handle_RIGHT(self):
        if self.lineBufferIndex < len(self.lineBuffer):
            self.lineBufferIndex += 1
            self.transport.cursorForward()

    def handle_HOME(self):
        if self.lineBufferIndex:
            self.transport.cursorBackward(self.lineBufferIndex)
            self.lineBufferIndex = 0

    def handle_END(self):
        offset = len(self.lineBuffer) - self.lineBufferIndex
        if offset:
            self.transport.cursorForward(offset)
            self.lineBufferIndex = len(self.lineBuffer)

    def handle_BACKSPACE(self):
        if self.lineBufferIndex > 0:
            self.lineBufferIndex -= 1
            del self.lineBuffer[self.lineBufferIndex]
            self.transport.cursorBackward()
            self.transport.deleteCharacter()

    def handle_DELETE(self):
        if self.lineBufferIndex < len(self.lineBuffer) - 1:
            del self.lineBuffer[self.lineBufferIndex]
            self.transport.deleteCharacter()

    def handle_RETURN(self):
        line = ''.join(self.lineBuffer)
        self.lineBuffer = []
        self.lineBufferIndex = 0
        self.transport.nextLine()
        self.lineReceived(line)

    def handle_INSERT(self):
        if self.mode == 'typeover':
            self.setInsertMode()
        else:
            self.setTypeoverMode()

    def lineReceived(self, line):
        pass

class HistoricRecvLine(RecvLine):
    def connectionMade(self):
        RecvLine.connectionMade(self)

        self.historyLines = []
        self.historyPosition = 0

        t = self.transport
        self.keyHandlers.update({t.UP_ARROW: self.handle_UP,
                                 t.DOWN_ARROW: self.handle_DOWN})

    def handle_UP(self):
        if self.lineBuffer and self.historyPosition == len(self.historyLines):
            self.historyLines.append(self.lineBuffer)
        if self.historyPosition > 0:
            self.handle_HOME()
            self.transport.eraseToLineEnd()

            self.historyPosition -= 1
            self.lineBuffer = list(self.historyLines[self.historyPosition])
            self.transport.write(''.join(self.lineBuffer))
            self.lineBufferIndex = len(self.lineBuffer)

    def handle_DOWN(self):
        if self.historyPosition < len(self.historyLines) - 1:
            self.handle_HOME()
            self.transport.eraseToLineEnd()

            self.historyPosition += 1
            self.lineBuffer = list(self.historyLines[self.historyPosition])
            self.transport.write(''.join(self.lineBuffer))
            self.lineBufferIndex = len(self.lineBuffer)
        else:
            self.handle_HOME()
            self.transport.eraseToLineEnd()

            self.historyPosition = len(self.historyLines)
            self.lineBuffer = []
            self.lineBufferIndex = 0

    def handle_RETURN(self):
        if self.lineBuffer:
            self.historyLines.append(''.join(self.lineBuffer))
        self.historyPosition = len(self.historyLines)
        return RecvLine.handle_RETURN(self)
