# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Commands for reporting test success of failure to the master.
"""

from twisted.protocols.amp import Command, String, Boolean



class AddSuccess(Command):
    """
    Add a Success.
    """
    arguments = [('testName', String())]
    response = [('success', Boolean())]



class AddError(Command):
    """
    Add an error.
    """
    arguments = [('testName', String()), ('error', String())]
    response = [('success', Boolean())]



class AddFailure(Command):
    """
    Add a failure.
    """
    arguments = [('testName', String()), ('fail', String())]
    response = [('success', Boolean())]



class AddSkip(Command):
    """
    Add a Skip.
    """
    arguments = [('testName', String()), ('reason', String())]
    response = [('success', Boolean())]



class AddExpectedFailure(Command):
    """
    Add an Expected Failure.
    """
    arguments = [('testName', String()), ('error', String()),
                 ('todo', String())]
    response = [('success', Boolean())]



class AddUnexpectedSuccess(Command):
    """
    Add an Unexpected Success.
    """
    arguments = [('testName', String()), ('todo', String())]
    response = [('success', Boolean())]



class StopTest(Command):
    """
    Stop the test.
    """
    arguments = [('testName', String())]
    response = [('success', Boolean())]



class ErrWrite(Command):
    """
    Write an error message.
    """
    arguments = [('error', String())]
    response = [('success', Boolean())]



class OutWrite(Command):
    """
    Write stdout.
    """
    arguments = [('out', String())]
    response = [('success', Boolean())]



class TestWrite(Command):
    """
    Write test log.
    """
    arguments = [('out', String())]
    response = [('success', Boolean())]

