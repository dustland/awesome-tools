from loguru import logger
import sys
import os

# Configure logger
log_level = os.getenv("LOG_LEVEL", "INFO")
log_file = os.getenv("LOG_FILE", "awesome-embodied-ai.log")

# Remove default handler and add our custom handlers
logger.remove()
logger.add(sys.stderr, level=log_level)
logger.add(log_file, rotation="10 MB", level=log_level)

__all__ = ["logger"] 