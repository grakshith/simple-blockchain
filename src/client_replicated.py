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
        self.my_row = int(my_port)-8000
        self.row_len = len(clients) + 1
        for _ in range(self.row_len):
            self.tt.append([0 for _ in range(self.row_len)])
        logging.debug("Initialize TT = {}".format(self.tt))
    
    def update_other_rows(self, twodtt):
        for i in range(self.row_len):
            if i == self.my_row:
                continue
            for j in range(self.row_len):
                self.tt[i][j] = max(self.tt[i][j], twodtt[i][j])
        logging.debug("Afer updating other rows = {}".format(self.tt))
    
    def update_my_row(self):
        for j in range(self.row_len):
            max_val = 0
            for i in range(self.row_len):
                max_val = max(max_val,self.tt[i][j])
            self.tt[self.my_row][j] = max_val
        

    def update_my_cell(self, lclock):
        self.tt[self.my_row][self.my_row] = lclock

    def unroll(self):
        unrolled = []
        for i in range(self.row_len):
            for j in range(self.row_len):
                unrolled.append(self.tt[i][j])
        return unrolled



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
        self.balance = 10.0
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
                                # message is the header
                                length_tuple = struct.unpack('=chic',message)
                                message_length = length_tuple[2]
                                logging.debug("Message length = {}".format(message_length))
                                blockchain = sock.recv(message_length)
                                logging.debug("Partial blockchain = {} - {}".format(sock.getpeername(), blockchain))
                                unpacked_blockchain = struct.unpack('{}i'.format(message_length/4), blockchain)
                                serialized_tt = sock.recv(9*4)
                                logging.debug("Serialized TT = {}".format(serialized_tt))
                                tt = struct.unpack('9i', serialized_tt)
                                reconstructed_tt = [[0,0,0],[0,0,0],[0,0,0]] # TODO: change this if possible
                                for i in range(3):
                                    for j in range(3):
                                        reconstructed_tt[i][j] = tt[3*i+j]
                                logging.debug("Reconstructed TT = {}".format(reconstructed_tt))
                                self.handle_message(length_tuple[1], unpacked_blockchain, client, reconstructed_tt)
                        except Exception:
                            logging.exception("Error while trying to read from incoming sockets")
                time.sleep(0.1)
        except Exception:
            logging.exception("Error")
            return

    def handle_message(self, num_transactions, message, client, tt):
        for i in range(num_transactions):
            tx_type = 'TRA'
            src = message[4*i]
            dest = message[4*i+1]
            amt = message[4*i+2]
            local_time = message[4*i+3]
            data = {
                'type': tx_type,
                'src': src,
                'dest': dest,
                'amt': amt,
                'local_time': local_time
            }
            self.blockchain.append(data)
            logging.debug("Appending to blockchain after receive = {}".format(data))
        self.time_table.update_other_rows(tt)
        self.time_table.update_my_row()
        logging.debug("Updated TT = {}".format(self.time_table.tt))
        




    def has_rec(self, node, recipient):
        event_src = int(node['src'])-8000
        recipient = int(recipient)-8000
        logging.debug("HasRec")
        logging.debug("Recepient = {}, Event_SRC = {}, Node Local Time = {}".format(recipient, event_src, node['local_time']))
        if(self.time_table.tt[recipient][event_src]>=node['local_time']):
            return True
        return False

    def find_subset_log(self, dest):
        dest = int(dest)
        curr = self.blockchain.head
        subset = []
        while curr:
            if self.has_rec(curr.data, dest):
                continue
            else:
                subset.append(curr.data)
            curr = curr.next
        return subset



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
                    print("$> dest = ", end='')
                    dest = input()
                    print("$> amt = ", end='')
                    amt = int(input())
                    if(amt>self.balance):
                        logging.error("Amount greater than the available balance. Aborting transaction!")
                        continue
                    else:
                        self.balance -= amt
                    self.lclock.update_time()
                    self.time_table.update_my_cell(self.lclock.time)
                    logging.debug("Updated 2DTT = {}".format(self.time_table.tt))
                    data = {
                        'type': "TRA",
                        'src': int(self.lclock.proc_id),
                        'dest': int(dest),
                        'amt': int(amt),
                        'local_time': self.lclock.time
                    }
                    self.blockchain.append(data)
                    logging.info('Inserted into the local blockchain {}'.format(data))
                elif(inp == "s"):
                    print("$> dest = ", end='')
                    dest = input()
                    log_subset = self.find_subset_log(dest)
                    # header structure
                    # total 8 bytes - 4 bytes number of transactions + 4 bytes total size of the log
                    header = struct.pack('=chic', bytes('H','utf-8'),len(log_subset), 16*len(log_subset),bytes('H', 'utf-8'))
                    self.outgoing_map[dest].send(bytes(header))
                    unrolled_list = []
                    for item in log_subset:
                        unrolled_list.append(item['src'])
                        unrolled_list.append(item['dest'])
                        unrolled_list.append(item['amt'])
                        unrolled_list.append(item['local_time'])
                    serialized_list = struct.pack('{}i'.format(len(unrolled_list)), *unrolled_list)
                    self.outgoing_map[dest].send(bytes(serialized_list))
                    unrolled_tt = self.time_table.unroll()
                    serialized_tt = struct.pack('{}i'.format(len(unrolled_tt)), *unrolled_tt)
                    self.outgoing_map[dest].send(bytes(serialized_tt))


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