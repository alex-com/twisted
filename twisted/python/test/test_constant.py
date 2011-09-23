
"""
Unit tests for L{twisted.python.constant}.
"""

from twisted.trial.unittest import TestCase

from twisted.python.constants import (
    _Container, _NamedConstant, names, bitvector, sequence)


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
        The string representation of an instance of L{_NamedConstant} includes the
        container the instances belongs to as well as the instance's name.
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



# Some constants, as one might use with an HTTP API, to use in tests for the
# names factory.
METHOD = names.METHOD(u"GET", u"PUT", u"POST", u"DELETE")



class NamesTests(TestCase):
    """
    Tests for L{twisted.python.symbolic.names}, a factory for named constants.
    """
    def test_representation(self):
        """
        The string representation of the object created using L{names} includes
        the name it was created with, given by the attribute of L{names} used,
        and all of the names passed in.
        """
        self.assertEqual("<METHOD: GET PUT POST DELETE>", repr(METHOD))


    def test_symbolicAttributes(self):
        """
        Each name passed to L{names} is available as an attribute on the
        returned object.
        """
        self.assertTrue(hasattr(METHOD, "GET"))
        self.assertTrue(hasattr(METHOD, "PUT"))
        self.assertTrue(hasattr(METHOD, "POST"))
        self.assertTrue(hasattr(METHOD, "DELETE"))


    def test_withoutOtherAttributes(self):
        """
        Names not passed to L{names} are not available as attributes on the
        returned object.
        """
        self.assertFalse(hasattr(METHOD, "foo"))


    def test_nameRepresentation(self):
        """
        The string representation of the object representing one of the named
        constants includes the name of the collection it is part of as well as
        its own name.
        """
        self.assertEqual("<METHOD=GET>", repr(METHOD.GET))


    def test_name(self):
        """
        The C{name} attribute of one of the named constants gives that
        constant's name.
        """
        self.assertEqual(u"GET", METHOD.GET.name)


    def test_attributeIdentity(self):
        """
        Repeated access of an attribute of an object created using L{names}
        results in the same object.
        """
        self.assertIdentical(METHOD.GET, METHOD.GET)


    def test_iteration(self):
        """
        Iteration over the object returned by L{names} produces each of its
        attribute values, in the order given to L{names}.
        """
        self.assertEqual(
            [METHOD.GET, METHOD.PUT, METHOD.POST, METHOD.DELETE],
            list(METHOD))


    def test_length(self):
        """
        The length of an object created with L{names} is equal to the number of
        names it has.
        """
        self.assertEqual(4, len(METHOD))


    def test_containsSymbolicNames(self):
        """
        The object returned by L{names} contains the names passed in.
        """
        self.assertIn(u"PUT", METHOD)


    def test_withoutOtherContents(self):
        """
        Names not passed to L{names} are not contained by the returned object.
        """
        self.assertNotIn(u"bar", METHOD)


FILEXFER_TYPE = sequence.FILEXFER_TYPE(
    u"REGULAR", u"DIRECTORY", u"SYMLINK", start=1)

FX = sequence.FX(
    u"OK", u"EOF", u"NO_SUCH_FILE", FILE_ALREADY_EXISTS=11)


