# -*- test-case-name: twisted.web.test.test_web -*-
# Copyright (c) 2001-2008 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.web.static}.
"""

import os

from twisted.python.filepath import FilePath
from twisted.python import log
from twisted.trial.unittest import TestCase
from twisted.web import static, http, script
from twisted.web.test.test_web import DummyRequest
from twisted.web.test._util import _render



class StaticFileTests(TestCase):
    """
    Tests for the basic behavior of L{File}.
    """
    def _render(self, resource, request):
        return _render(resource, request)


    def test_notFound(self):
        """
        If a request is made which encounters a L{File} before a final segment
        which does not correspond to any file in the path the L{File} was
        created with, a not found response is sent.
        """
        base = FilePath(self.mktemp())
        base.makedirs()
        file = static.File(base.path)

        request = DummyRequest(['foobar'])
        child = file.getChild("foobar", request)

        d = self._render(child, request)
        def cbRendered(ignored):
            self.assertEqual(request.responseCode, 404)
        d.addCallback(cbRendered)
        return d


    def test_securityViolationNotFound(self):
        """
        If a request is made which encounters a L{File} before a final segment
        which cannot be looked up in the filesystem due to security
        considerations, a not found response is sent.
        """
        base = FilePath(self.mktemp())
        base.makedirs()
        file = static.File(base.path)

        request = DummyRequest(['..'])
        child = file.getChild("..", request)

        d = self._render(child, request)
        def cbRendered(ignored):
            self.assertEqual(request.responseCode, 404)
        d.addCallback(cbRendered)
        return d


    def test_indexNames(self):
        """
        If a request is made which encounters a L{File} before a final empty
        segment, a file in the L{File} instance's C{indexNames} list which
        exists in the path the L{File} was created with is served as the
        response to the request.
        """
        base = FilePath(self.mktemp())
        base.makedirs()
        base.child("foo.bar").setContent("baz")
        file = static.File(base.path)
        file.indexNames = ['foo.bar']

        request = DummyRequest([''])
        child = file.getChild("", request)

        d = self._render(child, request)
        def cbRendered(ignored):
            self.assertEqual(''.join(request.written), 'baz')
            self.assertEqual(request.outgoingHeaders['content-length'], '3')
        d.addCallback(cbRendered)
        return d


    def test_staticFile(self):
        """
        If a request is made which encounters a L{File} before a final segment
        which names a file in the path the L{File} was created with, that file
        is served as the response to the request.
        """
        base = FilePath(self.mktemp())
        base.makedirs()
        base.child("foo.bar").setContent("baz")
        file = static.File(base.path)

        request = DummyRequest(['foo.bar'])
        child = file.getChild("foo.bar", request)

        d = self._render(child, request)
        def cbRendered(ignored):
            self.assertEqual(''.join(request.written), 'baz')
            self.assertEqual(request.outgoingHeaders['content-length'], '3')
        d.addCallback(cbRendered)
        return d


    def test_processors(self):
        """
        If a request is made which encounters a L{File} before a final segment
        which names a file with an extension which is in the L{File}'s
        C{processors} mapping, the processor associated with that extension is
        used to serve the response to the request.
        """
        base = FilePath(self.mktemp())
        base.makedirs()
        base.child("foo.bar").setContent(
            "from twisted.web.static import Data\n"
            "resource = Data('dynamic world','text/plain')\n")

        file = static.File(base.path)
        file.processors = {'.bar': script.ResourceScript}
        request = DummyRequest(["foo.bar"])
        child = file.getChild("foo.bar", request)

        d = self._render(child, request)
        def cbRendered(ignored):
            self.assertEqual(''.join(request.written), 'dynamic world')
            self.assertEqual(request.outgoingHeaders['content-length'], '13')
        d.addCallback(cbRendered)
        return d


    def test_ignoreExt(self):
        """
        The list of ignored extensions can be set by passing a value to
        L{File.__init__} or by calling L{File.ignoreExt} later.
        """
        file = static.File(".")
        self.assertEqual(file.ignoredExts, [])
        file.ignoreExt(".foo")
        file.ignoreExt(".bar")
        self.assertEqual(file.ignoredExts, [".foo", ".bar"])

        file = static.File(".", ignoredExts=(".bar", ".baz"))
        self.assertEqual(file.ignoredExts, [".bar", ".baz"])


    def test_ignoredExtensionsIgnored(self):
        """
        A request for the I{base} child of a L{File} succeeds with a resource
        for the I{base<extension>} file in the path the L{File} was created
        with if such a file exists and the L{File} has been configured to
        ignore the I{<extension>} extension.
        """
        base = FilePath(self.mktemp())
        base.makedirs()
        base.child('foo.bar').setContent('baz')
        base.child('foo.quux').setContent('foobar')
        file = static.File(base.path, ignoredExts=(".bar",))

        request = DummyRequest(["foo"])
        child = file.getChild("foo", request)

        d = self._render(child, request)
        def cbRendered(ignored):
            self.assertEqual(''.join(request.written), 'baz')
        d.addCallback(cbRendered)
        return d



class RangeTests(TestCase):
    """
    Tests for I{Range-Header} support in L{twisted.web.static.File}.

    @type file: L{file}
    @ivar file: Temporary (binary) file containing the content to be served.

    @type resource: L{static.File}
    @ivar resource: A leaf web resource using C{file} as content.

    @type request: L{DummyRequest}
    @ivar request: A fake request, requesting C{resource}.

    @type catcher: L{list}
    @ivar catcher: List which gathers all log information.
    """
    def setUp(self):
        """
        Create a temporary file with a fixed payload of 64 bytes.  Create a
        resource for that file and create a request which will be for that
        resource.  Each test can set a different range header to test different
        aspects of the implementation.
        """
        path = FilePath(self.mktemp())
        # This is just a jumble of random stuff.  It's supposed to be a good
        # set of data for this test, particularly in order to avoid
        # accidentally seeing the right result by having a byte sequence
        # repeated at different locations or by having byte values which are
        # somehow correlated with their position in the string.
        self.payload = ('\xf8u\xf3E\x8c7\xce\x00\x9e\xb6a0y0S\xf0\xef\xac\xb7'
                        '\xbe\xb5\x17M\x1e\x136k{\x1e\xbe\x0c\x07\x07\t\xd0'
                        '\xbckY\xf5I\x0b\xb8\x88oZ\x1d\x85b\x1a\xcdk\xf2\x1d'
                        '&\xfd%\xdd\x82q/A\x10Y\x8b')
        path.setContent(self.payload)
        self.file = path.open()
        self.resource = static.File(self.file.name)
        self.resource.isLeaf = 1
        self.request = DummyRequest([''])
        self.request.uri = self.file.name
        self.catcher = []
        log.addObserver(self.catcher.append)


    def tearDown(self):
        """
        Clean up the resource file and the log observer.
        """
        self.file.close()
        log.removeObserver(self.catcher.append)


    def _assertLogged(self, expected):
        """
        Asserts that a given log message occurred with an expected message.
        """
        logItem = self.catcher.pop()
        self.assertEquals(logItem["message"][0], expected)
        self.assertEqual(
            self.catcher, [], "An additional log occured: %r" % (logItem,))


    def test_invalidRanges(self):
        """
        L{File._parseRangeHeader} raises L{ValueError} when passed
        syntactically invalid byte ranges.
        """
        f = self.resource._parseRangeHeader

        # there's no =
        self.assertRaises(ValueError, f, 'bytes')

        # unknown isn't a valid Bytes-Unit
        self.assertRaises(ValueError, f, 'unknown=1-2')

        # there's no - in =stuff
        self.assertRaises(ValueError, f, 'bytes=3')

        # both start and end are empty
        self.assertRaises(ValueError, f, 'bytes=-')

        # start isn't an integer
        self.assertRaises(ValueError, f, 'bytes=foo-')

        # end isn't an integer
        self.assertRaises(ValueError, f, 'bytes=-foo')

        # end isn't equal to or greater than start
        self.assertRaises(ValueError, f, 'bytes=5-4')

        # Multiple ranges are not supported by this implementation (a future
        # implementation should lift this limitation, though).
        self.assertRaises(ValueError, f, 'bytes=1-2,3-4')


    def test_rangeMissingStop(self):
        """
        A single bytes range without an explicit stop position is parsed into a
        two-tuple giving the start position and C{None}.
        """
        self.assertEqual(
            self.resource._parseRangeHeader('bytes=0-'), (0, None))


    def test_rangeMissingStart(self):
        """
        A single bytes range without an explicit start position is parsed into
        a two-tuple of C{None} and the end position.
        """
        self.assertEqual(
            self.resource._parseRangeHeader('bytes=-3'), (None, 3))


    def test_range(self):
        """
        A single bytes range with explicit start and stop positions is parsed
        into a two-tuple of those positions.
        """
        self.assertEqual(
            self.resource._parseRangeHeader('bytes=2-5'), (2, 5))


    def test_rangeWithSpace(self):
        """
        A single bytes range with whitespace in allowed places is parsed in
        the same way as it would be without the whitespace.
        """
        self.assertEqual(
            self.resource._parseRangeHeader(' bytes=1-2 '), (1, 2))
        self.assertEqual(
            self.resource._parseRangeHeader('bytes =1-2 '), (1, 2))
        self.assertEqual(
            self.resource._parseRangeHeader('bytes= 1-2'), (1, 2))
        self.assertEqual(
            self.resource._parseRangeHeader('bytes=1 -2'), (1, 2))
        self.assertEqual(
            self.resource._parseRangeHeader('bytes=1- 2'), (1, 2))
        self.assertEqual(
            self.resource._parseRangeHeader('bytes=1-2 '), (1, 2))


    def test_nullRangeElements(self):
        """
        If there are multiple byte ranges but only one is non-null, the
        non-null range is parsed and its start and stop returned.
        """
        self.assertEqual(
            self.resource._parseRangeHeader('bytes=1-2,\r\n, ,\t'), (1, 2))


    def test_bodyLength(self):
        """
        A correct response to a range request is as long as the length of the
        requested range.
        """
        self.request.headers['range'] = 'bytes=0-43'
        self.resource.render(self.request)
        self.assertEquals(len(''.join(self.request.written)), 44)


    def test_invalidRangeRequest(self):
        """
        An incorrect range request (RFC 2616 defines a correct range request as
        a Bytes-Unit followed by a '=' character followed by a specific range.
        Only 'bytes' is defined) results in the range header value being logged
        and a normal 200 response being sent.
        """
        self.request.headers['range'] = range = 'foobar=0-43'
        self.resource.render(self.request)
        expected = "Ignoring malformed Range header %r" % (range,)
        self._assertLogged(expected)
        self.assertEquals(''.join(self.request.written), self.payload)
        self.assertEquals(self.request.responseCode, http.OK)
        self.assertEquals(
            self.request.outgoingHeaders['content-length'],
            str(len(self.payload)))


    def test_implicitEnd(self):
        """
        If the end byte position is omitted, then it is treated as if the
        length of the resource was specified by the end byte position.
        """
        self.request.headers['range'] = 'bytes=23-'
        self.resource.render(self.request)
        self.assertEquals(''.join(self.request.written), self.payload[23:])
        self.assertEquals(len(''.join(self.request.written)), 41)
        self.assertEquals(self.request.responseCode, http.PARTIAL_CONTENT)
        self.assertEquals(
            self.request.outgoingHeaders['content-range'], 'bytes 23-63/64')
        self.assertEquals(self.request.outgoingHeaders['content-length'], '41')


    def test_implicitStart(self):
        """
        If the start byte position is omitted but the end byte position is
        supplied, then the range is treated as requesting the last -N bytes of
        the resource, where N is the end byte position.
        """
        self.request.headers['range'] = 'bytes=-17'
        self.resource.render(self.request)
        self.assertEquals(''.join(self.request.written), self.payload[-17:])
        self.assertEquals(len(''.join(self.request.written)), 17)
        self.assertEquals(self.request.responseCode, http.PARTIAL_CONTENT)
        self.assertEquals(
            self.request.outgoingHeaders['content-range'], 'bytes 47-63/64')
        self.assertEquals(self.request.outgoingHeaders['content-length'], '17')


    def test_explicitRange(self):
        """
        A correct response to a bytes range header request from A to B starts
        with the A'th byte and ends with (including) the B'th byte. The first
        byte of a page is numbered with 0.
        """
        self.request.headers['range'] = 'bytes=3-43'
        self.resource.render(self.request)
        written = ''.join(self.request.written)
        self.assertEquals(written, self.payload[3:44])
        self.assertEquals(self.request.responseCode, http.PARTIAL_CONTENT)
        self.assertEquals(
            self.request.outgoingHeaders['content-range'], 'bytes 3-43/64')
        self.assertEquals(
            str(len(written)), self.request.outgoingHeaders['content-length'])


    def test_statusCodeRequestedRangeNotSatisfiable(self):
        """
        If a range is syntactically invalid due to the start being greater than
        the end, the range header is ignored (the request is responded to as if
        it were not present).
        """
        self.request.headers['range'] = 'bytes=20-13'
        self.resource.render(self.request)
        self.assertEquals(self.request.responseCode, http.OK)
        self.assertEquals(''.join(self.request.written), self.payload)
        self.assertEquals(
            self.request.outgoingHeaders['content-length'],
            str(len(self.payload)))


    def test_invalidStartBytePos(self):
        """
        If a range is unsatisfiable due to the start not being less than the
        length of the resource, the response is 416 (Requested range not
        satisfiable) and no data is written to the response body (RFC 2616,
        section 14.35.1).
        """
        self.request.headers['range'] = 'bytes=67-108'
        self.resource.render(self.request)
        self.assertEquals(
            self.request.responseCode, http.REQUESTED_RANGE_NOT_SATISFIABLE)
        self.assertEquals(''.join(self.request.written), '')
        self.assertEquals(self.request.outgoingHeaders['content-length'], '0')
        # Sections 10.4.17 and 14.16
        self.assertEquals(
            self.request.outgoingHeaders['content-range'],
            'bytes */%d' % (len(self.payload),))



class DirectoryListerTest(TestCase):
    """
    Tests for L{static.DirectoryLister}.
    """
    def _request(self, uri):
        request = DummyRequest([''])
        request.uri = uri
        return request


    def test_renderHeader(self):
        """
        L{static.DirectoryLister} prints the request uri as header of the
        rendered content.
        """
        path = FilePath(self.mktemp())
        path.makedirs()

        lister = static.DirectoryLister(path.path)
        data = lister.render(self._request('foo'))
        self.assertIn("<h1>Directory listing for foo</h1>", data)
        self.assertIn("<title>Directory listing for foo</title>", data)


    def test_renderUnquoteHeader(self):
        """
        L{static.DirectoryLister} unquote the request uri before printing it.
        """
        path = FilePath(self.mktemp())
        path.makedirs()

        lister = static.DirectoryLister(path.path)
        data = lister.render(self._request('foo%20bar'))
        self.assertIn("<h1>Directory listing for foo bar</h1>", data)
        self.assertIn("<title>Directory listing for foo bar</title>", data)


    def test_escapeHeader(self):
        """
        L{static.DirectoryLister} escape "&", "<" and ">" after unquoting the
        request uri.
        """
        path = FilePath(self.mktemp())
        path.makedirs()

        lister = static.DirectoryLister(path.path)
        data = lister.render(self._request('foo%26bar'))
        self.assertIn("<h1>Directory listing for foo&amp;bar</h1>", data)
        self.assertIn("<title>Directory listing for foo&amp;bar</title>", data)


    def test_renderFiles(self):
        """
        L{static.DirectoryLister} is able to list all the files inside a
        directory.
        """
        path = FilePath(self.mktemp())
        path.makedirs()
        path.child('file1').setContent("content1")
        path.child('file2').setContent("content2" * 1000)

        lister = static.DirectoryLister(path.path)
        data = lister.render(self._request('foo'))
        body = """<tr class="odd">
    <td><a href="file1">file1</a></td>
    <td>8B</td>
    <td>[text/html]</td>
    <td></td>
