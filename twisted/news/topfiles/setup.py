import sys

from twisted.python import dist

if __name__ == '__main__':
    dist.setup(
        twisted_subproject="news",
        # metadata
        name="Twisted News",
        version="2.0.0",
        description="Twisted News is an NNTP server and programming library.",
        author="Twisted Matrix Laboratories",
        author_email="twisted-python@twistedmatrix.com",
        maintainer="Jp Calderone",
        maintainer_email="exarkun@divmod.com",
        url="http://twistedmatrix.com/projects/news/",
        license="MIT",
        long_description="""\
Twisted News is an NNTP protocol (Usenet) programming library. The
library contains server and client protocol implementations. A simple
NNTP server is also provided.
""",
    )

