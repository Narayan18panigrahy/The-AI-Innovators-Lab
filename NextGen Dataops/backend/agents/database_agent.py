# backend/agents/database_agent.py

import psycopg2
from psycopg2 import sql # For safe SQL query construction
from psycopg2.extras import execute_values # For potential bulk inserts later (not used in current copy_expert)
import pandas as pd
import logging # Import logging
import re
import io # For using StringIO with copy_expert
# import traceback # No longer needed if using logger.error(exc_info=True)
from typing import List, Dict, Tuple, Any, Optional
import csv # For CSV handling in copy_expert

# Import constants for DB config
from constants import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_DEFAULT_SCHEMA_NAME

# Get a logger specific to this module
logger = logging.getLogger(__name__)

class DatabaseAgent:
    """
    Agent responsible for interacting with the PostgreSQL database.
    Manages connections, data loading, query execution, and schema retrieval.
    """

    def __init__(self):
        """Initializes the DatabaseAgent with connection parameters."""
        self.db_config = {
            "host": DB_HOST,
            "port": DB_PORT,
            "dbname": DB_NAME,
            "user": DB_USER,
            "password": DB_PASSWORD
        }
        self._test_connection() # Test connection on initialization

    def _test_connection(self):
        """Attempts a connection to verify credentials and reachability."""
        conn = None
        try:
            conn = self.get_connection()
            if conn:
                logger.info(f"Successfully tested connection to PostgreSQL database '{DB_NAME}' on {DB_HOST}:{DB_PORT}.")
            else:
                # Error logged by get_connection
                pass
        except Exception as e:
             # Error logged by get_connection
             pass # Avoid redundant logging
        finally:
            if conn: conn.close()

    def get_connection(self):
        """Establishes and returns a new connection to the PostgreSQL database."""
        try:
            conn = psycopg2.connect(**self.db_config)
            logger.debug("PostgreSQL connection established.")
            return conn
        except psycopg2.OperationalError as e:
            logger.error(f"PostgreSQL Connection Error: Unable to connect. Check credentials, host ({DB_HOST}:{DB_PORT}), database ('{DB_NAME}'), and server status. Error: {e}", exc_info=False) # Don't need full traceback for common connection errors
            return None
        except Exception as e:
            logger.error(f"PostgreSQL Connection Error: An unexpected error occurred. {e}", exc_info=True)
            return None

    def _sanitize_name(self, name: str, is_table_name=False) -> str:
        """
        Sanitizes a name for PostgreSQL (lowercase, underscores, no leading numbers, max length).
        """
        if not isinstance(name, str): name = str(name)
        # Replace non-alphanumeric characters (allowing underscores) with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]+', '_', name)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Prepend underscore if starts with a digit
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        # Convert to lowercase
        sanitized = sanitized.lower()
        # Handle empty names
        if not sanitized:
            sanitized = "unnamed_table" if is_table_name else "unnamed_column"
        # Truncate to PostgreSQL's default identifier limit (usually 63)
        max_len = 63
        if len(sanitized) > max_len:
             logger.warning(f"Identifier '{sanitized}' truncated to {max_len} characters.")
             sanitized = sanitized[:max_len]
        return sanitized

    def _map_pandas_dtype_to_sql(self, pd_type_str: str) -> str:
        """Maps pandas dtype string to a suitable PostgreSQL data type string."""
        pd_type_lower = pd_type_str.lower()
        if "int64" in pd_type_lower: return "BIGINT"
        if "int32" in pd_type_lower: return "INTEGER"
        if "int16" in pd_type_lower: return "SMALLINT"
        if pd_type_lower.startswith("int"): return "INTEGER"
        if "float64" in pd_type_lower: return "DOUBLE PRECISION"
        if "float32" in pd_type_lower: return "REAL"
        if pd_type_lower.startswith("float"): return "REAL"
        if "datetime64[ns" in pd_type_lower or "timestamp" in pd_type_lower: return "TIMESTAMP WITHOUT TIME ZONE"