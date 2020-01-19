import sys
import logging
from simple_socket import SimpleSocket

CONFIG_FILE = 'config.cfg'

class Client:
    def __init__(self, port):
        self.listener = SimpleSocket(listener=True, bind_addr=('0.0.0.0'), bind_port=port)
        self.clients = []
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                if line is not port:
                    self.clients.append(line)
    
    def create_connections(self):
        self.client_sock=[]
        for client in self.clients:
            self.client_sock.append(SimpleSocket(dest_addr=('0.0.0.0'), dest_port=client))

    def cleanup(self):
        for client in self.client_sock:
            client.socket.close()
        self.listener.socket.close()
    
    def repl(self):
        print("To begin, press Enter")
        _ = input()
        self.create_connections()
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
    logging.debug("Starting Client")
    c = Client(port)
    c.repl()