#include <unistd.h>
#include <queue>
#include <deque>
#include <sys/uio.h>
#include <boost/python.hpp> 
#include <boost/python/call_method.hpp>
#include <boost/shared_ptr.hpp>
#include <Python.h>
#include <twisted/util.h>


#ifndef TWISTED_TCP_H
#define TWISTED_TCP_H


namespace Twisted 
{
    // Base class for owners of buffers that can be written:
    class BufferOwner
    {
    public:
	virtual ~BufferOwner() {}
    };
    typedef boost::shared_ptr<BufferOwner> OwnerPtr;
}


// private implementation details
namespace TwistedImpl
{
    typedef Twisted::OwnerPtr OwnerPtr;

    // bool indicates if this has a OwnerPtr:
    typedef std::queue<std::pair<bool,OwnerPtr> > OwnerQueue;
    
    struct IOVecManager {
	iovec* m_vecs;
	size_t m_len; // number of iovecs
	size_t m_offset; // starting point off m_vecs
	size_t m_used; // number of iovecs used from m_offset on
	OwnerQueue m_ownerqueue;
	size_t m_bytessent; // number bytes already sent from m_vecs[m_offset];
	
	// Make sure we can add another item to m_vecs:
	void ensureEnoughSpace();
	
	// fix first item to take into account m_bytessent:
	inline void twiddleFirst() {
	    m_vecs[m_offset].iov_base = (char*)(m_vecs[m_offset].iov_base) + m_bytessent;
	    m_vecs[m_offset].iov_len -= m_bytessent;
	}

	// unfix first item to no longer take into account m_bytessent:
	inline void untwiddleFirst() {
	    m_vecs[m_offset].iov_base = (char*)(m_vecs[m_offset].iov_base) - m_bytessent;
	    m_vecs[m_offset].iov_len += m_bytessent;
	}
	
	inline void reallyAdd(const char* buf, size_t len, OwnerPtr p, bool isExternal) {
	    ensureEnoughSpace();
	    m_vecs[m_offset + m_used].iov_base = (void*) buf;
	    m_vecs[m_offset + m_used].iov_len = len;
	    m_used += 1;
	    m_ownerqueue.push(std::make_pair(isExternal, p));
	}
		
	// Adding locally owned storage:
	inline void add(const char* buf, size_t len) {
	    if (m_used && m_vecs[m_offset + m_used - 1].iov_base == (void*)buf) {
		m_vecs[m_offset + m_used - 1].iov_len += len;
	    } else {
		reallyAdd(buf, len, OwnerPtr(), false);
	    }
	}

	// Add externally owned storage:
	inline void add(const char* buf, size_t len, OwnerPtr p) {
	    reallyAdd(buf, len, p, true);
	}

	IOVecManager() {
	    m_vecs = (iovec*) malloc(sizeof(iovec) * 2048);
	    m_len = 2048;
	    m_offset = 0;
	    m_used = 0;
	    m_bytessent = 0;
	}

	~IOVecManager() {
	    free(m_vecs);
	}
    };
	
    struct LocalBuffer {
	static const size_t CHUNK_SIZE = 65536;
	char* buf;
	size_t numchunks;
	size_t offset; // offset from which filled in bytes start
	size_t len; // len of filled in bytes
	inline size_t available() const {
	    return (numchunks * CHUNK_SIZE) - offset - len;
	}
    };

    struct LocalBufferManager {
	// last item is always supposed to have some space,
	// if there isn't one we add one at the end:
	std::deque<LocalBuffer> m_localbuffers;
	// free part of a buffer. we know which because this will
	// be called in order of writes. specifically, it will
	// be the first item, since if we free all used data
	// we will move the item to the end of the queue or
	// remove it totally:
	void freePartOfBuffer(size_t bytes);
	// get a buffer with the assumption that we will only
	// write this many bytes at most: 
	char* getBuffer(size_t bytes);
	// how many bytes of result of getBuffer we didn't use in the end:
	void didntUse(size_t bytes);
	~LocalBufferManager();
    };    
} // namespace TwistedImpl


namespace Twisted
{
    using namespace boost::python;
    using namespace TwistedImpl;

    class Protocol;     // forward definition

    // The resulting Python class should be wrapped in to the transports
    // in twisted.internet.tcp.
    class TCPTransport
    {
    private:
	// Called by doWrite when write succeeds:
	void wrote(size_t bytes);

	Protocol* m_protocol;
	object m_self;
	int m_sockfd;
	bool m_hasproducer;
	object m_producer;

	// read buffer
	char* m_readbuffer;
	size_t m_readbuflen;

	// write buffer
	bool m_writable;
	IOVecManager m_iovec;
	LocalBufferManager m_local;
	size_t m_bufferedbytes;
    public:
	// Producer attributes we need to share with abstract.FileDescriptor:
	int connected;
	int producerPaused;
	int streamingProducer;
	int disconnecting;

	TCPTransport(object self);
	void initProtocol(); // call when "self.protocol" exists.
	~TCPTransport() {}
	void setReadBuffer(char* buffer, size_t buflen) {
	    m_readbuffer = buffer;
	    m_readbuflen = buflen;
	}
	object doRead();
	object doWrite();

	// Public API for transports:

	template <typename W>
	void write(size_t reserve, W writer) {
	    if (!connected || reserve == 0)
		return;
	    char* buf = m_local.getBuffer(reserve);
	    size_t written = writer(buf);
	    assert (written <= reserve);
	    m_local.didntUse(reserve - written);
	    if (written == 0)
		return;
	    m_iovec.add(buf, written);
	    m_bufferedbytes += written;
	    if (m_hasproducer && m_bufferedbytes > 131072) {
		this->producerPaused = true;
		m_producer.attr("pauseProducing")();
	    }
	    startWriting();
	}

	void write(char* buf, size_t len, OwnerPtr owner) {
	    if (!connected || len == 0)
		return;
	    m_iovec.add(buf, len, owner);
	    m_bufferedbytes += len;
	    if (m_hasproducer && m_bufferedbytes > 131072) {
		this->producerPaused = true;
		m_producer.attr("pauseProducing")();
	    }
	    startWriting();
	}

	void loseConnection() { m_self.attr("loseConnection")(); }

	void _setProducer(object p) {
	    m_producer = p;
	    m_hasproducer = (m_producer != object());
	}

	object _getProducer() {
	    return m_producer;
	}

	void registerProducer(object p, bool push) {
	    m_self.attr("registerProducer")(p, push);
	}

	void unregisterProducer() { 
	    m_self.attr("unregisterProducer")();
	}

	inline void startWriting() {
	    if (!m_writable) {
		m_self.attr("reactor").attr("addWriter")(m_self);
		m_writable = true;
	    }
	}
	void stopWriting() {
	    if (m_writable) {
		m_self.attr("reactor").attr("removeWriter")(m_self);
		m_writable = false;
	    }
	}
    };

    class Protocol
    {
    public:
	PyObject* self;
	object transportobj; // so that we have INCREF the transport
	TCPTransport* transport;

	Protocol() : transport(NULL) {};
	virtual ~Protocol() {}
	void init(PyObject* s) { 
	    this->self = s;
	}
	void makeConnection(object t) {
	    this->transportobj = t;
	    this->transport = extract<TCPTransport*>(t);
	    call_method<void>(self, "connectionMade");
	}
	virtual void connectionMade() {}
	virtual void connectionLost(object reason) {}
	virtual void dataReceived(char* buf, int buflen) = 0;
	virtual void bufferFull() = 0;
    };
}

#endif