class SequenceTests(TestCase):
    """
    Tests for L{twisted.python.symbolic.sequence}, a factory for named constants
    with mostly sequential integer values.
    """
    def test_representation(self):
        """
        The string representation of the object created using L{sequence}
        includes the name it was created with, given by the attribute of
        L{sequence} used, and all of the names passed in.
        """
        self.assertEqual(
            "<FX: OK EOF NO_SUCH_FILE FILE_ALREADY_EXISTS>", repr(FX))


    def test_values(self):
        """
        The names in a sequence are assigned sequential values starting at C{0}.
        """
        self.assertEqual(0, FX.OK.asInt())
        self.assertEqual(1, FX.EOF.asInt())
        self.assertEqual(2, FX.NO_SUCH_FILE.asInt())


    def test_overriddenValue(self):
        """
        A name in a sequence may have a value explicitly assigned to it by
        passing that name as a keyword argument with a value.
        """
        self.assertEqual(11, FX.FILE_ALREADY_EXISTS.asInt())


    def test_overriddenStart(self):
        """
        The starting value for a sequence can be specified by passing a value
        for the C{start} keyword argument.
        """
        self.assertEqual(1, FILEXFER_TYPE.REGULAR.asInt())
        self.assertEqual(2, FILEXFER_TYPE.DIRECTORY.asInt())
        self.assertEqual(3, FILEXFER_TYPE.SYMLINK.asInt())


    def test_iteration(self):
        """
        Iteration over the object returned by L{sequence} produces each of its
        attribute values, in the order given to L{sequence}.
        """
        self.assertEqual(
            [FX.OK, FX.EOF, FX.NO_SUCH_FILE, FX.FILE_ALREADY_EXISTS],
            list(FX))


    def test_length(self):
        """
        The length of an object created with L{sequence} is equal to the number
        of names it has.
        """
        self.assertEqual(4, len(FX))


    def test_ordering(self):
        """
        Sequence constants with smaller values than other sequence constants
        compare as less than them.
        """
        self.assertTrue(FX.OK < FX.EOF)
        self.assertTrue(FX.OK <= FX.EOF)
        self.assertTrue(FX.OK <= FX.OK)

        self.assertFalse(FX.OK > FX.EOF)
        self.assertFalse(FX.OK >= FX.EOF)
        self.assertTrue(FX.OK >= FX.OK)


    def test_containsSymbolicNames(self):
        """
        The object returned by L{sequence} contains the names passed in.
        """
        self.assertIn(u"OK", FX)
        self.assertIn(u"FILE_ALREADY_EXISTS", FX)


    def test_withoutOtherContents(self):
        """
        Names not passed to L{names} are not contained by the returned object.
        """
        self.assertNotIn(u"bar", FX)
        self.assertNotIn(u"start", FILEXFER_TYPE)


    def test_lookupByValue(self):
        """
        Indexing a sequence object by the value of one of its constants results
        in that constant.
        """
        self.assertIdentical(FX.lookupByValue(0), FX.OK)
        self.assertIdentical(FX.lookupByValue(1), FX.EOF)
        self.assertIdentical(FX.lookupByValue(2), FX.NO_SUCH_FILE)
        self.assertIdentical(FX.lookupByValue(11), FX.FILE_ALREADY_EXISTS)


FXF = bitvector.FXF(u"READ", u"WRITE", u"APPEND")


