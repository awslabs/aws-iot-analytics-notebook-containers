
import logging

from logging.handlers import RotatingFileHandler

from iota_notebook_containers.constants import MAX_LOG_BYTES

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_PATH = "/var/log/iota_notebook_containers.log"

def create_logger(module):
	logger = logging.getLogger(module)
	logger.setLevel(logging.INFO)
	handler = RotatingFileHandler(LOG_PATH, maxBytes=MAX_LOG_BYTES, backupCount=5)
	handler.setFormatter(logging.Formatter(LOG_FORMAT))
	logger.addHandler(handler)
	return logger