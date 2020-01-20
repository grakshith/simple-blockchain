import logging

logger = logging.getLogger('client')

class LamportClock:
    def __init__(self, port, time=0):
        self.time = time
        self.proc_id = port
        # Logging configuration
        # need to send create a logging adapter just as we had done in client
        # otherwise this logger is not compatible with client logger
        extra = {'port':port}
        global logger
        logger = logging.LoggerAdapter(logger, extra)        
    
    def update_time(self, time=0):
        self.time = max(self.time, time) + 1
        logger.debug("Updated lamport clock to {}".format(self.time))
        return self.time
    
