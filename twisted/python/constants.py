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


class NamedConstant(object):
    """
    L{NamedConstant} defines an attribute to be a named constant within a
    collection defined by a L{NamedConstants} subclass.

    @ivar name: A C{str} giving the name of this constant; only set once the
        constant is initialized by L{NamedConstants}.

    @ivar _container: The L{NamedConstants} subclass this constant belongs to;
        only set once the constant is initialized by that subclass.

    @ivar _index: A C{int} allocated from a shared counter in order to keep
        track of the order in which L{NamedConstants} are instantiated.
    """
    def __init__(self):
        self._index = _constantOrder()


    def __get__(self, oself, cls):
        """
        Ensure this constant has been initialized before returning it.
        """
        cls._initialize()
        return self


    def __repr__(self):
        """
        Return text identifying both which constant this is and which collection
        it belongs to.
        """
        return "<%s=%s>" % (self._container.__name__, self.name)


    def _realize(self, container, name, value):
        """
        Complete the initialization of this L{NamedConstant}.

        @param container: The L{NamedConstants} subclass this constant is part
            of.

        @param name: The name of this constant in its container.

        @param value: The value of this constant; not used, as named constants
            have no value apart from their identity.
        """
        self._container = container
        self.name = name



class _EnumerantsInitializer(object):
    """
    L{_EnumerantsInitializer} is a descriptor used to initialize a cache of
    objects representing named constants for a particular L{NamedConstants}
    subclass.
    """
    def __get__(self, oself, cls):
        """
        Initialize the cache on C{cls} and then return it.

        Additionally, replace this descriptor on C{cls} with the cache so that
        future access will go directly to it.
        """
        cls._initialize()
        return cls._enumerants



class NamedConstants(object):
    """
    A L{NamedConstants} contains constants which differ only their names and
    identities.

    @ivar _enumerants: A C{dict} mapping the names of L{NamedConstant} instances
        found in the class definition to those instances.  This is initialized
        in via the L{_EnumerantsInitializer} descriptor the first time it is
        accessed.
    """
    _initialized = False
    _enumerants = _EnumerantsInitializer()

    def __new__(cls):
        """
        L{NamedConstants}-derived classes are not intended to be instantiated.
        The class object itself is used directly.
        """
        raise TypeError("%s may not be instantiated." % (cls.__name__,))


    def iterconstants(cls):
        """
        Iteration over a L{NamedConstants} results in all of the constants it
        contains.
        """
        constants = cls._enumerants.values()
        constants.sort(key=lambda descriptor: descriptor._index)
        return iter(constants)
    iterconstants = classmethod(iterconstants)


    def lookupByName(cls, name):
        """
        Retrieve a constant by its name or raise a C{ValueError} if there is no
        constant associated with that name.
        """
        if name in cls._enumerants:
            return getattr(cls, name)
        raise ValueError(name)
    lookupByName = classmethod(lookupByName)


    def _initialize(cls):
        """
        Find all of the L{NamedConstant} instances in the definition of C{cls},
        initialize them with constant values, and build a mapping from their
        names to them to attach to C{cls}.
        """
        if not cls._initialized:
            constants = []
            for (name, descriptor) in cls.__dict__.iteritems():
                if isinstance(descriptor, NamedConstant):
                    constants.append((descriptor._index, name, descriptor))
            constants.sort()
            enumerants = {}
            for (index, enumerant, descriptor) in constants:
                value = cls._constantFactory(enumerant)
                descriptor._realize(cls, enumerant, value)
                enumerants[enumerant] = descriptor
            cls._enumerants = enumerants
            cls._initialized = True
    _initialize = classmethod(_initialize)


    def _constantFactory(cls, name):
        """
        Construct the value for a new constant to add to this container.

        @param name: The name of the constant to create.

        @return: L{NamedConstant} instances have no value apart from identity,
            so return a meaningless dummy value.
        """
        return _unspecified
    _constantFactory = classmethod(_constantFactory)
