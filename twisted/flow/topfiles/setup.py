import sys

from twisted.python import dist

if __name__ == '__main__':
    dist.setup(
        twisted_subproject="flow",
        # metadata
        name="Twisted Flow",
        version="0.1.0",
        description="A Twisted concurrency programming library.",
        author="Twisted Matrix Laboratories",
        author_email="twisted-python@twistedmatrix.com",
        maintainer="Clark Evans",
        maintainer_email="cce@twistedmatrix.com",
        url="http://twistedmatrix.com/projects/flow/",
        license="MIT",
        long_description="""\
Twisted Flow aims to make asynchronous programming a easier,
using python generators.
""",
        )
