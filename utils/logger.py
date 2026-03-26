import sys
import os
from loguru import logger


def setup_logger():
    logger.remove()
    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    )
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.add(sys.stdout, format=fmt, level=log_level, colorize=True)
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/alphasignal_{time:YYYY-MM-DD}.log",
        rotation="1 day", retention="30 days",
        format=fmt, level="DEBUG", enqueue=True
    )
    return logger


log = setup_logger()
