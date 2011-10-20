# -*- test-case-name: twisted.trial.dist.test -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
This package implements the distributed Trial test runner:

  - The L{twisted.trial.dist.disttrial} module implements a test runner which
    runs in a master process and can launch additional slave processes in which
    to run tests and gather up results from all of them.

  - The L{twisted.trial.dist.options} module defines command line options used
    to configure the distributed test runner.

  - The L{twisted.trial.dist.mastercommands} module defines AMP commands which
    are sent from slave processes back to the master process to report the
    results of tests.

  - The L{twisted.trial.dist.slavecommands} module defines AMP commands which
    are sent from the master process to the slave processes to control the
    execution of tests there.

  - The L{twisted.trial.dist.distreporter} module defines a proxy for
    L{twisted.trial.itrial.IReporter} which enforces the typical requirement
    that results be passed to a reporter for only one test at a time, allowing
    any reporter to be used with despite disttrial's simultaneously running
    tests.

  - The L{twisted.trial.dist.slavereporter} module implements a
    L{twisted.trial.itrial.IReporter} which is used by slave processes and
    reports results back to the master process using AMP commands.

  - The L{twisted.trial.dist.slavetrial} module is a runnable script which is
    the main point for slave processes.

  - The L{twisted.trial.dist.slave} process defines the master's AMP protocol
    for accepting results from slave processes and a process protocol for use
    running slaves as local child processes (as opposed to distributing them to
    another host).
"""