</tr>
<tr class="even">
    <td><a href="file2">file2</a></td>
    <td>7K</td>
    <td>[text/html]</td>
    <td></td>
</tr>"""
        self.assertIn(body, data)


    def test_renderDirectories(self):
        """
        L{static.DirectoryListerTest} is able to list all the directories
        inside a directory.
        """
        path = FilePath(self.mktemp())
        path.makedirs()
        path.child('dir1').makedirs()
        path.child('dir2 & 3').makedirs()

        lister = static.DirectoryLister(path.path)
        data = lister.render(self._request('foo'))
        body = """<tr class="odd">
    <td><a href="dir1/">dir1/</a></td>
    <td></td>
    <td>[Directory]</td>
    <td></td>
</tr>
<tr class="even">
    <td><a href="dir2%20%26%203/">dir2 &amp; 3/</a></td>
    <td></td>
    <td>[Directory]</td>
    <td></td>
</tr>"""
        self.assertIn(body, data)


    def test_renderFiltered(self):
        """
        L{static.DirectoryListerTest} takes a optional C{dirs} argument that
        filter out the list of of directories and files printed.
        """
        path = FilePath(self.mktemp())
        path.makedirs()
        path.child('dir1').makedirs()
        path.child('dir2').makedirs()
        path.child('dir3').makedirs()
        lister = static.DirectoryLister(path.path, dirs=["dir1", "dir3"])
        data = lister.render(self._request('foo'))
        body = """<tr class="odd">
    <td><a href="dir1/">dir1/</a></td>
    <td></td>
    <td>[Directory]</td>
    <td></td>
