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

class Client:
    def __init__(self, port):
        # setup sockets
        self.listener = SimpleSocket(listener=True, bind_addr=('0.0.0.0'), bind_port=port)
        self.listener.bind()
        self.listener.socket.listen(5)
        logging.debug("Listening socket bound to {}".format(self.listener.bind_address_port))
        self.incoming_map = {}
        self.outgoing_map = {}
        # lamports clock and dme
        self.lclock = LamportClock(port)
        self.queue = deque()
        self.socket_list = [self.listener.socket]
        self.clients = []
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line != port:
                    logging.debug("Adding client {} to the list".format(line))
                    self.clients.append(line)
    
    def create_connections(self):
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
                            message = sock.recv(1024)
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
                                self.handle_dme_message(message, client)
                        except Exception:
                            logging.exception("Error while trying to read from incoming sockets")
                time.sleep(0.1)
        except Exception:
            logging.exception("Error")
            return

    def start_dme(self):
        logging.info("Starting Lamport's DME")
        self.queue.append((self.lclock.proc_id, 1)) # (proc_id, no. of grants/ack; 1 is ack from self) 
        logging.debug("Queue = {}".format(self.queue))
        self.lclock.update_time()
        message = struct.pack('3si',bytes("REQ","utf-8"), self.lclock.time)
        for client in self.clients:
            outgoing_sock = self.outgoing_map[client]
            logging.info("Sending REQ to {}".format(client))
            outgoing_sock.send(bytes(message))

    def end_dme(self):
        logging.info("Ending Lamport's DME")
        # reverse the steps of start_dme 
        for i in range(len(self.queue)):
            if(self.queue[i][0]==self.lclock.proc_id):
                self.queue.remove(self.queue[i])
                break
        logging.debug("Queue = {}".format(self.queue))
        self.lclock.update_time()
        message = struct.pack('3si', bytes("REL", "utf-8"), self.lclock.time)
        for client in self.clients:
            outgoing_sock = self.outgoing_map[client]
            logging.info("Sending REL to {}".format(client))
            outgoing_sock.send(bytes(message))

    def handle_dme_message(self, message, client):
        message_tuple = struct.unpack('3si', message)
        message_type = message_tuple[0].decode('utf-8').strip()
        remote_lclock = message_tuple[1]
        self.lclock.update_time(remote_lclock)

        if message_type == "REQ":
            logging.debug("REQ from {}".format(client))
            self.queue.append((client, None)) #TODO: This should be made more robust
            sock = self.outgoing_map[client]
            self.lclock.update_time()
            outgoing_message = struct.pack('3si', bytes("GRA", "utf-8"), self.lclock.time)
            logging.debug("Sending GRA to {}".format(client))
            sock.send(bytes(outgoing_message))
        elif message_type == "GRA":
            # search for my request
            for i in range(len(self.queue)):
                if(self.queue[i][0]==self.lclock.proc_id):
                    if(self.queue[i][1]==len(self.clients)+1):
                        continue
                    updated_tup = (self.lclock.proc_id, self.queue[i][1]+1)
                    self.queue[i] = updated_tup
        elif message_type == "REL":
            logging.debug("REL from {}".format(client))
            self.queue.remove((client, None))
        logging.debug("Queue = {}".format(self.queue))


    
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
                    # Transfer transaction
                    self.start_dme()
                    # wait for GRA from everyone
                    # Access server
                    # release DME
                elif(inp == "b"):
                    # Balance transaction
                    pass
                elif(inp == "r"):
                    self.end_dme()
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