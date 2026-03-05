import tkinter as tk
import logging

class LoggingMiddleware(logging.Handler):
    """This class allows you to log to a Tkinter Text or ScrolledText widget"""
    def __init__(self, gui=None):
        logging.Handler.__init__(self)
        self.logging_widget = gui.logging_widget

    def emit(self, record):
        formatter = logging.Formatter('[%(asctime)s] %(message)s')#
        self.setFormatter(formatter)#
        msg = self.format(record)
        
        def append():
            self.logging_widget.configure(state='normal')
            self.logging_widget.insert(tk.END, msg + '\n')
            self.logging_widget.configure(state='disabled')
            self.logging_widget.yview(tk.END)
        self.logging_widget.after(0, append)
