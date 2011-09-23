# -*- test-case-name: twisted.python.test.test_constants -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Symbolic constant support, including collections and constants with text,
numeric, and bit flag values.
"""

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



class _IntegerConstant(_NamedConstant):
    def __init__(self, container, name, value):
        _NamedConstant.__init__(self, container, name)
        self.value = value


    def asInt(self):
        return self.value



class _Container(object):
    """
    A L{_Container} represents a collection of constants which are conceptually
    related to each other.

    @ivar name: The symbolic name of this collection.
    """
    def __init__(self, name, positional, keyword):
        self.name = name
        for enumerant in positional:
            setattr(self, enumerant, self._constantFactory(enumerant))
        for (enumerant, value) in keyword.iteritems():
            setattr(self, enumerant, self._constantFactory(enumerant, value))
        self._enumerants = positional + tuple(keyword)


    def __repr__(self):
        return '<%s: %s>' % (self.name, ' '.join(self._enumerants))


    def __contains__(self, name):
        return name in self._enumerants


    def __iter__(self):
        return iter([getattr(self, name) for name in self._enumerants])


    def __len__(self):
        return len(self._enumerants)



_unspecified = object()


class _NamesContainer(_Container):
    def _constantFactory(self, name, value=_unspecified):
        assert value is _unspecified # TODO test
        return _NamedConstant(self, name)



class _SequenceContainer(_Container):
    def __init__(self, name, positional, keyword):
        self._counter = keyword.pop('start', 0)
        self._valueToConstant = {}
        _Container.__init__(self, name, positional, keyword)


    def _constantFactory(self, name, value=_unspecified):
        if value is _unspecified:
            value = self._counter
            self._counter += 1
        result = _IntegerConstant(self, name, value)
        self._valueToConstant[value] = result # TODO test collision
        return result


    def lookupByValue(self, value):
        return self._valueToConstant[value]



class _BitvectorConstant(_IntegerConstant):
    def __init__(self, container, name, value):
        _IntegerConstant.__init__(self, container, name, value)
        if not isinstance(self.name, set):
            self.name = set([name])


    def __or__(self, other):
        # TODO What if it isn't a _BitvectorConstant
        value = self.value | other.value
        if value not in self.container._valueToConstant:
            self.container._valueToConstant[value] = _BitvectorConstant(
                self.container, self.name | other.name, value)
        return self.container._valueToConstant[value]


    def __and__(self, other):
        # TODO What if it isn't a _BitvectorConstant
        value = self.value & other.value
        if value not in self.container._valueToConstant:
            self.container._valueToConstant[value] = _BitvectorConstant(
                self.container, self.name & other.name, value)
        return self.container._valueToConstant[value]


    def __xor__(self, other):
        # TODO What if it isn't a _BitvectorConstant
        value = self.value ^ other.value
        if value not in self.container._valueToConstant:
            self.container._valueToConstant[value] = _BitvectorConstant(
                self.container, self.name ^ other.name, value)
        return self.container._valueToConstant[value]


    def __invert__(self):
        return self.container.lookupByValue(~self.value)


    def __repr__(self):
        return '<%s=%s>' % (self.container.name, u'|'.join(self.name))


    def __iter__(self):
        return iter([getattr(self.container, name) for name in self.name])



class _BitvectorContainer(_Container):

    def __init__(self, name, positional, keyword):
        self._counter = 0
        self._valueToConstant = {}
        _Container.__init__(self, name, positional, keyword)


    def _constantFactory(self, name, value=_unspecified):
        if value is _unspecified:
            value = 1 << self._counter
            self._counter += 1
        result = _BitvectorConstant(self, name, value)
        self._valueToConstant[value] = result
        return result


    def lookupByValue(self, value):
        result = None
        for name in self._enumerants:
            possible = getattr(self, name)
            if possible.value & value:
                if result is None:
                    result = possible
                else:
                    result = result | possible
        return result



class _ContainerFactory(object):
    def __init__(self, containerType):
        self.containerType = containerType


    def __getattr__(self, name):
        return lambda *args, **kwargs: self.containerType(name, args, kwargs)


names = _ContainerFactory(_NamesContainer)
sequence = _ContainerFactory(_SequenceContainer)
bitvector = _ContainerFactory(_BitvectorContainer)
