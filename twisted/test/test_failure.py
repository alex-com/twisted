
# Twisted, the Framework of Your Internet
# Copyright (C) 2001 Matthew W. Lefkowitz
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


"""
Test cases for failure module.
"""

import sys
import StringIO

from twisted.trial import unittest, util


from twisted.python import failure


class FailureTestCase(unittest.TestCase):

    def testFailAndTrap(self):
        """Trapping a failure."""
        try:
            raise NotImplementedError('test')
        except:
            f = failure.Failure()
        error = f.trap(SystemExit, RuntimeError)
        self.assertEquals(error, RuntimeError)
        self.assertEquals(f.type, NotImplementedError)
    
    def test_notTrapped(self):
        """Making sure trap doesn't trap what it shouldn't."""
        try:
            raise ValueError()
        except:
            f = failure.Failure()
        self.assertRaises(failure.Failure,f.trap,OverflowError)

    def testPrinting(self):
        out = StringIO.StringIO()
        try:
            1/0
        except:
            f = failure.Failure()
        f.printDetailedTraceback(out)
        f.printBriefTraceback(out)
        f.printTraceback(out)

    def testExplictPass(self):
        e = RuntimeError()
        f = failure.Failure(e)
        f.trap(RuntimeError)
        self.assertEquals(f.value, e)


    def _getDivisionFailure(self):
        try:
            1/0
        except:
            f = failure.Failure()
        return f

    def _getInnermostFrameLine(self, f):
        try:
            f.raiseException()
        except ZeroDivisionError:
            tb = util.extract_tb(sys.exc_info()[2])
            return tb[-1][-1]
        else:
            raise Exception(
                "f.raiseException() didn't raise ZeroDivisionError!?")

    def testRaiseExceptionWithTB(self):
        f = self._getDivisionFailure()
        innerline = self._getInnermostFrameLine(f)
        self.assertEquals(innerline, '1/0')

    def testLackOfTB(self):
        f = self._getDivisionFailure()
        f.cleanFailure()
        innerline = self._getInnermostFrameLine(f)
        self.assertEquals(innerline, '1/0')

    testLackOfTB.todo = "the traceback is not preserved, exarkun said he'll try to fix this! god knows how"
