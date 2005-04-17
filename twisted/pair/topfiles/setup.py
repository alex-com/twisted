import sys

from twisted.python import dist

if __name__ == '__main__':
    dist.setup(
        twisted_subproject="pair",
        # metadata
        name="Twisted Pair",
        version="0.1.0",
        description="Twisted Pair contains low-level networking support.",
        author="Twisted Matrix Laboratories",
        author_email="twisted-python@twistedmatrix.com",
        maintainer="Tommi Virtanen",
        maintainer_email="tv@twistedmatrix.com",
        url="http://twistedmatrix.com/projects/pair/",
        license="MIT",
        long_description="""
Raw network packet parsing routines, including ethernet, IP and UDP
packets, and tuntap support.
""",
        )
