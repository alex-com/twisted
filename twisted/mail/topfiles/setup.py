import sys

from twisted.python import dist

if __name__ == '__main__':
    dist.setup(
        twisted_subproject="mail",
        scripts=dist.getScripts("mail"),
        # metadata
        name="Twisted Mail",
        version="0.1.0",
        description="A Twisted Mail library, server and client.",
        author="Twisted Matrix Laboratories",
        author_email="twisted-python@twistedmatrix.com",
        maintainer="Jp Calderone",
        maintainer_email="exarkun@divmod.com",
        url="http://twistedmatrix.com/projects/mail/",
        license="MIT",
        long_description="""\
An SMTP, IMAP and POP protocol implementation together with clients
and servers.

Twisted Mail contains high-level, efficient protocol implementations
for both clients and servers of SMTP, POP3, and IMAP4. Additionally,
it contains an "out of the box" combination SMTP/POP3 virtual-hosting
mail server. Also included is a read/write Maildir implementation and
a basic Mail Exchange calculator.
""",
        )
