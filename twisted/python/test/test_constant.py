
"""
Unit tests for L{twisted.python.constant}.
"""

from twisted.trial.unittest import TestCase

from twisted.python.constants import (
    _Container, _NamedConstant, names, values, bitvector, sequence)


class _ContainerTests(TestCase):
    """
    Tests for the L{twisted.python.symbolic._Container} helper class which is
    used to represent a group of related symbolic names.
    """
    def test_representation(self):
        """
        The string representation of a L{_Container} instances includes its name
        and the names of all its values.
        """
        container = _Container(u"foo", u"value1", u"value2")
        self.assertEqual("<foo: value1 value2>", repr(container))



class _NamedConstantTests(TestCase):
    """
    Tests for the L{twisted.python.symbolic._NamedConstant} helper class which is used to
    represent individual values.
    """
    def test_name(self):
        """
        L{_NamedConstant.name} refers to the value passed to the L{_NamedConstant} initializer.
        """
        name = _NamedConstant(_Container(u"foo"), u"bar")
        self.assertEqual(name.name, u"bar")


    def test_representation(self):
        """
        The string representation of an instance of L{_NamedConstant} includes
        the container the instances belongs to as well as the instance's name.
        """
        name = _NamedConstant(_Container(u"foo"), u"bar")
        self.assertEqual(repr(name), "<foo=bar>")


    def test_equality(self):
        """
        A L{_NamedConstant} instance compares equal to itself.
        """
        name = _NamedConstant(_Container(u"foo"), u"bar")
        self.assertTrue(name == name)
        self.assertFalse(name != name)


    def test_nonequality(self):
        """
        Two different L{_NamedConstant} instances do not compare equal to each other.
        """
        first = _NamedConstant(_Container(u"foo"), u"bar")
        second = _NamedConstant(_Container(u"foo"), u"bar")
        self.assertFalse(first == second)
        self.assertTrue(first != second)


    def test_hash(self):
        """
        Two different L{_NamedConstant} instances with different names have different
        hashes, as do instances in different containers.
        """
        first = _NamedConstant(_Container(u"foo"), u"bar")
        second = _NamedConstant(_Container(u"foo"), u"baz")
        self.assertNotEqual(hash(first), hash(second))
        third = _NamedConstant(_Container(u"foo"), u"bar")
        self.assertNotEqual(hash(first), hash(third))



