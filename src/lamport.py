import logging

class LamportClock:
    def __init__(self, port):
        self.time = 0
        self.proc_id = port
    
    def update_time(self, time=0):
        self.time = max(self.time, time) + 1
        logging.debug("Updated lamport clock to {}".format(self.time))
        return self.time
    
