# -*- test-case-name: twisted.python.test.test_constants -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Symbolic constant support, including collections and constants with text,
numeric, and bit flag values.
"""

__all__ = ['NamedConstant', 'NamedConstants']

from itertools import count


_unspecified = object()
_constantOrder = count().next


class _NamedConstant(object):
    """
    A L{_NamedConstant} represents a single constant within some context.

    @ivar container: The L{NamedConstants} instance to which this constant
        belongs.
    @ivar name: The symbolic name of this constant.
    """
    def __init__(self, container, name):
        self.container = container
        self.name = name


    def __repr__(self):
        """
        Return text identifying both which constant this is and which collection
        it belongs to.
        """
        return "<%s=%s>" % (self.container.__name__, self.name)



class NamedConstant(object):
    """
    L{NamedConstant} defines an attribute to be a named constant within a
    collection defined by a L{NamedConstants} subclass.
    """
    def __init__(self):
        self.index = _constantOrder()


    def __get__(self, oself, cls):
        if not cls._initialized:
            cls._initialize()
        return cls._enumerants[self]



class NamedConstants(object):
    """
    A L{NamedContainer} contains named constants.
    """
    _initialized = False

    def iterconstants(cls):
        """
        Iteration over a L{_Container} results in all of the objects it contains
        (the names of its constants).
        """
        # XXX Maybe need to _initialize here
        constants = cls._enumerants.items()
        constants.sort(key=lambda (key, value): key.index)
        return iter([value for (key, value) in constants])
    iterconstants = classmethod(iterconstants)


    def lookupByName(cls, name):
        """
        Retrieve a constant by its name or raise a L{ValueError} if there is no
        constant associated with that name.
        """
        # XXX Maybe need to _initialize here
        if name in cls._enumerantNames:
            return getattr(cls, name)
        raise ValueError(name)
    lookupByName = classmethod(lookupByName)


    def _initialize(cls):
        names = set()
        constants = []
        for (name, descriptor) in cls.__dict__.iteritems():
            if isinstance(descriptor, NamedConstant):
                names.add(name)
                constants.append((descriptor.index, name, descriptor))
        constants.sort()
        enumerants = {}
        for (index, enumerant, descriptor) in constants:
            enumerants[descriptor] = cls._constantFactory(enumerant)
        cls._enumerants = enumerants
        cls._enumerantNames = names
        cls._initialized = True
    _initialize = classmethod(_initialize)


    def _constantFactory(cls, name):
        """
        Construct a new constant to add to this container.

        @param name: The name of the constant to create.

        @return: The newly created constant.
        @rtype: L{_NamedConstant}
        """
        return _NamedConstant(cls, name)
    _constantFactory = classmethod(_constantFactory)
