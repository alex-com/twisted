# -*- test-case-name: twisted.python.test.test_constants -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Symbolic constant support, including collections and constants with text,
numeric, and bit flag values.
"""

__all__ = ['names']


_unspecified = object()


class _NamedConstant(object):
    """
    A L{_NamedConstant} represents a single constant within some context.

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
        return "<%s=%s>" % (self.container.name, self.name)



class _ValueConstant(_NamedConstant):
    """
    A L{_ValueConstant} represents a single constant within some context with an
    associated value.

    @ivar value: The associated value.
    """
    def __init__(self, container, name, value):
        _NamedConstant.__init__(self, container, name)
        self.value = value



class _Container(object):
    """
    A L{_Container} represents a collection of constants which are conceptually
    related to each other.

    @ivar name: The symbolic name of this collection.

    @ivar _enumerants: A C{tuple} of the names of all of the constants in this
        container.
    """
    def __init__(self, name, positional, keyword):
        self.name = name
        for enumerant in positional:
            setattr(self, enumerant, self._constantFactory(enumerant))
        for (enumerant, value) in keyword.iteritems():
            setattr(self, enumerant, self._constantFactory(enumerant, value))
        self._enumerants = positional + tuple(
            sorted(keyword, key=keyword.__getitem__))


    def __repr__(self):
        """
        Return text identifying this container and the names of all of its
        constants.
        """
        return '<%s: %s>' % (self.name, ' '.join(self._enumerants))


    def __contains__(self, name):
        """
        The contents of a L{_Container} are the names of its constants.
        """
        return name in self._enumerants


    def __iter__(self):
        """
        Iteration over a L{_Container} results in all of the objects it contains
        (the names of its constants).
        """
        return iter([getattr(self, name) for name in self._enumerants])


    def __len__(self):
        """
        The length of a L{_Container} is the number of constants it contains.
        """
        return len(self._enumerants)



class _NamesContainer(_Container):
    """
    A L{_NamesContainer} contains L{_NamedConstant}s.
    """
    def _constantFactory(self, name, value=_unspecified):
        """
        Construct a new constant to add to this container.

        @param name: The name of the constant to create.

        @param value: An API placeholder.  No value is allowed.

        @raise TypeError: If a value is supplied.

        @return: The newly created constant.
        @rtype: L{_NamedConstant}
        """
        if value is not _unspecified:
            raise TypeError("Cannot construct names with values")
        return _NamedConstant(self, name)



class _ContainerFactory(object):
    """
    An internal helper for constructing new constant collections.  A collection
    is represented by a container with constants in it.  L{_ContainerFactory}
    allows the collections to be created by attribute access.

    @ivar containerType: A callable which is used to create new containers.
    """
    def __init__(self, containerType):
        self.containerType = containerType


    def __getattr__(self, name):
        return lambda *args, **kwargs: self.containerType(name, args, kwargs)


names = _ContainerFactory(_NamesContainer)
