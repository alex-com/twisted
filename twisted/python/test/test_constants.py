# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Unit tests for L{twisted.python.constants}.
"""

from twisted.trial.unittest import TestCase

from twisted.python.constants import _NamedConstant, NamedConstant, NamedConstants


class NamedConstantTests(TestCase):
    """
    Tests for the L{twisted.python.constants._NamedConstant} helper class which is used to
    represent individual values.
    """
    def setUp(self):
        """
        Create a dummy container into which constants can be placed.
        """
        class foo(NamedConstants):
            pass
        self.container = foo


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



class NamedConstantsTests(TestCase):
    """
    Tests for L{twisted.python.constants.NamedConstants}, a factory for named constants.
    """
    class METHOD(NamedConstants):
        """
        A container for some named constants to use in unit tests for
        L{NamedConstants}.
        """
        GET = NamedConstant()
        PUT = NamedConstant()
        POST = NamedConstant()
        DELETE = NamedConstant()


    def test_symbolicAttributes(self):
        """
        Each name passed to L{NamedConstants} is available as an attribute on the
        returned object.
        """
        self.assertTrue(hasattr(self.METHOD, "GET"))
        self.assertTrue(hasattr(self.METHOD, "PUT"))
        self.assertTrue(hasattr(self.METHOD, "POST"))
        self.assertTrue(hasattr(self.METHOD, "DELETE"))


    def test_withoutOtherAttributes(self):
        """
        Names not passed to L{NamedConstants} are not available as attributes on the
        returned object.
        """
        self.assertFalse(hasattr(self.METHOD, "foo"))


    def test_lookupByName(self):
        """
        Constants can be looked up by name using L{NamedConstants.lookupByName}.
        """
        self.assertIdentical(self.METHOD.lookupByName(u"GET"), self.METHOD.GET)


    def test_notLookupMissingByName(self):
        """
        Names not defined with a L{Constant} instance cannot be looked up using
        L{NamedConstants.lookupByName}.
        """
        self.assertRaises(ValueError, self.METHOD.lookupByName, u"lookupByName")
        self.assertRaises(ValueError, self.METHOD.lookupByName, u"__init__")
        self.assertRaises(ValueError, self.METHOD.lookupByName, u"foo")


    def test_name(self):
        """
        The C{name} attribute of one of the named constants gives that
        constant's name.
        """
        self.assertEqual(u"GET", self.METHOD.GET.name)


    def test_attributeIdentity(self):
        """
        Repeated access of an attribute of an object created using L{NamedConstants}
        results in the same object.
        """
        self.assertIdentical(self.METHOD.GET, self.METHOD.GET)


    def test_iteration(self):
        """
        Iteration over the object returned by L{NamedConstants} produces each of its
        attribute values, in the order given to L{NamedConstants}.
        """
        self.assertEqual(
            [self.METHOD.GET, self.METHOD.PUT,
             self.METHOD.POST, self.METHOD.DELETE],
            list(self.METHOD.iterconstants()))
