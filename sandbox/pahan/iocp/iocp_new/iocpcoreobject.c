#include <Python.h>
#include <winsock2.h>
#include <mswsock.h>
#include <windows.h>
#include "structmember.h"

#define SPEW
// compensate for mingw's lack of recent Windows headers
#ifndef _MSC_VER
#define WSAID_CONNECTEX {0x25a207b9,0xddf3,0x4660,{0x8e,0xe9,0x76,0xe5,0x8c,0x74,0x06,0x3e}}
#define WSAID_ACCEPTEX {0xb5367df1,0xcbac,0x11cf,{0x95,0xca,0x00,0x80,0x5f,0x48,0xa1,0x92}}

typedef
BOOL
(PASCAL FAR * LPFN_CONNECTEX) (
    IN SOCKET s,
    IN const struct sockaddr FAR *name,
    IN int namelen,
    IN PVOID lpSendBuffer OPTIONAL,
    IN DWORD dwSendDataLength,
    OUT LPDWORD lpdwBytesSent,
    IN LPOVERLAPPED lpOverlapped
    );

typedef
BOOL
(PASCAL FAR * LPFN_ACCEPTEX)(
    IN SOCKET sListenSocket,
    IN SOCKET sAcceptSocket,
    IN PVOID lpOutputBuffer,
    IN DWORD dwReceiveDataLength,
    IN DWORD dwLocalAddressLength,
    IN DWORD dwRemoteAddressLength,
    OUT LPDWORD lpdwBytesReceived,
    IN LPOVERLAPPED lpOverlapped
    );
#endif

typedef struct {
    int size;
    char buffer[0];
} AddrBuffer;

LPFN_CONNECTEX gConnectEx;
LPFN_ACCEPTEX gAcceptEx;

typedef struct {
    OVERLAPPED ov;
    PyObject *callback;
} MyOVERLAPPED;

typedef struct {
    PyObject_HEAD
//    PyObject *cur_ops;
    HANDLE iocp;
} iocpcore;

void CALLBACK dummy_completion(DWORD err, DWORD bytes, OVERLAPPED *ov, DWORD flags) {
}

static void
iocpcore_dealloc(iocpcore* self)
{
//    PyDict_Clear(self->cur_ops);
//    Py_DECREF(self->cur_ops);
    CloseHandle(self->iocp);
    self->ob_type->tp_free((PyObject*)self);
}

static PyObject *
iocpcore_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    iocpcore *self;

    self = (iocpcore *)type->tp_alloc(type, 0);
    if(self != NULL) {
        self->iocp = CreateIoCompletionPort(INVALID_HANDLE_VALUE, NULL, 0, 1);
        if(!self->iocp) {
            Py_DECREF(self);
            return PyErr_SetFromWindowsErr(0);
        }
//        self->cur_ops = PyDict_New();
//        if(!self->cur_ops) {
//            CloseHandle(self->iocp);
//            Py_DECREF(self);
//            return NULL;
//        }
    }
    return (PyObject *)self;
}

static PyObject *iocpcore_doIteration(iocpcore* self, PyObject *args) {
    long timeout;
    double ftimeout;
    PyObject *tm, *ret, *object;
    DWORD bytes;
    unsigned long key;
    MyOVERLAPPED *ov;
    int res, err;
    if(!PyArg_ParseTuple(args, "d", &ftimeout)) {
        PyErr_Clear();
        if(!PyArg_ParseTuple(args, "O", &tm)) {
            return NULL;
        }
        if(tm == Py_None) {
            timeout = INFINITE;
        } else {
            PyErr_SetString(PyExc_TypeError, "Wrong timeout argument");
            return NULL;
        }
    } else {
        timeout = (int)(ftimeout * 1000);
    }
    Py_BEGIN_ALLOW_THREADS;
    res = GetQueuedCompletionStatus(self->iocp, &bytes, &key, (OVERLAPPED**)&ov, timeout);
    Py_END_ALLOW_THREADS;
#ifdef SPEW
    printf("gqcs returned res %d, ov 0x%p\n", res, ov);
#endif
    err = GetLastError();
#ifdef SPEW
    printf("    GLE returned %d\n", err);
#endif
    if(!res) {
        if(!ov) {
#ifdef SPEW
            printf("gqcs returned NULL ov\n");
#endif
            if(err != WAIT_TIMEOUT) {
                return PyErr_SetFromWindowsErr(err);
            } else {
                return Py_BuildValue("");
            }
        }
    }
    // At this point, ov is non-NULL
    // steal its reference, then clobber it to death! I mean free it!
    object = ov->callback;
    if(object) {
        // this is retarded. GQCS only sets error value if it wasn't succesful
        // (what about forth case, when handle is closed?)
        if(res) {
            err = 0;
        }
#ifdef SPEW
        printf("calling callback with err %d, bytes %d\n", err, bytes);
#endif
        ret = PyObject_CallFunction(object, "ll", err, bytes);
        if(!ret) {
            Py_DECREF(object);
            PyMem_Free(ov);
            return NULL;
        }
        Py_DECREF(ret);
        Py_DECREF(object);
    }
    PyMem_Free(ov);
    return Py_BuildValue("");
}

