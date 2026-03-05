import logging
from logging import handlers
from bot.defines import LOGGER_MESSAGE

class Logger:
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'crit': logging.CRITICAL
    }

    def __init__(self, filename, write_to_file=True, level="info"):
        self.__logger = logging.getLogger(filename)
        formatter = logging.Formatter(LOGGER_MESSAGE)
        self.__logger.setLevel(self.level_relations.get(level))
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        self.__logger.addHandler(sh)

        if write_to_file: 
            th = handlers.TimedRotatingFileHandler(filename=filename, when='D', backupCount=1, encoding='utf-8')
            th.setFormatter(formatter)
            self.__logger.addHandler(th)

    def get_logger(self):
        return self.__logger
