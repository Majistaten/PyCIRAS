import logging
import time

from functools import wraps

from utility import util


def timed(func):
    """This decorator is used to measure the execution time of a function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()

        logging.info(f"{func.__name__} had the execution time: {util.format_duration(end - start)}")
        return result

    return wrapper