class NamesTests(TestCase):
    """
    Tests for L{twisted.python.symbolic.names}, a factory for named constants.
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


    def test_containsSymbolicNames(self):
        """
        The object returned by L{names} contains the names passed in.
        """
        self.assertIn(u"PUT", self.METHOD)


    def test_withoutOtherContents(self):
        """
        Names not passed to L{names} are not contained by the returned object.
        """
        self.assertNotIn(u"bar", self.METHOD)



class ValuesTests(TestCase):
    """
    Tests for L{twisted.python.symbolic.values}, a factory for named constants
    associated with arbitrary values.
    """
    def setUp(self):
        self.RPL = values.RPL(WELCOME="001", YOURHOST="002", CREATED="003")


    def test_duplicateValue(self):
        """
        Constants constructed using L{values} may not have duplicate (re-used)
        values.
        """
        # Thanks for the example, IRC.
        self.assertRaises(ValueError, values.IRC, BOUNCE="010", ISUPPORT="010")


    def test_representation(self):
        """
        The string representation of the object created using L{values} includes
        the name it was created with, given by the attribute of L{values} used,
        and all of the names passed in.
        """
        self.assertEqual("<RPL: WELCOME YOURHOST CREATED>", repr(self.RPL))


    def test_values(self):
        """
        Each constant attribute of an object created using L{values} has a
        C{value} attribute set to the value associated with that constant in the
        initializer.
        """
        self.assertEqual(self.RPL.WELCOME.value, "001")
        self.assertEqual(self.RPL.YOURHOST.value, "002")
        self.assertEqual(self.RPL.CREATED.value, "003")


    def test_iteration(self):
        """
        Iteration over the object returned by L{values} produces each of its
        attribute values.
        """
        self.assertEqual(
            set([self.RPL.WELCOME, self.RPL.YOURHOST, self.RPL.CREATED]),
            set(self.RPL))


    def test_length(self):
        """
        The length of an object created with L{values} is equal to the number
        of names it has.
        """
        self.assertEqual(3, len(self.RPL))


    def test_containsSymbolicNames(self):
        """
        The object returned by L{values} contains the names passed in.
        """
        self.assertIn(u"WELCOME", self.RPL)
        self.assertIn(u"YOURHOST", self.RPL)
        self.assertIn(u"CREATED", self.RPL)


    def test_withoutOtherContents(self):
        """
        Names not passed to L{values} are not contained by the returned object.
        """
        self.assertNotIn(u"foo", self.RPL)
        self.assertNotIn("001", self.RPL)


    def test_lookupByValue(self):
        """
        The C{lookupByValue} method of a L{values} object can be used to find a
        constant by its value.
        """
        self.assertIdentical(self.RPL.lookupByValue("001"), self.RPL.WELCOME)
        self.assertIdentical(self.RPL.lookupByValue("002"), self.RPL.YOURHOST)
        self.assertIdentical(self.RPL.lookupByValue("003"), self.RPL.CREATED)



class SequenceTests(TestCase):
    """
    Tests for L{twisted.python.symbolic.sequence}, a factory for named constants
    with mostly sequential integer values.
    """
    def setUp(self):
        self.FILEXFER_TYPE = sequence.FILEXFER_TYPE(
            u"REGULAR", u"DIRECTORY", u"SYMLINK", start=1)
        self.FX = sequence.FX(
            u"OK", u"EOF", u"NO_SUCH_FILE", FILE_ALREADY_EXISTS=11)


    def test_representation(self):
        """
        The string representation of the object created using L{sequence}
        includes the name it was created with, given by the attribute of
        L{sequence} used, and all of the names passed in.
        """
        self.assertEqual(
            "<FX: OK EOF NO_SUCH_FILE FILE_ALREADY_EXISTS>", repr(self.FX))


    def test_values(self):
        """
        The names in a sequence are assigned sequential values starting at C{0}.
        """
        self.assertEqual(0, self.FX.OK.value)
        self.assertEqual(1, self.FX.EOF.value)
        self.assertEqual(2, self.FX.NO_SUCH_FILE.value)


    def test_overriddenValue(self):
        """
        A name in a sequence may have a value explicitly assigned to it by
        passing that name as a keyword argument with a value.
        """
        self.assertEqual(11, self.FX.FILE_ALREADY_EXISTS.value)


    def test_overriddenStart(self):
        """
        The starting value for a sequence can be specified by passing a value
        for the C{start} keyword argument.
        """
        self.assertEqual(1, self.FILEXFER_TYPE.REGULAR.value)
        self.assertEqual(2, self.FILEXFER_TYPE.DIRECTORY.value)
        self.assertEqual(3, self.FILEXFER_TYPE.SYMLINK.value)


    def test_iteration(self):
        """
        Iteration over the object returned by L{sequence} produces each of its
        attribute values, in the order given to L{sequence}.
        """
        self.assertEqual(
            [self.FX.OK, self.FX.EOF, self.FX.NO_SUCH_FILE, self.FX.FILE_ALREADY_EXISTS],
            list(self.FX))


    def test_length(self):
        """
        The length of an object created with L{sequence} is equal to the number
        of names it has.
        """
        self.assertEqual(4, len(self.FX))


    def test_ordering(self):
        """
        Sequence constants with smaller values than other sequence constants
        compare as less than them.
        """
        self.assertTrue(self.FX.OK < self.FX.EOF)
        self.assertTrue(self.FX.OK <= self.FX.EOF)
        self.assertTrue(self.FX.OK <= self.FX.OK)

        self.assertFalse(self.FX.OK > self.FX.EOF)
        self.assertFalse(self.FX.OK >= self.FX.EOF)
        self.assertTrue(self.FX.OK >= self.FX.OK)


    def test_containsSymbolicNames(self):
        """
        The object returned by L{sequence} contains the names passed in.
        """
        self.assertIn(u"OK", self.FX)
        self.assertIn(u"FILE_ALREADY_EXISTS", self.FX)


    def test_withoutOtherContents(self):
        """
        Names not passed to L{sequence} are not contained by the returned object.
        """
        self.assertNotIn(u"bar", self.FX)
        self.assertNotIn(u"start", self.FILEXFER_TYPE)


    def test_lookupByValue(self):
        """
        The C{lookupByValue} method of a L{sequence} object can be used to find
        a constant by its value.
        """
        self.assertIdentical(self.FX.lookupByValue(0), self.FX.OK)
        self.assertIdentical(self.FX.lookupByValue(1), self.FX.EOF)
        self.assertIdentical(self.FX.lookupByValue(2), self.FX.NO_SUCH_FILE)
        self.assertIdentical(
            self.FX.lookupByValue(11), self.FX.FILE_ALREADY_EXISTS)



class BitvectorTests(TestCase):
    """
    Tests for L{twisted.python.symbolic.bitvector}, a factory for
    constants which can be composed into an integer, with each bit
    corresponding to one of the constants.
    """
    def setUp(self):
        self.FXF = bitvector.FXF(u"READ", u"WRITE", u"APPEND", TEXT=0x40)


    def test_duplicateValue(self):
        """
        Constants constructed using L{bitvector} may not have duplicate
        (re-used) values.
        """
        # Oops, a typo, or something.
        self.assertRaises(ValueError, bitvector.FXF, READ=0x1, WRITE=0x1)
        # Also avoid collisions with implicitly assigned values
        self.assertRaises(ValueError, bitvector.FXF, u"READ", WRITE=0x1)


    def test_representation(self):
        """
        The string representation of the object created using
        L{bitvector} includes the name it was created with, given by
        the attribute of L{bitvector} used, and all of the names
        passed in.
        """
        self.assertEqual("<FXF: READ WRITE APPEND TEXT>", repr(self.FXF))


    def test_values(self):
        """
        The names in a bitvector are assigned sequential powers of two starting
        at C{1}.
        """
        self.assertEqual(1, self.FXF.READ.value)
        self.assertEqual(2, self.FXF.WRITE.value)
        self.assertEqual(4, self.FXF.APPEND.value)
        self.assertEqual(64, self.FXF.TEXT.value)


    def test_iteration(self):
        """
        Iteration over the object returned by L{bitvector} produces each of its
        attribute values, in the order given to L{bitvector}.
        """
        self.assertEqual(
            [self.FXF.READ, self.FXF.WRITE, self.FXF.APPEND, self.FXF.TEXT],
            list(self.FXF))


    def test_length(self):
        """
        The length of an object created with L{bitvector} is equal to the number
        of names it has.
        """
        self.assertEqual(4, len(self.FXF))


    def test_or(self):
        """
        Two bitvector constants can be combined using C{|}, producing a new
        constant representing the disjunction of the inputs.
        """
        self.assertEqual(3, (self.FXF.READ | self.FXF.WRITE).value)
        self.assertEqual(5, (self.FXF.READ | self.FXF.APPEND).value)
        self.assertEqual(6, (self.FXF.WRITE | self.FXF.APPEND).value)
        self.assertEqual(
            7, (self.FXF.READ | self.FXF.WRITE | self.FXF.APPEND).value)


    def test_onlyBitvectorConstantOr(self):
        """
        A bitvector constant can only be combined using C{|} with another
        bitvector constant.
        """
        self.assertRaises(TypeError, lambda: self.FXF.READ | "hello")
        self.assertRaises(TypeError, lambda: self.FXF.READ | [])
        self.assertRaises(TypeError, lambda: self.FXF.READ | 10)


    def test_combinedRepresentation(self):
        """
        The object resulting from the combination of two bitvector constants
        using C{|} has a string representation reflecting both of the inputs.
        """
        self.assertEqual(
            "<FXF=READ|WRITE>", repr(self.FXF.READ | self.FXF.WRITE))


    def test_negation(self):
        """
        The negation of one of the constants created by L{bitvector} is the
        disjunction of all the other constants in that L{bitvector}.
        """
        self.assertIdentical(
            ~self.FXF.READ, self.FXF.WRITE | self.FXF.APPEND | self.FXF.TEXT)


    def test_and(self):
        """
        Two bitvector constants can be combined using C{&}, producing a new
        constant representing the conjunction of the inputs.
        """
        self.assertEqual(
            1, (self.FXF.READ & (self.FXF.READ | self.FXF.WRITE)).value)
        self.assertEqual(
            2, (self.FXF.WRITE & (self.FXF.READ | self.FXF.WRITE)).value)
        self.assertEqual(
            3,
            ((self.FXF.READ | self.FXF.WRITE)
             & (self.FXF.READ | self.FXF.WRITE | self.FXF.APPEND)).value)
        self.assertEqual(0, (self.FXF.READ & self.FXF.WRITE).value)


    def test_onlyBitvectorConstantAnd(self):
        """
        A bitvector constant can only be combined using C{&} with another
        bitvector constant.
        """
        self.assertRaises(TypeError, lambda: self.FXF.READ & "hello")
        self.assertRaises(TypeError, lambda: self.FXF.READ & [])
        self.assertRaises(TypeError, lambda: self.FXF.READ & 10)


    def test_xor(self):
        """
        The result of an exclusive or operation on two L{bitvector} constants is
        a constant with exactly the bits set which were in one or the other but
        not both inputs.
        """
        self.assertIdentical(
            self.FXF.READ ^ (self.FXF.READ | self.FXF.WRITE), self.FXF.WRITE)
        self.assertIdentical(
            (self.FXF.READ | self.FXF.WRITE)
            ^ (self.FXF.WRITE | self.FXF.APPEND),
            (self.FXF.READ | self.FXF.APPEND))
        self.assertIdentical(
            self.FXF.READ ^ self.FXF.READ, self.FXF.WRITE ^ self.FXF.WRITE)


    def test_onlyBitvectorConstantXor(self):
        """
        A bitvector constant can only be combined using C{^} with another
        bitvector constant.
        """
        self.assertRaises(TypeError, lambda: self.FXF.READ ^ "hello")
        self.assertRaises(TypeError, lambda: self.FXF.READ ^ [])
        self.assertRaises(TypeError, lambda: self.FXF.READ ^ 10)


    def test_containsSymbolicNames(self):
        """
        The object returned by L{bitvector} contains the names passed in.
        """
        self.assertIn(u"READ", self.FXF)
        self.assertIn(u"WRITE", self.FXF)
        self.assertIn(u"APPEND", self.FXF)
        self.assertIn(u"TEXT", self.FXF)


    def test_withoutOtherContents(self):
        """
        The object returned by L{bitvector} does not contain other names.
        """
        self.assertNotIn(u"foo", self.FXF)
        self.assertNotIn(1, self.FXF)


    def test_lookupByValue(self):
        """
        Indexing a bitvector object by the value of one of its constants result
        in that constant.
        """
        self.assertIdentical(self.FXF.lookupByValue(0), None)
        self.assertIdentical(self.FXF.lookupByValue(1), self.FXF.READ)
        self.assertIdentical(self.FXF.lookupByValue(2), self.FXF.WRITE)
        self.assertIdentical(self.FXF.lookupByValue(4), self.FXF.APPEND)
        self.assertIdentical(self.FXF.lookupByValue(64), self.FXF.TEXT)


    def test_lookupCombination(self):
        """
        Indexing a bitvector object by a value corresponding to the combination
        of two or more of its constants results in
        """
        self.assertIdentical(
            self.FXF.lookupByValue(1 | 2), self.FXF.READ | self.FXF.WRITE)
        self.assertIdentical(
            self.FXF.lookupByValue(1 | 4), self.FXF.READ | self.FXF.APPEND)
        self.assertIdentical(
            self.FXF.lookupByValue(2 | 4), self.FXF.WRITE | self.FXF.APPEND)
        self.assertIdentical(
            self.FXF.lookupByValue(1 | 2 | 4),
            self.FXF.READ | self.FXF.WRITE | self.FXF.APPEND)
        self.assertIdentical(
            self.FXF.lookupByValue(1 | 64),
            self.FXF.READ | self.FXF.TEXT)
        self.assertIdentical(self.FXF.lookupByValue(1 | 8), None)


    def test_valueIteration(self):
        """
        After combining two values using C{|}, the resulting object can be
        iterated over, resulting in the inputs.
        """
        self.assertEqual(
            list(self.FXF.READ | self.FXF.WRITE),
            [self.FXF.READ, self.FXF.WRITE])