</tr>
<tr class="even">
    <td><a href="dir3/">dir3/</a></td>
    <td></td>
    <td>[Directory]</td>
    <td></td>
</tr>"""
        self.assertIn(body, data)


    def test_oddAndEven(self):
        """
        L{static.DirectoryLister} gives an alternate class for each odd and
        even rows in the table.
        """
        lister = static.DirectoryLister(None)
        elements = [{"href": "", "text": "", "size": "", "type": "",
                     "encoding": ""}  for i in xrange(5)]
        content = lister._buildTableContent(elements)

        self.assertEquals(len(content), 5)
        self.assertTrue(content[0].startswith('<tr class="odd">'))
        self.assertTrue(content[1].startswith('<tr class="even">'))
        self.assertTrue(content[2].startswith('<tr class="odd">'))
        self.assertTrue(content[3].startswith('<tr class="even">'))
        self.assertTrue(content[4].startswith('<tr class="odd">'))


    def test_mimeTypeAndEncodings(self):
        """
        L{static.DirectoryLister} is able to detect mimetype and encoding of
        listed files.
        """
        path = FilePath(self.mktemp())
        path.makedirs()
        path.child('file1.txt').setContent("file1")
        path.child('file2.py').setContent("python")
        path.child('file3.conf.gz').setContent("conf compressed")
        path.child('file4.diff.bz2').setContent("diff compressed")
        directory = os.listdir(path.path)
        directory.sort()

        contentTypes = {
            ".txt": "text/plain",
            ".py": "text/python",
            ".conf": "text/configuration",
            ".diff": "text/diff"
        }

        lister = static.DirectoryLister(path.path, contentTypes=contentTypes)
        dirs, files = lister._getFilesAndDirectories(directory)
        self.assertEquals(dirs, [])
        self.assertEquals(files, [
            {'encoding': '',
             'href': 'file1.txt',
             'size': '5B',
             'text': 'file1.txt',
             'type': '[text/plain]'},
            {'encoding': '',
             'href': 'file2.py',
             'size': '6B',
             'text': 'file2.py',
             'type': '[text/python]'},
            {'encoding': '[gzip]',
             'href': 'file3.conf.gz',
             'size': '15B',
             'text': 'file3.conf.gz',
             'type': '[text/configuration]'},
            {'encoding': '[bzip2]',
             'href': 'file4.diff.bz2',
             'size': '15B',
             'text': 'file4.diff.bz2',
             'type': '[text/diff]'}])


    def test_brokenSymlink(self):
        """
        If on the file in the listing points to a broken symlink, it should not
        be returned by L{static.DirectoryLister._getFilesAndDirectories}.
        """
        path = FilePath(self.mktemp())
        path.makedirs()
        file1 = path.child('file1')
        file1.setContent("file1")
        file1.linkTo(path.child("file2"))
        file1.remove()

        lister = static.DirectoryLister(path.path)
        directory = os.listdir(path.path)
        directory.sort()
        dirs, files = lister._getFilesAndDirectories(directory)
        self.assertEquals(dirs, [])
        self.assertEquals(files, [])

    if getattr(os, "symlink", None) is None:
        test_brokenSymlink.skip = "No symlink support"


    def test_repr(self):
        """
        L{static.DirectoryListerTest.__repr__} gives the path of the lister.
        """
        path = FilePath(self.mktemp())
        lister = static.DirectoryLister(path.path)
        self.assertEquals(repr(lister),
                          "<DirectoryLister of %r>" % (path.path,))
        self.assertEquals(str(lister),
                          "<DirectoryLister of %r>" % (path.path,))

    def test_formatFileSize(self):
        """
        L{static.formatFileSize} format an amount of bytes into a more readable
        format.
        """
        self.assertEquals(static.formatFileSize(0), "0B")
        self.assertEquals(static.formatFileSize(123), "123B")
        self.assertEquals(static.formatFileSize(4567), "4K")
        self.assertEquals(static.formatFileSize(8900000), "8M")
        self.assertEquals(static.formatFileSize(1234000000), "1G")
        self.assertEquals(static.formatFileSize(1234567890000), "1149G")
