
# Copyright (c) 2001-2004 Twisted Matrix Laboratories.
# See LICENSE for details.


"""
I am the support module for making a ftp server with mktap.
"""

from twisted.protocols import ftp
from twisted.python import usage
from twisted.application import internet
from twisted.cred import error, portal, checkers, credentials

import os.path


class Options(usage.Options):
    synopsis = """Usage: mktap ftp [options].
    WARNING: This FTP server is probably INSECURE do not use it.
    """
    optParameters = [
        ["port", "p", "2121",                 "set the port number"],
        ["root", "r", "/usr/local/ftp",       "define the root of the ftp-site."],
        ["userAnonymous", "", "anonymous",    "Name of the anonymous user."]
    ]

    longdesc = ''


#def addUser(factory, username, password):
#    factory.userdict[username] = {}
#    if factory.otp:
#        from twisted.python import otp
#        factory.userdict[username]["otp"] = otp.OTP(password, hash=otp.md5)
#    else:
#        factory.userdict[username]["passwd"] = password

def makeService(config):
    f = ftp.FTPFactory()

    r = ftp.FTPRealm()
    r.tld = config['root']
    p = portal.Portal(r)
    p.registerChecker(checkers.AllowAnonymousAccess(), credentials.IAnonymous)

    f.tld = config['root']
    f.userAnonymous = config['userAnonymous']
    f.portal = p
    f.protocol = ftp.FTP
    
    try:
        portno = int(config['port'])
    except KeyError:
        portno = 2121
    return internet.TCPServer(portno, f)
