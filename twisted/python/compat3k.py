# Copyright (c) 2010 Twisted Matrix Laboratories.
# See LICENSE for details.

def execfile(filename, *args):
    return exec(compile(open(filename).read(), filename, 'exec'), *args)
