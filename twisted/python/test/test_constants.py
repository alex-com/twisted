# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Unit tests for L{twisted.python.constants}.
"""

from twisted.trial.unittest import TestCase

from twisted.python.constants import _Container, _NamedConstant, names


class DumbContainer(_Container):
    def _constantFactory(self, name, value=None):
        return name


class _ContainerTests(TestCase):
    """
    Tests for the L{twisted.python.constants._Container} helper class which is
    used to represent a group of related symbolic names.
    """
    def test_representation(self):
        """
        The string representation of a L{_Container} instances includes its name
        and the names of all its values.
        """
        container = DumbContainer(u"foo", (u"value1", u"value2"), {})
        self.assertEqual("<foo: value1 value2>", repr(container))



class _NamedConstantTests(TestCase):
    """
    Tests for the L{twisted.python.constants._NamedConstant} helper class which is used to
    represent individual values.
    """
    def setUp(self):
        """
        Create a dummy container into which constants can be placed.
        """
        self.container = _Container(u"foo", (), {})


    def test_name(self):
        """
        L{_NamedConstant.name} refers to the value passed to the L{_NamedConstant} initializer.
        """
        name = _NamedConstant(self.container, u"bar")
        self.assertEqual(name.name, u"bar")


    def test_representation(self):
        """
        The string representation of an instance of L{_NamedConstant} includes
        the container the instances belongs to as well as the instance's name.
        """
        name = _NamedConstant(self.container, u"bar")
        self.assertEqual(repr(name), "<foo=bar>")


    def test_equality(self):
        """
        A L{_NamedConstant} instance compares equal to itself.
        """
        name = _NamedConstant(self.container, u"bar")
        self.assertTrue(name == name)
        self.assertFalse(name != name)


    def test_nonequality(self):
        """
        Two different L{_NamedConstant} instances do not compare equal to each other.
        """
        first = _NamedConstant(self.container, u"bar")
        second = _NamedConstant(self.container, u"bar")
        self.assertFalse(first == second)
        self.assertTrue(first != second)


    def test_hash(self):
        """
        Two different L{_NamedConstant} instances with different names have different
        hashes, as do instances in different containers.
        """
        first = _NamedConstant(self.container, u"bar")
        second = _NamedConstant(self.container, u"baz")
        self.assertNotEqual(hash(first), hash(second))
        third = _NamedConstant(self.container, u"bar")
        self.assertNotEqual(hash(first), hash(third))



class NamesTests(TestCase):
    """
    Tests for L{twisted.python.constants.names}, a factory for named constants.
    """
    def setUp(self):
        # Some constants, as one might use with an HTTP API, to use in tests for
        # the names factory.
        self.METHOD = names.METHOD(u"GET", u"PUT", u"POST", u"DELETE")


    def test_rejectValues(self):
        """
        Constants constructed using L{names} may not have associated values.
        """
        # HTTP should be created with values instead, it won't work with names.
        self.assertRaises(TypeError, names.HTTP, OK=200)


    def test_representation(self):
        """
        The string representation of the object created using L{names} includes
        the name it was created with, given by the attribute of L{names} used,
        and all of the names passed in.
        """
        self.assertEqual("<METHOD: GET PUT POST DELETE>", repr(self.METHOD))


    def test_symbolicAttributes(self):
        """
        Each name passed to L{names} is available as an attribute on the
        returned object.
        """
        self.assertTrue(hasattr(self.METHOD, "GET"))
        self.assertTrue(hasattr(self.METHOD, "PUT"))
        self.assertTrue(hasattr(self.METHOD, "POST"))
        self.assertTrue(hasattr(self.METHOD, "DELETE"))


    def test_withoutOtherAttributes(self):
        """
        Names not passed to L{names} are not available as attributes on the
        returned object.
        """
        self.assertFalse(hasattr(self.METHOD, "foo"))


    def test_nameRepresentation(self):
        """
        The string representation of the object representing one of the named
        constants includes the name of the collection it is part of as well as
        its own name.
        """
        self.assertEqual("<METHOD=GET>", repr(self.METHOD.GET))


    def test_name(self):
        """
        The C{name} attribute of one of the named constants gives that
        constant's name.
        """
        self.assertEqual(u"GET", self.METHOD.GET.name)


    def test_attributeIdentity(self):
        """
        Repeated access of an attribute of an object created using L{names}
        results in the same object.
        """
        self.assertIdentical(self.METHOD.GET, self.METHOD.GET)


    def test_iteration(self):
        """
        Iteration over the object returned by L{names} produces each of its
        attribute values, in the order given to L{names}.
        """
        self.assertEqual(
            [self.METHOD.GET, self.METHOD.PUT, self.METHOD.POST,
             self.METHOD.DELETE],
            list(self.METHOD))


    def test_length(self):
        """
        The length of an object created with L{names} is equal to the number of
        names it has.
        """
        self.assertEqual(4, len(self.METHOD))
