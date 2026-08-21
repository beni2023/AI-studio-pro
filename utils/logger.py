"""
Centralized Logging System
جایگزین print() - با levels و formatting
"""
import logging
import sys
from functools import wraps

# Configure logger
logger = logging.getLogger('ai_studio')
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Decorator for logging function calls
def log_call(func):
    """Decorator to log function entry/exit"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Completed {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise
    return wrapper

# Convenience methods
def log_info(msg):
    logger.info(msg)

def log_error(msg, exc_info=False):
    logger.error(msg, exc_info=exc_info)

def log_warning(msg):
    logger.warning(msg)

def log_debug(msg):
    logger.debug(msg)