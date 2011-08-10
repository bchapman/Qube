'''
renderTalk
Author: Brennan Chapman

Communicates with an active After Effects
session through a socket.

Socket Commands:
Render (frameRange)
    Renders a range of frames
    Ex: Render 1-10,15
Exit
    Closes after effects.
'''

import sys
import socket

class renderTalk:
    def __init__(self, host='localhost', port):
        
        self.conn = None
        for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
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
            print 'ERROR: Could not open socket'
            sys.exit(1)


# Echo client program
while 1:
    data = s.recv(1024)
    if not data:
        break
    else:
        print 'Received', repr(data)
    s.send('Hi There!\n')
s.close()

HOST = 'localhost' # Local host
PORT = 5001              # The same port as used by the server
s = None
