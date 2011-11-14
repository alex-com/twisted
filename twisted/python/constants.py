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

    @ivar _index: A C{int} allocated from a shared counter in order to keep
        track of the order in which L{NamedConstants} are instantiated.
    """
    def __init__(self):
        self._index = _constantOrder()


    def __get__(self, oself, cls):
        """
        Retrieve the L{_NamedConstant} instance which corresponds to this
        constant from the cache on C{cls}.
        """
        cls._initialize()
        return self


    def __repr__(self):
        """
        Return text identifying both which constant this is and which collection
        it belongs to.
        """
        return "<%s=%s>" % (self.container.__name__, self.name)


    def _realize(self, container, name, value):
        """
        Complete the initialization of this L{NamedConstant}.

        @param container: The L{NamedConstant} subclass this constant is part
            of.

        @param name: The name of this constant in its container.

        @param value: The value of this constant; not used, as named constants
            have no value apart from their identity.
        """
        self.container = container
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
    A L{NamedContainer} contains named constants.

    @ivar _enumerants: A C{dict} mapping L{NamedConstant} instances found in the
        class definition to L{_NamedConstant} instances which know their own
        name.  This is initialized in via the L{_EnumerantsInitializer}
        descriptor the first time it is accessed.
    """
    _initialized = False
    _enumerants = _EnumerantsInitializer()

    def iterconstants(cls):
        """
        Iteration over a L{_Container} results in all of the objects it contains
        (the names of its constants).
        """
        constants = cls._enumerants.values()
        constants.sort(key=lambda descriptor: descriptor._index)
        return iter(constants)
    iterconstants = classmethod(iterconstants)


    def lookupByName(cls, name):
        """
        Retrieve a constant by its name or raise a L{ValueError} if there is no
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
        Construct a new constant to add to this container.

        @param name: The name of the constant to create.

        @return: The newly created constant.
        @rtype: L{_NamedConstant}
        """
        return _unspecified
    _constantFactory = classmethod(_constantFactory)
