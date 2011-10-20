# -*- test-case-name: twisted.trial.dist.test.test_options -*-
#
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from twisted.python.usage import Options, UsageError
from twisted.scripts.trial import _BasicOptions
from twisted.application.app import ReactorSelectionMixin



class DistOptions(_BasicOptions, Options, ReactorSelectionMixin):
    """
    Standard options for disttrial.
    """

    optParameters = [
        ['localnumber', 'n', '4', 'Number of local slaves to run']
        ]

    _slaveFlags = ["disablegc", "force-gc"]
    _slaveParameters = ["recursionlimit", "reactor"]


    def opt_localnumber(self, number):
        """
        Parse the argument to the localnumber option, expecting a strictly
        postive integer.
        """
        number = int(number)
        if number <= 0:
            raise UsageError(
                "argument to --localnumber must be a strictly positive integer")
        self["localnumber"] = number


    def getSlaveArguments(self):
        """
        Return a list of options to pass to disttrial slaves.
        """
        args = []
        for option in self._slaveFlags:
            if self.get(option) is not None:
                if self[option]:
                    args.append("--%s" % (option,))
        for option in self._slaveParameters:
            if self.get(option) is not None:
                args.extend(["--%s" % (option,), str(self[option])])
        return args
