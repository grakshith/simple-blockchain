import sys
import logging
import threading
import socket
import time
import select
import re
import struct
from simple_socket import SimpleSocket

CONFIG_FILE = 'config.cfg'

class Node:
    def __init__(self, data=None, next=None, prev=None):
        self.data = data
        # data = {
        #    'type': "TRA",
        #    'src' : 8000,
        #    'dest': 8001,
        #    'amt': 5    
        # }
        self.next = next
        self.prev = prev

    def __repr__(self):
        return str(self.data)

class LinkedList:
    def __init__(self):
        self.head = None

    def prepend(self, data):
        new_head = Node(data=data, next=self.head)
        if self.head:
            self.head.prev = new_head
        self.head = new_head

    def append(self, data):
        if not self.head:
            self.head = Node(data=data)
            return
        curr = self.head
        while curr.next:
            curr = curr.next
        curr.next = Node(data=data, prev=curr)

class Server:
    def __init__(self):
        self.listener = SimpleSocket(listener=True, bind_addr=('0.0.0.0'), bind_port=5535)
        self.listener.bind()
        self.listener.socket.listen(5)
        logging.debug("Listening socket bound to {}".format(self.listener.bind_address_port))
        self.blockchain = LinkedList()
        self.clients = []
        self.incoming_map = {}
        self.outgoing_map = {}
        self.socket_list = [self.listener.socket]
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                logging.debug("Adding client {} to the list".format(line))
                self.clients.append(line)

    def init_blockchain(self):
        for client in self.clients:
            data = {
                'type': "INIT",
                'src': 0,
                'dest': int(client),
                'amt': 10.0
            }
            self.blockchain.append(data)

    def cleanup(self):
        for client in self.clients:
            if(self.outgoing_map.get(client)):
                try:
                    self.outgoing_map[client].close()
                    sock = self.outgoing_map[client]
                    del(self.incoming_map[sock])
                    del(sock)
                except:
                    #assume everything is closed
                    pass
        return


    def handle_connections(self):
        try:
            while 1:
                read, _, _ = select.select(self.socket_list, [], [], 0)
                for sock in read:
                    if sock == self.listener.socket:
                        sockfd, addr = self.listener.socket.accept()
                        self.socket_list.append(sockfd)
                        logging.info("Accepted new connection from {}".format(addr))
                    else:
                        try:
                            message = sock.recv(1024)
                            logging.debug("{} - {}".format(sock.getpeername(), message))
                            if re.match("[0-9]+", message.decode('utf-8').strip()):
                                self.incoming_map[sock] = message.decode('utf-8').strip()
                                self.outgoing_map[message.decode('utf-8').strip()] = sock
                                logging.debug("{} = {}".format(message.decode('utf-8').strip(), sock.getpeername()))
                            elif message==b'':
                                sock.shutdown(socket.SHUT_RDWR)
                                sock.close()
                                self.socket_list.remove(sock)
                                client = self.incoming_map[sock]
                                del(self.incoming_map[sock])
                                del(self.outgoing_map[client])
                            else:
                                client = self.incoming_map[sock]
                                self.handle_transaction(message, client)
                        except Exception:
                            logging.exception("Error while trying to read form incoming sockets")
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.cleanup()
            logging.exception("Error")
            return

    def check_transaction_validity(self, message_tuple):
        client_balance = {0:30.0}
        # Initialise initial balance
        for client in self.clients:
            client_balance[int(client)] = 0.0
        # iterate through the blockchain to see the balance of each client at the last block
        curr = self.blockchain.head
        while curr:
            data = curr.data
            src = data['src']
            dest = data['dest']
            amt = data['amt']
            client_balance[src] -= amt
            client_balance[dest] +=amt
            curr = curr.next
        message_type = message_tuple[0].decode('utf-8').strip()
        src = message_tuple[1]
        dest = message_tuple[2]
        amt = message_tuple[3]
        logging.debug("Balance vector = {}".format(client_balance))
        if message_type == "BAL":
            return client_balance[message_tuple[1]]
        elif message_type == "TRA":
            if amt<=client_balance[src]:
                return "VALID"
            else:
                return "INVALID"

    def handle_transaction(self, message, client):
        message_tuple = struct.unpack('3siii', message)
        message_type = message_tuple[0].decode('utf-8').strip()
        logging.debug("Message tuple = {}".format(message_tuple))
        src = message_tuple[1]
        dest = message_tuple[2]
        amt = message_tuple[3]
        status = self.check_transaction_validity(message_tuple)
        logging.debug("Transaction status: {}".format(status))
        if message_type == "TRA":
            if status == "VALID":
                data = {
                    'type': 'TRA',
                    'src': src,
                    'dest': dest,
                    'amt': amt
                }
                self.blockchain.append(data)
                status_msg = struct.pack('9s', bytes("SUCCESS", 'utf-8'))
                logging.debug("Sending SUCCESS to {}".format(src))
                self.outgoing_map[str(src)].send(bytes(status_msg))
            else:
                status_msg = struct.pack('9s', bytes("INCORRECT", 'utf-8'))
                logging.debug("Sending INCORRECT to {}".format(src))
                self.outgoing_map[str(src)].send(bytes(status_msg))
        elif message_type == "BAL":
            status_msg = struct.pack('7sf', bytes("BALANCE", 'utf-8'), status)
            logging.debug("Sending balance to {}".format(src))
            self.outgoing_map[str(src)].send(bytes(status_msg))




if __name__ == "__main__":
    # Logging Configuration

    logging.basicConfig(
        handlers = [
            logging.FileHandler("Server.log"),
            logging.StreamHandler()
        ],
        level=logging.DEBUG,
        format='%(asctime)s - [%(levelname)s]: %(message)s', datefmt="%Y-%m-%d %H:%M:%S %z"
        )
    logging.info("Starting Client")
    c = Server()
    c.init_blockchain()
    c.handle_connections()



