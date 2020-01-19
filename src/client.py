import sys
import logging
import select
import threading
import socket
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
        # lamports clock
        self.lclock = LamportClock(port)
        self.socket_list = [self.listener.socket]
        self.clients = []
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line != port:
                    logging.debug("Adding client {} to the list".format(line))
                    self.clients.append(line)
    
    def create_connections(self):
        self.client_sock=[]
        for client in self.clients:
            sock = SimpleSocket(dest_addr=('0.0.0.0'), dest_port=client)
            sock.connect()
            self.client_sock.append(sock)

    def cleanup(self):
        for client in self.client_sock:
            client.socket.close()
        self.listener.socket.close()

    def handle_connections(self):
        try:
            while 1:
                read, _, _ = select.select(self.socket_list, [], [], 0)
                for sock in read:
                    if sock == self.listener.socket:
                        sockfd, addr = self.listener.socket.accept()
                        self.socket_list.append(sockfd)
                        logging.debug("Accepted new connection from {}".format(addr))
                    else:
                        try:
                            message = sock.recv(1024)
                            logging.debug("{} - {}".format(sock.getpeername(), message))
                            if message == b'':
                                sock.shutdown(socket.SHUT_RDWR)
                                sock.close()
                                self.socket_list.remove(sock)
                        except Exception:
                            logging.exception("Error while trying to read from incoming sockets")
                            continue
        except:
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
                print("$> ")
                inp = input()
                if(inp == "t"):
                    # Transfer transaction
                    pass
                elif(inp == "b"):
                    # Balance transaction
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