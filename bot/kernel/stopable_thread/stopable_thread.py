import threading

class StoppableThread():
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self):
        pass

    def run(self, *args, **kwargs):
        self.th = threading.Thread(*args, **kwargs)
        self.th._stop = threading.Event()
        self.th.start()

    def stop(self):
        self.th._stop.set()

    def get_ident(self):
        return self.th.ident

    def stopped(self):
        return self.th._stop.isSet()
