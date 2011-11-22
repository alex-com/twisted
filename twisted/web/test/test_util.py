# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.web.util}.
"""

from twisted.python.failure import Failure
from twisted.trial.unittest import TestCase
from twisted.web.util import (
    _hasSubstring, redirectTo, VariableElement, SourceLineElement,
    SourceFragmentElement, FrameElement, StackElement)

from twisted.web.http import FOUND
from twisted.web.server import Request
from twisted.web.template import TagLoader, flattenString, tags

from twisted.web.test.test_web import DummyChannel

class HasSubstringTestCase(TestCase):
    """
    Test regular expression-based substring searching.
    """

    def test_hasSubstring(self):
        """
        L{_hasSubstring} returns True if the specified substring is present in
        the text being searched.
        """
        self.assertTrue(_hasSubstring("foo", "<foo>"))

    def test_hasSubstringWithoutMatch(self):
        """
        L{_hasSubstring} returns False if the specified substring is not
        present in the text being searched.
        """
        self.assertFalse(_hasSubstring("foo", "<bar>"))

    def test_hasSubstringOnlyMatchesStringsWithNonAlphnumericNeighbors(self):
        """
        L{_hasSubstring} returns False if the specified substring is present
        in the text being searched but the characters surrounding the
        substring are alphanumeric.
        """
        self.assertFalse(_hasSubstring("foo", "barfoobaz"))
        self.assertFalse(_hasSubstring("foo", "1foo2"))

    def test_hasSubstringEscapesKey(self):
        """
        L{_hasSubstring} uses a regular expression to determine if a substring
        exists in a text snippet.  The substring is escaped to ensure that it
        doesn't interfere with the regular expression.
        """
        self.assertTrue(_hasSubstring("[b-a]",
                                      "Python can generate names like [b-a]."))


class RedirectToTestCase(TestCase):
    """
    Tests for L{redirectTo}.
    """

    def test_headersAndCode(self):
        """
        L{redirectTo} will set the C{Location} and C{Content-Type} headers on
        its request, and set the response code to C{FOUND}, so the browser will
        be redirected.
        """
        request = Request(DummyChannel(), True)
        request.method = 'GET'
        targetURL = "http://target.example.com/4321"
        redirectTo(targetURL, request)
        self.assertEqual(request.code, FOUND)
        self.assertEqual(
            request.responseHeaders.getRawHeaders('location'), [targetURL])
        self.assertEqual(
            request.responseHeaders.getRawHeaders('content-type'),
            ['text/html; charset=utf-8'])



class FailureElementTests(TestCase):
    """
    Tests for L{FailureElement} and related helpers which can render a
    L{Failure} as an HTML string.
    """
    def setUp(self):
        """
        Create a L{Failure} which can be used by the rendering tests.
        """
        def lineNumberProbeAlsoBroken():
            raise Exception("This is a problem")
        self.base = lineNumberProbeAlsoBroken.func_code.co_firstlineno

        try:
            lineNumberProbeAlsoBroken()
        except:
            self.failure = Failure()
            self.frame = self.failure.frames[-1]


    def test_variableElement(self):
        """
        L{VariableElement} renders the name and value of the variable (local,
        global, or attribute) it wraps.
        """
        element = VariableElement(
            TagLoader(tags.div(
                    tags.span(render="variableName"),
                    tags.span(render="variableValue"))),
            "spam", "eggs")
        d = flattenString(None, element)
        d.addCallback(
            self.assertEqual, "<div><span>spam</span><span>eggs</span></div>")
        return d


    def test_sourceLineElement(self):
        """
        L{SourceLineElement} renders a source line and line number.
        """
        element = SourceLineElement(
            TagLoader(tags.div(
                    tags.span(render="lineNumber"),
                    tags.span(render="sourceLine"))),
            50, "    print 'hello'")
        d = flattenString(None, element)
        d.addCallback(
            self.assertEqual,
            "<div><span>50</span><span>    print 'hello'</span></div>")
        return d


    def test_sourceFragmentElement(self):
        """
        L{SourceFragmentElement} renders source lines at and around the line
        number indicated by a frame object.
        """
        element = SourceFragmentElement(
            TagLoader(tags.div(
                    tags.span(render="lineNumber"),
                    tags.span(render="sourceLine"),
                    render="sourceLines")),
            self.frame)

        source = [
            'def lineNumberProbeAlsoBroken():',
            '    raise Exception("This is a problem")',
            'self.base = lineNumberProbeAlsoBroken.func_code.co_firstlineno',
        ]
        d = flattenString(None, element)
        d.addCallback(
            self.assertEqual,
            ''.join([
                    '<div class="snippet%sLine"><span>%d</span><span>%s</span>'
                    '</div>' % (
                        ["", "Highlight"][lineNumber == self.base + 1],
                        lineNumber, " " * 8 + sourceLine)
                    for (lineNumber, sourceLine)
                    in enumerate(source, self.base)]))
        return d


    def test_frameElementFilename(self):
        """
        The I{filename} renderer of L{FrameElement} renders the filename
        associated with the frame object used to initialize the L{FrameElement}.
        """
        element = FrameElement(
            TagLoader(tags.span(render="filename")),
            self.frame)
        d = flattenString(None, element)
        d.addCallback(
            # __file__ differs depending on whether an up-to-date .pyc file
            # already existed.
            self.assertEqual, "<span>" + __file__.rstrip('c') + "</span>")
        return d


    def test_frameElementLineNumber(self):
        """
        The I{lineNumber} renderer of L{FrameElement} renders the line number
        associated with the frame object used to initialize the L{FrameElement}.
        """
        element = FrameElement(
            TagLoader(tags.span(render="lineNumber")),
            self.frame)
        d = flattenString(None, element)
        d.addCallback(
            self.assertEqual, "<span>" + str(self.base + 1) + "</span>")
        return d


    def test_frameElementFunction(self):
        """
        The I{function} renderer of L{FrameElement} renders the line number
        associated with the frame object used to initialize the L{FrameElement}.
        """
        element = FrameElement(
            TagLoader(tags.span(render="function")),
            self.frame)
        d = flattenString(None, element)
        d.addCallback(
            self.assertEqual, "<span>lineNumberProbeAlsoBroken</span>")
        return d


    def test_frameElementSource(self):
        """
        The I{source} renderer of L{FrameElement} renders the source code near
        the source filename/line number associated with the frame object used to
        initialize the L{FrameElement}.
        """
        element = FrameElement(None, self.frame)
        renderer = element.lookupRenderMethod("source")
        tag = tags.div()
        result = renderer(None, tag)
        self.assertIsInstance(result, SourceFragmentElement)
        self.assertIdentical(result.frame, self.frame)
        self.assertEqual([tag], result.loader.load())


    def test_stackElement(self):
        """
        The I{frames} renderer of L{StackElement} renders each stack frame in
        the list of frames used to initialize the L{StackElement}.
        """
        element = StackElement(None, self.failure.frames[:2])
        renderer = element.lookupRenderMethod("frames")
        tag = tags.div()
        result = renderer(None, tag)
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))
        self.assertIsInstance(result[0], FrameElement)
        self.assertIdentical(result[0].frame, self.failure.frames[0])
        self.assertIsInstance(result[1], FrameElement)
        self.assertIdentical(result[1].frame, self.failure.frames[1])
