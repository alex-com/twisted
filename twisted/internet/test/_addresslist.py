from socket import socket, AF_INET6, SOCK_STREAM
from ctypes import WinDLL, byref, create_string_buffer, c_int, c_void_p, get_last_error, POINTER, Structure, addressof, cast, string_at

SIO_ADDRESS_LIST_QUERY = 0x48000016
WSAEFAULT = 10014

class SOCKET_ADDRESS(Structure):
    _fields_ = [('lpSockaddr', c_void_p),
                ('iSockaddrLength', c_int)]

def make_SAL(ln):
    class SOCKET_ADDRESS_LIST(Structure):
        _fields_ = [('iAddressCount', c_int),
                    ('Address', SOCKET_ADDRESS * ln)]
    return SOCKET_ADDRESS_LIST

def win32GetLinkLocalIPv6Addresses():
    ws2_32 = WinDLL('ws2_32', use_last_error = True)
    WSAIoctl = ws2_32.WSAIoctl
    WSAAddressToString = ws2_32.WSAAddressToStringA

    s = socket(AF_INET6, SOCK_STREAM)
    buf = create_string_buffer(4096)
    retBytes = c_int()
    ret = WSAIoctl(s.fileno(), SIO_ADDRESS_LIST_QUERY, 0, 0, buf, 4096, byref(retBytes), 0, 0)
    if ret and get_last_error() == WSAEFAULT: # not enough space
        buf = create_string_buffer(retBytes.value)
        ret = WSAIoctl(s.fileno(), SIO_ADDRESS_LIST_QUERY, 0, 0, buf, retBytes.value, byref(retBytes), 0, 0)
    if ret:
        raise WindowsError(get_last_error())

    addrList = cast(buf, POINTER(make_SAL(0)))
    addrCount = addrList[0].iAddressCount
    addrList = cast(buf, POINTER(make_SAL(addrCount)))

    buf2 = create_string_buffer(1024)

    retList = []
    for i in range(addrList[0].iAddressCount):
        retBytes.value = 1024
        if WSAAddressToString(addrList[0].Address[i].lpSockaddr, addrList[0].Address[i].iSockaddrLength, 0, buf2, byref(retBytes)):
            raise WindowsError(get_last_error())
        retList.append(string_at(buf2))
    return retList

if __name__ == '__main__':
    print win32GetLinkLocalIPv6Addresses()

