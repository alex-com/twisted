# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Commands for telling a slave to load tests, run tests or quit.
"""

from twisted.protocols.amp import Command, String, Boolean



class Run(Command):
    """
    Run a test.
    """
    arguments = [('testCase', String())]
    response = [('success', Boolean())]



class ChDir(Command):
    """
    Change directories.
    """
    arguments = [('directory', String())]
    response = [('success', Boolean())]



class Quit(Command):
    """
    Close the slave process.
    """
    arguments = []
    response = [('success', Boolean())]

