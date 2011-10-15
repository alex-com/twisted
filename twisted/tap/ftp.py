# -*- test-case-name: twisted.test.test_ftp_options -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.


"""
I am the support module for making a ftp server with twistd.
"""

from twisted.application import internet
from twisted.cred import error, portal, checkers, credentials, strcred
from twisted.protocols import ftp

from twisted.python import usage, deprecate, versions

import os.path, warnings


class Options(usage.Options, strcred.AuthOptionMixin):
    synopsis = """[options].
    WARNING: This FTP server is probably INSECURE do not use it.
    """
    optParameters = [
        ["port", "p", "2121",               "set the port number"],
        ["root", "r", "/usr/local/ftp",     "define the root of the ftp-site."],
        ["userAnonymous", "", "anonymous",  "Name of the anonymous user."]
    ]

    longdesc = 'This creates a ftp.tap file that can be used by twistd'


    def opt_password_file(self, filename):
        """
        Specify a file containing username:password login info for authenticated
        connections. (DEPRECATED; see --help-auth instead)

        @since: 11.1
        """
        self['password-file'] = filename;
        msg = deprecate.getDeprecationWarningString(
            self.opt_password_file, versions.Version('Twisted', 11, 1, 0))
        warnings.warn(msg, category=DeprecationWarning, stacklevel=2)


    def postOptions(self):
        if not self.has_key('password-file'):
            self['password-file'] = None;



def makeService(config):
    f = ftp.FTPFactory()

    r = ftp.FTPRealm(config['root'])
    p = portal.Portal(r)
    p.registerChecker(checkers.AllowAnonymousAccess(), credentials.IAnonymous)

    if config['password-file'] is not None:
        p.registerChecker(
            checkers.FilePasswordDB(config['password-file'], cache=True))

    f.tld = config['root']
    f.userAnonymous = config['userAnonymous']
    f.portal = p
    f.protocol = ftp.FTP
    
    try:
        portno = int(config['port'])
    except KeyError:
        portno = 2121
    return internet.TCPServer(portno, f)