class BitvectorTests(TestCase):
    """
    Tests for L{twisted.python.symbolic.bitvector}, a factory for
    constants which can be composed into an integer, with each bit
    corresponding to one of the constants.
    """
    def test_representation(self):
        """
        The string representation of the object created using
        L{bitvector} includes the name it was created with, given by
        the attribute of L{bitvector} used, and all of the names
        passed in.
        """
        self.assertEqual("<FXF: READ WRITE APPEND>", repr(FXF))


    def test_values(self):
        """
        The names in a bitvector are assigned sequential powers of two starting
        at C{1}.
        """
        self.assertEqual(1, FXF.READ.asInt())
        self.assertEqual(2, FXF.WRITE.asInt())
        self.assertEqual(4, FXF.APPEND.asInt())


    def test_iteration(self):
        """
        Iteration over the object returned by L{bitvector} produces each of its
        attribute values, in the order given to L{bitvector}.
        """
        self.assertEqual([FXF.READ, FXF.WRITE, FXF.APPEND], list(FXF))


    def test_length(self):
        """
        The length of an object created with L{bitvector} is equal to the number
        of names it has.
        """
        self.assertEqual(3, len(FXF))


    def test_or(self):
        """
        Two bitvector constants can be combined using C{|}, producing a new
        constant representing the disjunction of the inputs.
        """
        self.assertEqual(3, (FXF.READ | FXF.WRITE).asInt())
        self.assertEqual(5, (FXF.READ | FXF.APPEND).asInt())
        self.assertEqual(6, (FXF.WRITE | FXF.APPEND).asInt())
        self.assertEqual(7, (FXF.READ | FXF.WRITE | FXF.APPEND).asInt())


    def test_combinedRepresentation(self):
        """
        The object resulting from the combination of two bitvector constants
        using C{|} has a string representation reflecting both of the inputs.
        """
        self.assertEqual("<FXF=READ|WRITE>", repr(FXF.READ | FXF.WRITE))


    def test_negation(self):
        """
        The negation of one of the constants created by L{bitvector} is the
        disjunction of all the other constants in that L{bitvector}.
        """
        self.assertIdentical(~FXF.READ, FXF.WRITE | FXF.APPEND)


    def test_and(self):
        """
        Two bitvector constants can be combined using C{&}, producing a new
        constant representing the conjunction of the inputs.
        """
        self.assertEqual(1, (FXF.READ & (FXF.READ | FXF.WRITE)).asInt())
        self.assertEqual(2, (FXF.WRITE & (FXF.READ | FXF.WRITE)).asInt())
        self.assertEqual(
            3,
            ((FXF.READ | FXF.WRITE) & (FXF.READ | FXF.WRITE | FXF.APPEND)).asInt())
        self.assertEqual(0, (FXF.READ & FXF.WRITE).asInt()) # XXX GLUGH


    def test_xor(self):
        """
        The result of an exclusive or operation on two L{bitvector} constants is
        a constant with exactly the bits set which were in one or the other but
        not both inputs.
        """
        self.assertIdentical(FXF.READ ^ (FXF.READ | FXF.WRITE), FXF.WRITE)
        self.assertIdentical(
            (FXF.READ | FXF.WRITE) ^ (FXF.WRITE | FXF.APPEND),
            (FXF.READ | FXF.APPEND))
        self.assertIdentical(FXF.READ ^ FXF.READ, FXF.WRITE ^ FXF.WRITE)


    def test_containsBits(self):
        """
        The object returned by L{bitvector} contains the integer values of the
        constants it defines and the integer values of combinations of the
        constants it defines.
        """
        self.assertIn(1, FXF)
        self.assertIn(2, FXF)
        self.assertIn(1 | 2, FXF)
        self.assertIn(4, FXF)
        self.assertIn(1 | 4, FXF)
        self.assertIn(2 | 4, FXF)
        self.assertIn(1 | 2 | 4, FXF)


    def test_withoutOtherContents(self):
        """
        The object returned by L{bitvector} does not contain other integer
        values.
        """
        self.assertNotIn(0, FXF)
        self.assertNotIn(8, FXF)
        self.assertNotIn(9, FXF)


    def test_lookupByValue(self):
        """
        Indexing a bitvector object by the value of one of its constants result
        in that constant.
        """
        self.assertIdentical(FXF.lookupByValue(1), FXF.READ)
        self.assertIdentical(FXF.lookupByValue(2), FXF.WRITE)
        self.assertIdentical(FXF.lookupByValue(4), FXF.APPEND)


    def test_lookupCombination(self):
        """
        Indexing a bitvector object by a value corresponding to the combination
        of two or more of its constants results in
        """
        self.assertIdentical(FXF.lookupByValue(1 | 2), FXF.READ | FXF.WRITE)
        self.assertIdentical(FXF.lookupByValue(1 | 4), FXF.READ | FXF.APPEND)
        self.assertIdentical(FXF.lookupByValue(2 | 4), FXF.WRITE | FXF.APPEND)
        self.assertIdentical(
            FXF.lookupByValue(1 | 2 | 4), FXF.READ | FXF.WRITE | FXF.APPEND)


    def test_valueIteration(self):
        """
        After combining two values using C{|}, the resulting object can be
        iterated over, resulting in the inputs.
        """
        self.assertEqual(list(FXF.READ | FXF.WRITE), [FXF.READ, FXF.WRITE])