static PyObject *iocpcore_WriteFile(iocpcore* self, PyObject *args) {
    HANDLE handle;
    char *buf;
    int buflen, res, len = -1;
    DWORD err, bytes;
    PyObject *object;
    MyOVERLAPPED *ov;
    if(!PyArg_ParseTuple(args, "lt#O|l", &handle, &buf, &buflen, &object, &len)) {
        return NULL;
    }
    if(len == -1) {
        len = buflen;
    }
    if(len <= 0 || len > buflen) {
        PyErr_SetString(PyExc_ValueError, "Invalid length specified");
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    ov->callback = object;
    CreateIoCompletionPort(handle, self->iocp, 0, 1);
#ifdef SPEW
    printf("calling WriteFile(%d, 0x%p, %d, 0x%p, 0x%p)\n", handle, buf, len, &bytes, ov);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = WriteFile(handle, buf, len, &bytes, (OVERLAPPED *)ov);
    Py_END_ALLOW_THREADS;
    err = GetLastError();
#ifdef SPEW
    printf("    wf returned %d, err %d\n", res, err);
#endif
    if(!res && err != ERROR_IO_PENDING) {
        return PyErr_SetFromWindowsErr(err);
    }
    if(res) {
        err = 0;
    }
    return Py_BuildValue("ll", err, bytes);
}

static PyObject *iocpcore_ReadFile(iocpcore* self, PyObject *args) {
    HANDLE handle;
    char *buf;
    int buflen, res, len = -1;
    DWORD err, bytes;
    PyObject *object;
    MyOVERLAPPED *ov;
    if(!PyArg_ParseTuple(args, "lw#O|l", &handle, &buf, &buflen, &object, &len)) {
        return NULL;
    }
    if(len == -1) {
        len = buflen;
    }
    if(len <= 0 || len > buflen) {
        PyErr_SetString(PyExc_ValueError, "Invalid length specified");
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    ov->callback = object;
    CreateIoCompletionPort(handle, self->iocp, 0, 1);
#ifdef SPEW
    printf("calling ReadFile(%d, 0x%p, %d, 0x%p, 0x%p)\n", handle, buf, len, &bytes, ov);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = ReadFile(handle, buf, len, &bytes, (OVERLAPPED *)ov);
    Py_END_ALLOW_THREADS;
    err = GetLastError();
#ifdef SPEW
    printf("    rf returned %d, err %d\n", res, err);
#endif
    if(!res && err != ERROR_IO_PENDING) {
        return PyErr_SetFromWindowsErr(err);
    }
    if(res) {
        err = 0;
    }
    return Py_BuildValue("ll", err, bytes);
}

// rape'n'paste from socketmodule.c
static PyObject *parsesockaddr(struct sockaddr *addr, int addrlen)
{
    if (addrlen == 0) {
        /* No address -- may be recvfrom() from known socket */
        Py_INCREF(Py_None);
        return Py_None;
    }

    switch (addr->sa_family) {
    case AF_INET:
    {
        struct sockaddr_in *a = (struct sockaddr_in *)addr;
        char *s;
        s = inet_ntoa(a->sin_addr);
        PyObject *ret = NULL;
        if (s) {
            ret = Py_BuildValue("si", s, ntohs(a->sin_port));
        } else {
            PyErr_SetString(PyExc_ValueError, "Invalid AF_INET address");
        }
        return ret;
    }
    default:
        /* If we don't know the address family, don't raise an
           exception -- return it as a tuple. */
        return Py_BuildValue("is#",
                     addr->sa_family,
                     addr->sa_data,
                     sizeof(addr->sa_data));

    }
}

static PyObject *iocpcore_interpretAB(iocpcore* self, PyObject *args) {
    char *buf;
    int len;
    if(!PyArg_ParseTuple(args, "t#", &buf, &len)) {
        return NULL;
    }
    return parsesockaddr((struct sockaddr *)buf, len);
}

static PyObject *iocpcore_WSARecvFrom(iocpcore* self, PyObject *args) {
    SOCKET handle;
    char *buf;
    int buflen, res, len = -1, ablen;
    DWORD bytes, err, flags;
    PyObject *object;
    MyOVERLAPPED *ov;
    WSABUF wbuf;
    AddrBuffer *ab;
    if(!PyArg_ParseTuple(args, "lw#Ow#|ll", &handle, &buf, &buflen, &object, &ab, &ablen, &len, &flags)) {
        return NULL;
    }
    if(ablen < sizeof(int)+sizeof(struct sockaddr)) {
        PyErr_SetString(PyExc_ValueError, "Address buffer too small");
        return NULL;
    }
    if(len == -1) {
        len = buflen;
    }
    if(len <= 0 || len > buflen) {
        PyErr_SetString(PyExc_ValueError, "Invalid length specified");
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    ov->callback = object;
    wbuf.len = len;
    wbuf.buf = buf;
    CreateIoCompletionPort((HANDLE)handle, self->iocp, 0, 1);
#ifdef SPEW
    printf("calling WSARecvFrom(%d, 0x%p, %d, 0x%p, 0x%p, 0x%p, 0x%p, 0x%p, 0x%p)\n", handle, &wbuf, 1, &bytes, &flags, (struct sockaddr *)ab->buffer, &ab->size, ov, dummy_completion);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = WSARecvFrom(handle, &wbuf, 1, &bytes, &flags, (struct sockaddr *)ab->buffer, &ab->size, (OVERLAPPED *)ov, dummy_completion);
    Py_END_ALLOW_THREADS;
    err = GetLastError();
    if(res == SOCKET_ERROR && err != ERROR_IO_PENDING) {
        return PyErr_SetFromWindowsErr(err);
    }
    return Py_BuildValue("ll", err, bytes);
}

// yay, rape'n'paste of getsockaddrarg from socketmodule.c. "I couldn't understand what it does, so I removed it!"
static int makesockaddr(int sock_family, PyObject *args, struct sockaddr **addr_ret, int *len_ret)
{
    switch (sock_family) {
    case AF_INET:
    {
        struct sockaddr_in* addr;
        char *host;
        int port;
        unsigned long result;
        if(!PyTuple_Check(args)) {
            PyErr_Format(PyExc_TypeError, "AF_INET address must be tuple, not %.500s", args->ob_type->tp_name);
            return 0;
        }
        if(!PyArg_ParseTuple(args, "si", &host, &port)) {
            return 0;
        }
        addr = PyMem_Malloc(sizeof(struct sockaddr_in));
        result = inet_addr(host);
        if(result == -1) {
            PyMem_Free(addr);
            PyErr_SetString(PyExc_ValueError, "Can't parse ip address string");
            return 0;
        }
#ifdef SPEW
        printf("makesockaddr setting addr, %lu, %d, %hu\n", result, AF_INET, htons((short)port));
#endif
        addr->sin_addr.s_addr = result;
        addr->sin_family = AF_INET;
        addr->sin_port = htons((short)port);
        *addr_ret = (struct sockaddr *) addr;
        *len_ret = sizeof *addr;
        return 1;
    }
    default:
        PyErr_SetString(PyExc_ValueError, "bad family");
        return 0;
    }
}

static PyObject *iocpcore_WSASendTo(iocpcore* self, PyObject *args) {
    SOCKET handle;
    char *buf;
    int buflen, res, len = -1, addrlen, family;
    DWORD bytes, err, flags;
    PyObject *object, *address;
    MyOVERLAPPED *ov;
    WSABUF wbuf;
    struct sockaddr *addr;
    if(!PyArg_ParseTuple(args, "lit#OO|ll", &handle, &family, &buf, &buflen, &object, &address, &len, &flags)) {
        return NULL;
    }
    if(len == -1) {
        len = buflen;
    }
    if(len <= 0 || len > buflen) {
        PyErr_SetString(PyExc_ValueError, "Invalid length specified");
        return NULL;
    }
    if(!makesockaddr(family, address, &addr, &addrlen)) {
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    ov->callback = object;
    wbuf.len = len;
    wbuf.buf = buf;
    CreateIoCompletionPort((HANDLE)handle, self->iocp, 0, 1);
#ifdef SPEW
    printf("calling WSASendTo(%d, 0x%p, %d, 0x%p, %d, 0x%p, %d, 0x%p, 0x%p)\n", handle, &wbuf, 1, &bytes, flags, addr, addrlen, ov, dummy_completion);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = WSASendTo(handle, &wbuf, 1, &bytes, flags, addr, addrlen, (OVERLAPPED *)ov, dummy_completion);
    Py_END_ALLOW_THREADS;
    err = GetLastError();
#ifdef SPEW
    printf("    st returned %d, err %d\n", res, err);
#endif
    if(res == SOCKET_ERROR && err != ERROR_IO_PENDING) {
        return PyErr_SetFromWindowsErr(err);
    }
    return Py_BuildValue("ll", err, bytes);
}

static PyObject *iocpcore_getsockinfo(iocpcore* self, PyObject *args) {
    SOCKET handle;
    WSAPROTOCOL_INFO pinfo;
    int size = sizeof(pinfo), res;
    if(!PyArg_ParseTuple(args, "l", &handle)) {
        return NULL;
    }
    res = getsockopt(handle, SOL_SOCKET, SO_PROTOCOL_INFO, (char *)&pinfo, &size);
    if(res == SOCKET_ERROR) {
        return PyErr_SetFromWindowsErr(0);
    }
    return Py_BuildValue("iiii", pinfo.iMaxSockAddr, pinfo.iAddressFamily, pinfo.iSocketType, pinfo.iProtocol);
}

static PyObject *iocpcore_AcceptEx(iocpcore* self, PyObject *args) {
    SOCKET handle, acc_sock;
    char *buf;
    int buflen, res;
    DWORD bytes, err;
    PyObject *object;
    MyOVERLAPPED *ov;
    if(!PyArg_ParseTuple(args, "llOw#", &handle, &acc_sock, &object, &buf, &buflen)) {
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    ov->callback = object;
    CreateIoCompletionPort((HANDLE)handle, self->iocp, 0, 1);
#ifdef SPEW
    printf("calling AcceptEx(%d, %d, 0x%p, %d, %d, %d, 0x%p, 0x%p)\n", handle, acc_sock, buf, 0, buflen/2, buflen/2, &bytes, ov);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = gAcceptEx(handle, acc_sock, buf, 0, buflen/2, buflen/2, &bytes, (OVERLAPPED *)ov);
    Py_END_ALLOW_THREADS;
    err = WSAGetLastError();
#ifdef SPEW
    printf("    ae returned %d, err %d\n", res, err);
#endif
    if(!res && err != ERROR_IO_PENDING) {
        return PyErr_SetFromWindowsErr(err);
    }
    if(res) {
        err = 0;
    }
    return Py_BuildValue("ll", err, 0);
}

static PyObject *iocpcore_ConnectEx(iocpcore* self, PyObject *args) {
    SOCKET handle;
    int res, addrlen, family;
    DWORD err;
    PyObject *object, *address;
    MyOVERLAPPED *ov;
    struct sockaddr *addr;
    if(!PyArg_ParseTuple(args, "liOO", &handle, &family, &address, &object)) {
        return NULL;
    }
    if(!makesockaddr(family, address, &addr, &addrlen)) {
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    ov->callback = object;
    CreateIoCompletionPort((HANDLE)handle, self->iocp, 0, 1);
#ifdef SPEW
    printf("calling ConnectEx(%d, 0x%p, %d, 0x%p)\n", handle, addr, addrlen, ov);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = gConnectEx(handle, addr, addrlen, NULL, 0, NULL, (OVERLAPPED *)ov);
    Py_END_ALLOW_THREADS;
    PyMem_Free(addr);
    err = WSAGetLastError();
#ifdef SPEW
    printf("    ce returned %d, err %d\n", res, err);
#endif
    if(!res && err != ERROR_IO_PENDING) {
        return PyErr_SetFromWindowsErr(err);
    }
    if(res) {
        err = 0;
    }
    return Py_BuildValue("ll", err, 0);
}

static PyObject *iocpcore_PostQueuedCompletionStatus(iocpcore* self, PyObject *args) {
    int res;
    DWORD err;
    PyObject *object;
    MyOVERLAPPED *ov;
    if(!PyArg_ParseTuple(args, "O", &object)) {
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    ov->callback = object;
#ifdef SPEW
    printf("calling PostQueuedCompletionStatus(0x%p)\n", ov);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = PostQueuedCompletionStatus(self->iocp, 0, 0, (OVERLAPPED *)ov);
    Py_END_ALLOW_THREADS;
    err = WSAGetLastError();
#ifdef SPEW
    printf("    pqcs returned %d, err %d\n", res, err);
#endif
    if(!res && err != ERROR_IO_PENDING) {
        return PyErr_SetFromWindowsErr(err);
    }
    if(res) {
        err = 0;
    }
    return Py_BuildValue("ll", err, 0);
}

PyObject *iocpcore_AllocateReadBuffer(PyObject *self, PyObject *args)
{
    int bufSize;
    if(!PyArg_ParseTuple(args, "i", &bufSize)) {
        return NULL;
    }
    return PyBuffer_New(bufSize);
}

static PyMethodDef iocpcore_methods[] = {
    {"doIteration", (PyCFunction)iocpcore_doIteration, METH_VARARGS,
     "Perform one event loop iteration"},
    {"issueWriteFile", (PyCFunction)iocpcore_WriteFile, METH_VARARGS,
     "Issue an overlapped WriteFile operation"},
    {"issueReadFile", (PyCFunction)iocpcore_ReadFile, METH_VARARGS,
     "Issue an overlapped ReadFile operation"},
    {"interpretAB", (PyCFunction)iocpcore_interpretAB, METH_VARARGS,
     "Interpret address buffer as returned by WSARecvFrom"},
    {"issueWSARecvFrom", (PyCFunction)iocpcore_WSARecvFrom, METH_VARARGS,
     "Issue an overlapped WSARecvFrom operation"},
    {"issueWSASendTo", (PyCFunction)iocpcore_WSASendTo, METH_VARARGS,
     "Issue an overlapped WSASendTo operation"},
    {"issueAcceptEx", (PyCFunction)iocpcore_AcceptEx, METH_VARARGS,
     "Issue an overlapped AcceptEx operation"},
    {"issueConnectEx", (PyCFunction)iocpcore_ConnectEx, METH_VARARGS,
     "Issue an overlapped ConnectEx operation"},
    {"issuePostQueuedCompletionStatus", (PyCFunction)iocpcore_PostQueuedCompletionStatus, METH_VARARGS,
     "Issue an overlapped PQCS operation"},
    {"getsockinfo", (PyCFunction)iocpcore_getsockinfo, METH_VARARGS,
     "Given a socket handle, retrieve its protocol info"},
    {"AllocateReadBuffer", (PyCFunction)iocpcore_AllocateReadBuffer, METH_VARARGS,
     "Allocate a buffer to read into"},
    {NULL}
};

static PyTypeObject iocpcoreType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "iocpcore.iocpcore",             /*tp_name*/
    sizeof(iocpcore),             /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)iocpcore_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "core functionality for IOCP reactor",           /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    iocpcore_methods,             /* tp_methods */
//    iocpcore_members,             /* tp_members */
    0,             /* tp_members */
//    iocpcore_getseters,           /* tp_getset */
    0,           /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
//    (initproc)iocpcore_init,      /* tp_init */
    0,      /* tp_init */
    0,                         /* tp_alloc */
    iocpcore_new,                 /* tp_new */
};

static PyMethodDef module_methods[] = {
    {NULL}  /* Sentinel */
};

#ifndef PyMODINIT_FUNC /* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
initiocpcore(void) 
{
    PyObject *m;
    GUID guid1 = WSAID_CONNECTEX; // should use one GUID variable, but oh well
    GUID guid2 = WSAID_ACCEPTEX;
    DWORD bytes, ret;
    SOCKET s;
    if(PyType_Ready(&iocpcoreType) < 0) {
        return;
    }
    m = PyImport_ImportModule("_socket"); // cause WSAStartup to get called
    if(!m) {
        return;
    }

    s = socket(AF_INET, SOCK_STREAM, 0);
    ret = WSAIoctl(s, SIO_GET_EXTENSION_FUNCTION_POINTER, &guid1, sizeof(GUID),
                   &gConnectEx, sizeof(gConnectEx), &bytes, NULL, NULL);
    if(ret == SOCKET_ERROR) {
        PyErr_SetFromWindowsErr(0);
        return;
    }
    
    ret = WSAIoctl(s, SIO_GET_EXTENSION_FUNCTION_POINTER, &guid2, sizeof(GUID),
                   &gAcceptEx, sizeof(gAcceptEx), &bytes, NULL, NULL);
    if(ret == SOCKET_ERROR) {
        PyErr_SetFromWindowsErr(0);
        return;
    }

    closesocket(s);

    m = Py_InitModule3("iocpcore", module_methods,
                       "core functionality for IOCP reactor");

    if(!m) {
        return;
    }

    Py_INCREF(&iocpcoreType);
    PyModule_AddObject(m, "iocpcore", (PyObject *)&iocpcoreType);
}

