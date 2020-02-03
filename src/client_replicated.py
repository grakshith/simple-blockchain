import sys
import logging
import select
import threading
import socket
from collections import deque
import re
import struct
from simple_socket import SimpleSocket
from lamport import LamportClock
import time

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

class TwoDTT:
    def __init__(self, clients, my_port):
        self.tt = []
        self.my_row = my_port-8000
        self.row_len = len(clients) + 1
        for _ in self.row_len:
            tt.append([0 for _ in range(self.row_len)])
    
    def update_other_rows(self, twodtt):
        for i in range(self.row_len):
            if i == self.my_row:
                continue
            for j in range(self.row_len):
                tt[i][j] = max(tt[i][j], twodtt[i][j])
    
    def update_my_row(self):
        max_val = 0
        for j in range(self.row_len):
            for i in range(self.row_len):
                max_val = max(self.tt[i][j])
            self.tt[self.my_row] = max_val


class Client:
    def __init__(self, port):
        # setup sockets
        self.listener = SimpleSocket(listener=True, bind_addr=('0.0.0.0'), bind_port=port)
        self.listener.bind()
        self.listener.socket.listen(5)
        logging.debug("Listening socket bound to {}".format(self.listener.bind_address_port))
        self.incoming_map = {}
        self.outgoing_map = {}
        # lamports clock and blockchain
        self.blockchain = LinkedList()
        self.lclock = LamportClock(port)
        self.socket_list = [self.listener.socket]
        self.clients = []
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line != port:
                    logging.debug("Adding client {} to the list".format(line))
                    self.clients.append(line)
        self.time_table = TwoDTT(self.clients, port)
    
    def create_connections(self):
        # client sockets
        for client in self.clients:
            sock = SimpleSocket(dest_addr=('0.0.0.0'), dest_port=client)
            self.outgoing_map[client] = sock
            sock.connect()
            logging.debug("Outgoing to {} = {}".format(client, sock.socket.getsockname()))
            sock.send(bytes(str(self.listener.bind_address_port[1]), 'UTF-8'))

    def cleanup(self):
        for client in self.clients:
            self.outgoing_map[client].socket.close()
            del(self.outgoing_map[client])
        self.listener.socket.close()

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
                            message = sock.recv(8)
                            logging.debug("{} - {}".format(sock.getpeername(), message))
                            if re.match("[0-9]+", message.decode('utf-8').strip()):
                                self.incoming_map[sock] = message.decode('utf-8').strip()
                                logging.debug("{} = {}".format(message.decode('utf-8').strip(), sock.getpeername()))
                            elif message == b'':
                                sock.shutdown(socket.SHUT_RDWR)
                                sock.close()
                                self.socket_list.remove(sock)
                                del(self.incoming_map[sock])
                            else:
                                client = self.incoming_map[sock]
                                # for i in range(len(message)):
                                #     chunk = message[i:i+8]
                                #     logging.debug("Chunk = {}, i={}, i+8={}, message={}".format(chunk,i,i+8, message))
                                #     i = i+8
                                self.handle_message(message, client)
                        except Exception:
                            logging.exception("Error while trying to read from incoming sockets")
                time.sleep(0.1)
        except Exception:
            logging.exception("Error")
            return

    def repl(self):
        print("To begin, press Enter")
        _ = input()
        # create connections and start new thread to handle them
        self.create_connections()
        conn_thread = threading.Thread(target=self.handle_connections)
        conn_thread.daemon = True
        conn_thread.start()
        try:
            while(True):
                print("$> ", end='')
                inp = input()
                if(inp == "t"):
                    pass
                elif(inp == "s"):
                    pass
                else:
                    continue
        except KeyboardInterrupt:
            print("Closing all sockets and terminating")
            self.cleanup()
            sys.exit(1)

if __name__ == "__main__":
    if(len(sys.argv)<2):
        print("Port is required")
        sys.exit(1)
    port = sys.argv[1]

    # Logging Configuration
    extra = {'port': port}

    logging.basicConfig(
        handlers = [
            logging.FileHandler("{}.log".format(port)),
            logging.StreamHandler()
        ],
        level=logging.DEBUG,
        format='%(asctime)s - [%(levelname)s]: [%(port)s] - %(message)s', datefmt="%Y-%m-%d %H:%M:%S %z"
        )
    logger = logging.getLogger(__name__)
    logging = logging.LoggerAdapter(logger, extra)
    logging.info("Starting Client")
    c = Client(port)
    c.repl()