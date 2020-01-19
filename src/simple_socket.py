"""
SimpleSocket is a wrapper around the socket library

Author: Rakshith G (hehaichi@gmail.com)
"""

import socket
from functools import wraps

def check_listener(f):
    """Decorator to check if the function is run on a listener type socket"""
    @wraps(f)
    def check(self):
        if self.listener:
            return f(self)
        else:
            raise AttributeError('Cannot call {} on non-listening socket'.format(f.__name__))
    return check

def check_non_listener(f):
    """Check if f is run on a non-listener socket"""
    @wraps(f)
    def check(self):
        if not self.listener:
            return f(self)
        else:
            raise AttributeError('Cannot call {} on listening socket'.format(f.__name__))
    return check

class SimpleSocket:
    def __init__(self, listener=False, **kwargs):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.listener = listener
        if self.listener:
            self.bind_address_port = (kwargs.get('bind_addr'), int(kwargs.get('bind_port')))
        else:
            self.destination = (kwargs.get('dest_addr'), int(kwargs.get('dest_port')))

    @check_listener
    def bind(self):
        self.socket.bind(self.bind_address_port)
    
    @check_non_listener
    def connect(self):
        self.socket.connect(self.destination)
    
    def send(self, message):
        self.socket.send(message)
    
    def receive(self):
        message = self.socket.recv(1024)
        return message

