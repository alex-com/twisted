# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Unit tests for L{twisted.python.constants}.
"""

from twisted.trial.unittest import TestCase

from twisted.python.constants import NamedConstant, NamedConstants


class NamedConstantTests(TestCase):
    """
    Tests for the L{twisted.python.constants.NamedConstant} class which is used
    to represent individual values.
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
        The C{name} attribute of a L{NamedConstant} refers to the value passed
        for the C{name} parameter to C{_realize}.
        """
        name = NamedConstant()
        name._realize(self.container, u"bar", None)
        self.assertEqual(u"bar", name.name)


    def test_representation(self):
        """
        The string representation of an instance of L{NamedConstant} includes
        the container the instances belongs to as well as the instance's name.
        """
        name = NamedConstant()
        name._realize(self.container, u"bar", None)
        self.assertEqual("<foo=bar>", repr(name))


    def test_equality(self):
        """
        A L{NamedConstant} instance compares equal to itself.
        """
        name = NamedConstant()
        name._realize(self.container, u"bar", None)
        self.assertTrue(name == name)
        self.assertFalse(name != name)


    def test_nonequality(self):
        """
        Two different L{NamedConstant} instances do not compare equal to each
        other.
        """
        first = NamedConstant()
        first._realize(self.container, u"bar", None)
        second = NamedConstant()
        second._realize(self.container, u"bar", None)
        self.assertFalse(first == second)
        self.assertTrue(first != second)


    def test_hash(self):
        """
        Two different L{NamedConstant} instances have different hashes.
        """
        first = NamedConstant()
        first._realize(self.container, u"bar", None)
        second = NamedConstant()
        second._realize(self.container, u"bar", None)
        self.assertNotEqual(hash(first), hash(second))



class NamedConstantsTests(TestCase):
    """
    Tests for L{twisted.python.constants.NamedConstants}, a base class for
    containers of related constaints.
    """
    def setUp(self):
        """
        Create a fresh new L{NamedConstants} subclass for each unit test to use.
        Since L{NamedConstants} is stateful, re-using the same subclass across
        test methods makes covering certain cases difficult.
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

        self.METHOD = METHOD


    def test_symbolicAttributes(self):
        """
        Each name associated with a L{NamedConstant} instance in the definition
        of a L{NamedConstants} subclass is available as an attribute on the
        resulting class.
        """
        self.assertTrue(hasattr(self.METHOD, "GET"))
        self.assertTrue(hasattr(self.METHOD, "PUT"))
        self.assertTrue(hasattr(self.METHOD, "POST"))
        self.assertTrue(hasattr(self.METHOD, "DELETE"))


    def test_withoutOtherAttributes(self):
        """
        As usual, names not defined in the class scope of a L{NamedConstants}
        subclass are not available as attributes on the resulting class.
        """
        self.assertFalse(hasattr(self.METHOD, "foo"))


    def test_representation(self):
        """
        The string representation of a constant on a L{NamedConstants} subclass
        includes the name of the L{NamedConstants} subclass and the name of the
        constant itself.
        """
        self.assertEqual("<METHOD=GET>", repr(self.METHOD.GET))


    def test_lookupByName(self):
        """
        Constants can be looked up by name using L{NamedConstants.lookupByName}.
        """
        method = self.METHOD.lookupByName(u"GET")
        self.assertIdentical(self.METHOD.GET, method)


    def test_notLookupMissingByName(self):
        """
        Names not defined with a L{NamedConstant} instance cannot be looked up
        using L{NamedConstants.lookupByName}.
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
        Repeated access of an attribute associated with a L{NamedConstant} value
        in a L{NamedConstants} subclass results in the same object.
        """
        self.assertIdentical(self.METHOD.GET, self.METHOD.GET)


    def test_iterconstants(self):
        """
        L{NamedConstants.iterconstants} returns an iterator over all of the
        constants defined in the class, in the order they were defined.
        """
        constants = list(self.METHOD.iterconstants())
        self.assertEqual(
            [self.METHOD.GET, self.METHOD.PUT,
             self.METHOD.POST, self.METHOD.DELETE],
            constants)
