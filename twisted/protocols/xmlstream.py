import warnings
warnings.warn("twisted.protocols.xmlstream is DEPRECATED. import twisted.xish.xmlstream instead.",
              DeprecationWarning, stacklevel=2)

from twisted.xish.xmlstream import *
