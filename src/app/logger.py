import logging
from src.config.settings import LOG_FILE

def setup_logger(name=__name__, level=logging.INFO):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.FileHandler(LOG_FILE)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger
