import time
from functools import wraps
from src.telemetry.logger import logger

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    """
    A sophisticated retry decorator with exponential backoff.
    Ideal for handling rate limits, server errors, and network timeouts.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt > retries:
                        logger.error(f"Function {func.__name__} failed after {retries} retries. Final Error: {e}")
                        raise
                    sleep_time = backoff_in_seconds * (2 ** (attempt - 1))
                    logger.info(f"Error '{e}' in {func.__name__}. Retrying in {sleep_time}s (Attempt {attempt}/{retries})...")
                    time.sleep(sleep_time)
        return wrapper
    return decorator
