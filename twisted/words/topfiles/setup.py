import sys

from twisted.python import dist

if __name__ == '__main__':
    dist.setup(
        twisted_subproject="words",
        scripts=dist.getScripts("words"),
        # metadata
        name="Twisted Words",
        version="2.0.0",
        description="Twisted Words contains Instant Messaging implementations.",
        author="Twisted Matrix Laboratories",
        author_email="twisted-python@twistedmatrix.com",
        maintainer="Jp Calderone",
        maintainer_email="exarkun@divmod.com",
        url="http://twistedmatrix.com/projects/words/",
        license="MIT",
        long_description="""\
Twisted Words contains implementations of many Instant Messaging
protocols, including IRC, Jabber, MSN, OSCAR (AIM & ICQ), TOC (AOL),
and some functionality for creating bots, inter-protocol gateways, and
a client application for many of the protocols.
""",
        )
