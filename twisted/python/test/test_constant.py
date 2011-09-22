
"""
Unit tests for L{twisted.python.constant}.
"""

from twisted.trial.unittest import TestCase

from twisted.python.constant import (
    _Container, _Name, names, bitvector, sequence)


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



class _NameTests(TestCase):
    """
    Tests for the L{twisted.python.symbolic._Name} helper class which is used to
    represent individual values.
    """
    def test_name(self):
        """
        L{_Name.name} refers to the value passed to the L{_Name} initializer.
        """
        name = _Name(_Container(u"foo"), u"bar")
        self.assertEqual(name.name, u"bar")


    def test_representation(self):
        """
        The string representation of an instance of L{_Name} includes the
        container the instances belongs to as well as the instance's name.
        """
        name = _Name(_Container(u"foo"), u"bar")
        self.assertEqual(repr(name), "<foo=bar>")


    def test_equality(self):
        """
        A L{_Name} instance compares equal to itself.
        """
        name = _Name(_Container(u"foo"), u"bar")
        self.assertTrue(name == name)
        self.assertFalse(name != name)


    def test_nonequality(self):
        """
        Two different L{_Name} instances do not compare equal to each other.
        """
        first = _Name(_Container(u"foo"), u"bar")
        second = _Name(_Container(u"foo"), u"bar")
        self.assertFalse(first == second)
        self.assertTrue(first != second)


    def test_hash(self):
        """
        Two different L{_Name} instances with different names have different
        hashes, as do instances in different containers.
        """
        first = _Name(_Container(u"foo"), u"bar")
        second = _Name(_Container(u"foo"), u"baz")
        self.assertNotEqual(hash(first), hash(second))
        third = _Name(_Container(u"foo"), u"bar")
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
        self.assertIsInstance(METHOD.GET, _Name)
        self.assertEqual(u"GET", METHOD.GET.name)


    def test_withoutOtherAttributes(self):
        """
        Names not passed to L{names} are not available as attributes on the
        returned object.
        """
        self.assertRaises(AttributeError, getattr, METHOD, 'foo')


    def test_iteration(self):
        """
        Iteration over the object returned by L{names} produces each of its
        attribute values, in the order given to L{names}.
        """
        self.assertEqual(
            [METHOD.GET, METHOD.PUT, METHOD.POST, METHOD.DELETE],
            list(METHOD))


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
        self.assertEqual(0, FX.OK)
        self.assertEqual(1, FX.EOF)
        self.assertEqual(2, FX.NO_SUCH_FILE)


    def test_overriddenValue(self):
        """
        A name in a sequence may have a value explicitly assigned to it by
        passing that name as a keyword argument with a value.
        """
        self.assertEqual(11, FX.FILE_ALREADY_EXISTS)


    def test_overriddenStart(self):
        """
        The starting value for a sequence can be specified by passing a value
        for the C{start} keyword argument.
        """
        self.assertEqual(1, FILEXFER_TYPE.REGULAR)
        self.assertEqual(2, FILEXFER_TYPE.DIRECTORY)
        self.assertEqual(3, FILEXFER_TYPE.SYMLINK)


    def test_iteration(self):
        """
        Iteration over the object returned by L{sequence} produces each of its
        attribute values, in the order given to L{sequence}.
        """
        self.assertEqual(
            [FX.OK, FX.EOF, FX.NO_SUCH_FILE, FX.FILE_ALREADY_EXISTS],
            list(FX))


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
        self.assertIdentical(FX[0], FX.OK)
        self.assertIdentical(FX[1], FX.EOF)
        self.assertIdentical(FX[2], FX.NO_SUCH_FILE)
        self.assertIdentical(FX[11], FX.FILE_ALREADY_EXISTS)


FXF = bitvector.FXF(u"READ", u"WRITE", u"APPEND")


assert ~FXF.READ is (FXF.WRITE | FXF.APPEND)
assert (FXF.READ | FXF.WRITE) & (FXF.WRITE | FXF.APPEND) is FXF.WRITE
assert (FXF.READ | FXF.WRITE) ^ (FXF.WRITE | FXF.APPEND) is (FXF.READ | FXF.APPEND)


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
        self.assertEqual(1, FXF.READ)
        self.assertEqual(2, FXF.WRITE)
        self.assertEqual(4, FXF.APPEND)


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
        self.assertEqual(3, FXF.READ | FXF.WRITE)
        self.assertEqual(5, FXF.READ | FXF.APPEND)
        self.assertEqual(6, FXF.WRITE | FXF.APPEND)
        self.assertEqual(7, FXF.READ | FXF.WRITE | FXF.APPEND)


    def test_combinedRepresentation(self):
        """
        The object resulting from the combination of two bitvector constants
        using C{|} has a string representation reflecting both of the inputs.
        """
        self.assertEqual("<FXF=READ|WRITE>", FXF.READ | FXF.WRITE)


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
        self.assertEqual(1, FXF.READ & (FXF.READ | FXF.WRITE))
        self.assertEqual(2, FXF.WRITE & (FXF.READ | FXF.WRITE))
        self.assertEqual(
            3, (FXF.READ | FXF.READ) & (FXF.READ | FXF.WRITE | FXF.APPEND))
        self.assertEqual(0, FXF.READ & FXF.WRITE) # XXX GLUGH


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
        self.assertIdentical(FXF.READ ^ FXF.READ, 0) # XXX OOPS API FAIL


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
        self.assertIdentical(FXF[1], FXF.READ)
        self.assertIdentical(FXF[2], FXF.WRITE)
        self.assertIdentical(FXF[4], FXF.APPEND)


    def test_lookupCombination(self):
        """
        Indexing a bitvector object by a value corresponding to the combination
        of two or more of its constants results in
        """
        self.assertIdentical(FXF[1 | 2], FXF.READ | FXF.WRITE)
        self.assertIdentical(FXF[1 | 4], FXF.READ | FXF.APPEND)
        self.assertIdentical(FXF[2 | 4], FXF.WRITE | FXF.APPEND)
        self.assertIdentical(FXF[1 | 2 | 4], FXF.READ | FXF.WRITE | FXF.WRITE)





RPL = sequence.RPL(
    WELCOME="001", YOURHOST="002", CREATED="003", MYINFO="004", ISUPPORT="005")
assert RPL.WELCOME.name.encode("ascii") == "WELCOME"
assert RPL.WELCOME < RPL.YOURHOST < RPL.CREATED < RPL.MYINFO < RPL.ISUPPORT
assert RPL["001"] is RPL.WELCOME
assert list(RPL) == [
    RPL.WELCOME, RPL.YOURHOST, RPL.CREATED, RPL.MYINFO, RPL.ISUPPORT]
