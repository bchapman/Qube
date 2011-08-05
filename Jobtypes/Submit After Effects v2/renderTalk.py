# Echo client program
import socket
import sys

HOST = 'localhost' # Local host
PORT = 5001              # The same port as used by the server
s = None
for res in socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM):
    af, socktype, proto, canonname, sa = res
    try:
        s = socket.socket(af, socktype, proto)
    except socket.error, msg:
        s = None
        continue
    try:
        s.connect(sa)
    except socket.error, msg:
        s.close()
        s = None
        continue
    break
if s is None:
    print 'could not open socket'
    sys.exit(1)
while 1:
    data = s.recv(1024)
    if not data:
        break
    else:
        print 'Received', repr(data)
    s.send('Hi There!\n')
s.close()