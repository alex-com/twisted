"""Glue package for developers to use split out projects as one"""
import os.path, glob
__path__ = ["core", "conch", "flow", "lore", "mail", 
            "names", "news", "pair", "runner", "web", 
            "web2", "words", "xish"]
__path__=[os.path.abspath(os.path.join(os.path.dirname(__file__),
                                       "..", "..", elt, "twisted"))
          for elt in __path__]
import copyright
__version__ = copyright.version

import plugins
plugins.__path__.extend([os.path.abspath(os.path.join(x, 'plugins')) for x in __path__])


from twisted.python import compat
del compat, os, glob
