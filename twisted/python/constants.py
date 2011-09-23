# -*- test-case-name: twisted.python.test.test_constants -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Symbolic constant support, including collections and constants with text,
numeric, and bit flag values.
"""

__all__ = ['names', 'values', 'sequence', 'bitvector']

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



_unspecified = object()


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



class _SequenceContainer(_Container):
    """
    A L{_SequenceContainer} contains L{_ValueConstant}s.

    @ivar _counter: An C{int} used during initialization to assign increasing
        values to constants not explicitly assigned a value.

    @ivar _valueToConstant: A C{dict} mapping values the L{_ValueConstant}
        representing those values.
    """
    def __init__(self, name, positional, keyword):
        self._counter = keyword.pop('start', 0)
        self._valueToConstant = {}
        _Container.__init__(self, name, positional, keyword)


    def _constantFactory(self, name, value=_unspecified):
        """
        Construct a new constant to add to this container, allocating the next
        value (monotonically increasing) to it if no value is specified.

        @param name: The name of the constant to create.

        @param value: The value to assign to the new constant.  If not given, a
            value will be assigned.

        @raise ValueError: If the explicitly specified value has already been
            allocated to another constant.

        @return: The newly created constant.
        @type: L{_ValueConstant}
        """
        if value is _unspecified:
            value = self._counter
            self._counter += 1
        if value in self._valueToConstant:
            raise ValueError(
                "Duplicate value %r assigned to %s, already assigned to %s" % (
                    value, name, self._valueToConstant[value].name))
        result = _ValueConstant(self, name, value)
        self._valueToConstant[value] = result
        return result


    def lookupByValue(self, value):
        """
        Look up and return the constant which represents the given value.
        """
        return self._valueToConstant[value]



class _ValuesContainer(_SequenceContainer):
    """
    A L{_ValuesContainer} contains L{_ValueConstant}s with arbitrary values.
    """
    def _constantFactory(self, name, value):
        """
        Create a new constant to add to this container, requiring an explicit
        value.
        """
        return _SequenceContainer._constantFactory(self, name, value)



class _BitvectorConstant(_ValueConstant):
    """
    A L{_BitvectorConstant} some bits set within the context of a bitvector.
    Zero, one, or many bits may be set in a particular L{_BitvectorConstant}.

    @ivar name: A C{set} of the names of the bits set in the value of this
        constant.
    """
    def __init__(self, container, name, value):
        _ValueConstant.__init__(self, container, name, value)
        if not isinstance(self.name, set):
            self.name = set([name])


    def __or__(self, other):
        """
        Return a L{_BitvectorConstant} which includes all of the bits set in the
        value of C{self} and the value of C{other}, creating it if necessary,
        otherwise returning it from a cache.
        """
        if not isinstance(other, _BitvectorConstant):
            return NotImplemented
        value = self.value | other.value
        if value not in self.container._valueToConstant:
            self.container._valueToConstant[value] = _BitvectorConstant(
                self.container, self.name | other.name, value)
        return self.container._valueToConstant[value]


    def __and__(self, other):
        """
        Return a L{_BitvectorConstant} which includes only the bits set in the
        values of both C{self} and C{other}, creating it if necessary, otherwise
        returning it from a cache.
        """
        if not isinstance(other, _BitvectorConstant):
            return NotImplemented
        value = self.value & other.value
        if value not in self.container._valueToConstant:
            self.container._valueToConstant[value] = _BitvectorConstant(
                self.container, self.name & other.name, value)
        return self.container._valueToConstant[value]


    def __xor__(self, other):
        """
        Return a L{_BitvectorConstant} which includes only the bits set in the
        value of only one or the other of C{self} and C{other}, creating it if
        necessary, otherwise returning it from a cache.
        """
        if not isinstance(other, _BitvectorConstant):
            return NotImplemented
        value = self.value ^ other.value
        if value not in self.container._valueToConstant:
            self.container._valueToConstant[value] = _BitvectorConstant(
                self.container, self.name ^ other.name, value)
        return self.container._valueToConstant[value]


    def __invert__(self):
        """
        Return a L{_BitvectorConstant} which includes all of the bits defined by
        the container for this constant, except for those which are set on the
        value of C{self}.
        """
        result = self ^ self
        desired = ~self.value
        for other in self.container:
            if other.value & desired:
                result = result | other
        return result


    def __repr__(self):
        """
        Return text identifying both which bits are set in this constant and the
        collection this constant belongs to.
        """
        return '<%s=%s>' % (self.container.name, u'|'.join(self.name))


    def __iter__(self):
        """
        Iteration over a L{_BitvectorConstant} results in a
        L{_BitvectorConstant} for each bit set in the value of C{self}.
        """
        return iter([getattr(self.container, name) for name in self.name])



class _BitvectorContainer(_Container):
    """
    A L{_BitvectorContainer} contains L{_BitvectorConstant}s.

    @ivar _counter: An C{int} used during initialization to assign increasing
        values to constants not explicitly assigned a value.

    @ivar _valueToConstant: A C{dict} mapping values the L{_BitvectorConstant}
        representing those values.
    """
    def __init__(self, name, positional, keyword):
        self._counter = 0
        self._valueToConstant = {}
        _Container.__init__(self, name, positional, keyword)


    def _constantFactory(self, name, value=_unspecified):
        """
        Construct a new constant to add to this container, allocating the next
        bit position (monotonically increasing) to it if no value is specified.

        @param name: The name of the constant to create.

        @param value: The value to assign to the new constant.  If not given, a
            value will be assigned.

        @raise ValueError: If the explicitly specified value has already been
            allocated to another constant.

        @return: The newly created constant.
        @type: L{_BitvectorConstant}
        """
        if value is _unspecified:
            value = 1 << self._counter
            self._counter += 1
        if value in self._valueToConstant:
            raise ValueError(
                "Duplicate value %r assigned to %s, already assigned to %s" % (
                    value, name, self._valueToConstant[value].name))
        result = _BitvectorConstant(self, name, value)
        self._valueToConstant[value] = result
        return result


    def lookupByValue(self, value):
        """
        Look up and return a constant by its bit value.

        @param value: A C{int} representing a bitvector with zero, one, or many
            bits set.

        @return: If C{value} is C{0} or if any of the bits in C{value} do not
            correspond to a constant defined by this container , C{None}.
            Otherwise, a bitvector constant corresponding to all of the bits in
            C{value}.
        """
        if value == 0:
            return None
        anything = self._valueToConstant[1]
        result = anything ^ anything
        for name in self._enumerants:
            possible = getattr(self, name)
            if possible.value & value:
                value &= ~possible.value
                result = result | possible
        if value:
            return None
        return result



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
values = _ContainerFactory(_ValuesContainer)
sequence = _ContainerFactory(_SequenceContainer)
bitvector = _ContainerFactory(_BitvectorContainer)
