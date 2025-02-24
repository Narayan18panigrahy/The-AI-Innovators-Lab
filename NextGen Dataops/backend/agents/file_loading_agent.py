# backend/agents/file_loading_agent.py

import pandas as pd
import io
import os # Needed for os.path.exists if checking path type
# import traceback # No longer needed with logger.error(exc_info=True)
import logging # Import logging
from pathlib import Path # For type hinting and checking path
from typing import Union

# Get a logger specific to this module
logger = logging.getLogger(__name__)

class FileLoadingAgent:
    """
    Agent responsible for loading data from uploaded files (CSV, Excel).
    Handles file paths passed from the backend API handler.
    """

    def __init__(self):
        """Initializes the FileLoadingAgent."""
        logger.debug("FileLoadingAgent initialized.")
        pass # No specific state needed currently

    def load_data(self, file_input: Union[str, Path, io.BytesIO, io.StringIO]) -> Union[pd.DataFrame, None]:
        """
        Loads data from a file path or buffer into a Pandas DataFrame.

        Args:
            file_input: A file path (string or Path object) or a file-like
                        object (BytesIO, StringIO).

        Returns:
            A pandas DataFrame if successful, None otherwise.
        """
        file_name_for_log = "Unknown File"
        file_extension = ""

        # Determine input type and extract filename/extension
        if isinstance(file_input, (str, Path)):
            file_path = Path(file_input)
            if not file_path.is_file():
                 logger.error(f"File not found at path: {file_path}")
                 return None
            file_name_for_log = file_path.name
            file_extension = file_path.suffix.lower().strip('.')
            logger.debug(f"Loading from path: {file_path}")
        elif hasattr(file_input, 'read') and hasattr(file_input, 'seek'): # Check if it's a file-like object
             # Try to get a name if available (e.g., from UploadedFile)
             file_name_for_log = getattr(file_input, 'name', 'Uploaded Buffer')
             # Infer extension from name if possible
             if '.' in file_name_for_log:
                 file_extension = file_name_for_log.rsplit('.', 1)[-1].lower()
             else:
                 # Cannot reliably determine extension from buffer without name
                 # We might need to rely on content sniffing or explicit type later
                 logger.warning(f"Cannot determine file extension from buffer named '{file_name_for_log}'. Will attempt CSV/Excel.")
                 # Default to trying CSV first, then Excel if needed
                 file_extension = 'csv' # Or make it None and handle below
             logger.debug(f"Loading from buffer: {file_name_for_log}")
             # Ensure buffer is at the start
             file_input.seek(0)
        else:
             logger.error(f"Invalid file input type: {type(file_input)}")
             return None


        df = None

        try:
            logger.info(f"Attempting to load '{file_name_for_log}' (extension: '{file_extension}')...")

            if file_extension == 'csv':
                try:
                    # Pass the path or buffer directly
                    df = pd.read_csv(file_input)
                    logger.debug(f"CSV '{file_name_for_log}' loaded successfully with default UTF-8.")
                except UnicodeDecodeError:
                    logger.warning(f"UTF-8 decoding failed for '{file_name_for_log}', trying 'latin1' encoding...")
                    # If it's a buffer, we need seek(0) before retrying
                    if hasattr(file_input, 'seek'):
                        file_input.seek(0)
                    try:
                        df = pd.read_csv(file_input, encoding='latin1')
                        logger.debug(f"CSV '{file_name_for_log}' loaded successfully with 'latin1'.")
                    except Exception as e_latin1:
                         logger.error(f"Failed reading CSV '{file_name_for_log}' with latin1. Error: {e_latin1}", exc_info=True)
                         return None
                except Exception as e_csv:
                    logger.error(f"Failed to parse CSV '{file_name_for_log}'. Error: {e_csv}", exc_info=True)
                    return None

            elif file_extension in ['xlsx', 'xls']:
                try:
                    # pd.ExcelFile and pd.read_excel work with both paths and buffers
                    # Ensure buffer is at the start if it's a buffer
                    if hasattr(file_input, 'seek'):
                        file_input.seek(0)
                    xls = pd.ExcelFile(file_input)
                    sheet_names = xls.sheet_names