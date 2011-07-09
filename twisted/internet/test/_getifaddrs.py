import socket

from socket import AF_INET, AF_INET6, inet_ntop
from ctypes import (
    CDLL, POINTER, Structure, c_char, c_char_p, c_short, c_ushort, c_int,
    c_uint, c_uint32, c_uint64, c_void_p, c_ubyte, pointer, cast)

families = dict((v, k) for (k, v) in vars(socket).iteritems() if k.startswith("AF_"))

try:
    libc = CDLL("libc.so.6")
except OSError:
    libc = CDLL("libc.dylib")

class in_addr(Structure):
    _fields_ = [
        ("in_addr", c_ubyte * 4),
        ]

class in6_addr(Structure):
    _fields_ = [
        ("in_addr", c_ubyte * 16),
        ]

class sockaddr(Structure):
    _fields_ = [
        ("sin_family", c_ushort),
        ("sin_port", c_ushort),
        ]

class sockaddr_in(Structure):
    _fields_ = [
        ("sin_family", c_ushort),
        ("sin_port", c_ushort),
        ("sin_addr", in_addr),
        ]

class sockaddr_in6(Structure):
    _fields_ = [
        ("sin_family", c_ushort),
        ("sin_port", c_ushort),
        ("sin_flowinfo", c_uint32),
        ("sin_addr", in6_addr),
        ]

class ifaddrs(Structure):
    pass
ifaddrs_p = POINTER(ifaddrs)
ifaddrs._fields_ = [
    ('ifa_next', ifaddrs_p),
    ('ifa_name', c_char_p),
    ('ifa_flags', c_uint32),
    ('ifa_addr', POINTER(sockaddr)),
    ('ifa_netmask', POINTER(sockaddr)),
    ('ifa_dstaddr', POINTER(sockaddr)),
    ('ifa_data', c_void_p)]

getifaddrs = libc.getifaddrs
getifaddrs.argtypes = [POINTER(ifaddrs_p)]
getifaddrs.restype = c_int

freeifaddrs = libc.freeifaddrs
freeifaddrs.argtypes = [ifaddrs_p]
freeifaddrs.restype = c_int

def _interfaces():
    ifaddrs = ifaddrs_p()
    if getifaddrs(pointer(ifaddrs)) < 0:
        raise OSError()
    results = []
    try:
        while ifaddrs:
            if ifaddrs[0].ifa_addr:
                family = ifaddrs[0].ifa_addr[0].sin_family
                if family == AF_INET:
                    addr = cast(ifaddrs[0].ifa_addr, POINTER(sockaddr_in))
                elif family == AF_INET6:
                    addr = cast(ifaddrs[0].ifa_addr, POINTER(sockaddr_in6))
                else:
                    addr = None

                if addr:
                    packed = ''.join(map(chr, addr[0].sin_addr.in_addr[:]))
                    results.append((ifaddrs[0].ifa_name, family, inet_ntop(family, packed)))
            # for k, _ in ifaddrs[0].ifa_addr._fields_:
            #     print k, getattr(ifaddrs[0].ifa_addr, k)
            #     in_addr = ifaddrs[0].ifa_addr.sin_addr.in_addr
            # print (
            #     in_addr >> 24, '.',
            #     in_addr >> 16 & 0xff, '.',
            #     in_addr >> 8 & 0xff, '.',
            #     in_addr & 0xff)

            ifaddrs = ifaddrs[0].ifa_next
    finally:
        freeifaddrs(ifaddrs)
    return results

print _interfaces()
