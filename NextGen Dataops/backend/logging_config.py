import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FILENAME = 'backend_app.log'
LOG_DIR = os.path.dirname(__file__) # Place log file in the backend directory
LOG_FILEPATH = os.path.join(LOG_DIR, LOG_FILENAME)

def setup_logging(log_level_str='INFO'):
    """Configures centralized logging for the application."""

    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Define the format for log messages, including filename and line number
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- File Handler ---
    # Rotates logs, keeping 5 backups of 5MB each
    file_handler = RotatingFileHandler(
        LOG_FILEPATH,
        maxBytes=5*1024*1024, # 5 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    # Set file handler to log DEBUG level messages and above
    file_handler.setLevel(logging.DEBUG)

    # --- Console Handler ---
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    # Set console handler based on the function argument or default
    console_handler.setLevel(log_level)

    # --- Root Logger Configuration ---
    # Get the root logger
    root_logger = logging.getLogger()
    # Set the root logger level to the lowest level you want to capture (DEBUG)
    # Handlers will then filter based on their own levels
    root_logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates if setup is called multiple times
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Add the handlers to the root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Use the root logger for this initial message, as specific loggers might not exist yet
    root_logger.info(f"Logging configured. Level: {log_level_str}. Output file: {LOG_FILEPATH}")

# Example of how to get a logger in other modules:
# import logging
# logger = logging.getLogger(__name__) # Using __name__ helps identify the module in logs
# logger.info("This is an info message.")
# logger.debug("This is a debug message.")