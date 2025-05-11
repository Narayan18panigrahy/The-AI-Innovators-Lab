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
        # Handle specific date type if pandas uses it
        if pd_type_lower == "date": return "DATE"
        if "bool" in pd_type_lower: return "BOOLEAN"
        if "object" in pd_type_lower or "string" in pd_type_lower: return "TEXT"
        if "category" in pd_type_lower: return "TEXT"
        logger.warning(f"Unmapped pandas dtype '{pd_type_str}', defaulting to TEXT.")
        return "TEXT"

    def create_table_from_df(self, df: pd.DataFrame, table_name: str, schema_name: str = DB_DEFAULT_SCHEMA_NAME) -> tuple[Optional[str], Optional[dict]]:
        """
        Creates a PostgreSQL table from a Pandas DataFrame, sanitizing names and loading data.

        Args:
            df: The Pandas DataFrame to load.
            table_name: The desired base name for the table.
            schema_name: The database schema to use.

        Returns:
            (fully_qualified_table_name, schema_dict_for_llm) or (None, None) on failure.
        """
        if df is None or df.empty:
            logger.error("Cannot create table: Input DataFrame is None or empty.")
            return None, None

        sanitized_table = self._sanitize_name(table_name, is_table_name=True)
        sanitized_schema = self._sanitize_name(schema_name)
        fully_qualified_table_name = f"{sanitized_schema}.{sanitized_table}"
        table_identifier = sql.Identifier(sanitized_schema, sanitized_table)

        logger.info(f"Preparing to create/replace table '{fully_qualified_table_name}' from DataFrame.")

        columns_defs = []
        df_schema_for_llm = {'table_name': fully_qualified_table_name, 'columns': {}}
        renamed_columns_map = {}
        final_column_names_for_df = []
        seen_sanitized_names = set()

        for col in df.columns:
            original_col_name = str(col) # Ensure column name is string
            sanitized_col = self._sanitize_name(original_col_name)
            # Handle potential duplicate sanitized column names robustly
            final_sanitized_col = sanitized_col
            count = 1
            while final_sanitized_col in seen_sanitized_names:
                suffix = f"_{count}"
                max_base_len = 63 - len(suffix)
                final_sanitized_col = f"{sanitized_col[:max_base_len]}{suffix}"
                count += 1
            seen_sanitized_names.add(final_sanitized_col)

            if final_sanitized_col != original_col_name: # Log only if renamed
                logger.debug(f"Sanitizing column '{original_col_name}' to '{final_sanitized_col}'")

            final_column_names_for_df.append(final_sanitized_col)
            renamed_columns_map[original_col_name] = final_sanitized_col

            sql_type = self._map_pandas_dtype_to_sql(str(df[original_col_name].dtype))
            # Use sql.Identifier for column names in CREATE TABLE statement
            columns_defs.append(sql.SQL("{} {}").format(sql.Identifier(final_sanitized_col), sql.SQL(sql_type)))
            # Store schema info for LLM using the final sanitized name
            df_schema_for_llm['columns'][final_sanitized_col] = {'original_name': sanitized_col, 'sql_type': sql_type}
            logger.debug(f"Column '{original_col_name}' mapped to '{final_sanitized_col}' with type '{sql_type}'")

        # Create a copy WITH the new column names for loading
        df_copy = df.copy()
        df_copy.columns = final_column_names_for_df

        # --- Prepare SQL Statements ---
        create_table_sql = sql.SQL("CREATE TABLE {} ({})").format(
            table_identifier,
            sql.SQL(', ').join(columns_defs)
        )
        drop_table_sql = sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(table_identifier)
        create_schema_sql = sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(sanitized_schema))
        cols_sql_identifiers = sql.SQL(', ').join(map(sql.Identifier, final_column_names_for_df))
        # Use E'\t' for tab delimiter, \\N for NULL
        copy_sql_template = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N')").format(
             table_identifier,
             cols_sql_identifiers
        )

        # --- Execute Transaction ---
        conn = None
        try:
            conn = self.get_connection()
            if not conn: return None, None
            conn.autocommit = False # Ensure transaction control
            with conn.cursor() as cur:
                logger.debug(f"Ensuring schema '{sanitized_schema}' exists...")
                cur.execute(create_schema_sql)

                logger.debug(f"Dropping table if exists: {fully_qualified_table_name}")
                cur.execute(drop_table_sql)

                logger.debug(f"Creating table: {fully_qualified_table_name}")
                logger.debug(f"Create Table SQL: {create_table_sql.as_string(cur)}")
                cur.execute(create_table_sql)

                # Load data using copy_expert
                logger.debug(f"Preparing data buffer for COPY into {fully_qualified_table_name}...")
                sio = io.StringIO()
                # Handle potential quoting issues and delimiters in data itself
                # Using QUOTE_NONE (3) might be risky if data contains the delimiter. Tab is usually safer.
                df_copy.to_csv(sio, index=False, header=False, sep='\t', na_rep='\\N', quoting=csv.QUOTE_MINIMAL)
                sio.seek(0)

                logger.debug(f"Executing COPY command...")
                logger.debug(f"Copy SQL: {copy_sql_template.as_string(cur)}")
                cur.copy_expert(copy_sql_template, sio)
                rows_copied = cur.rowcount # Get number of rows copied
                logger.info(f"Data loaded via COPY successfully. Rows affected: {rows_copied}")

                conn.commit() # Commit the transaction
            logger.info(f"Table '{fully_qualified_table_name}' created and loaded successfully.")
            return fully_qualified_table_name, df_schema_for_llm

        except psycopg2.Error as e:
            if conn: conn.rollback() # Rollback on error
            logger.error(f"PostgreSQL Error during table setup for '{fully_qualified_table_name}': {e}", exc_info=True)
            return None, None
        except Exception as e:
            if conn: conn.rollback()
            logger.error(f"Unexpected error during table setup for '{fully_qualified_table_name}': {e}", exc_info=True)
            return None, None
        finally:
            if conn: conn.close()

    def execute_query(self, sql_query: str, params: Optional[tuple] = None) -> tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Executes a given SQL SELECT query against the PostgreSQL database.

        Args:
            sql_query: The SQL query string.
            params: Optional parameters for query execution.

        Returns:
            (result_dataframe, error_message_string | None) tuple.
        """
        conn = None
        try:
            conn = self.get_connection()
            if not conn: return None, "Failed to connect to database for query execution."

            logger.debug(f"Executing SQL (PostgreSQL): {sql_query[:500]}... with params: {params}")
            # Using pandas for convenience, it handles fetching and column names
            results_df = pd.read_sql_query(sql_query, conn, params=params)
            logger.info(f"SQL query executed successfully, {len(results_df)} rows returned.")
            return results_df, None

        except psycopg2.Error as e:
            # Provide detailed PG error if available
            error_detail = f"{e.pgcode} - {e.pgerror}" if hasattr(e, 'pgcode') and e.pgcode else str(e)
            error_msg = f"PostgreSQL Execution Error: {error_detail}"
            logger.error(f"{error_msg} | Query: {sql_query[:500]}...", exc_info=False) # Log less verbose traceback for common exec errors
            return None, error_detail # Return detailed error string for LLM feedback
        except Exception as e:
            error_msg = f"Unexpected error during SQL query execution: {e}"
            logger.error(error_msg, exc_info=True)
            return None, str(e)
        finally:
            if conn: conn.close()

    def get_table_schema_for_llm(self, table_name: str, schema_name: str = DB_DEFAULT_SCHEMA_NAME) -> str:
        """
        Retrieves table schema from information_schema, formatted for an LLM prompt.
        """
        # Ensure table/schema names passed here are the *sanitized* ones used in DB
        # No need to re-sanitize if called with names from session state
        fully_qualified_table_name = f"{schema_name}.{table_name}"
        logger.debug(f"Fetching schema for LLM: {fully_qualified_table_name}")

        query = sql.SQL("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position;
        """)
        conn = None
        try:
            conn = self.get_connection()
            if not conn: return "Error: Could not connect to database."
            with conn.cursor() as cur:
                cur.execute(query, (schema_name, table_name))
                columns_info = cur.fetchall()

            if not columns_info:
                logger.warning(f"No columns found for table '{fully_qualified_table_name}' in information_schema.")
                return f"Error: Table '{fully_qualified_table_name}' not found or has no columns."

            # Format for LLM prompt (similar to standard SQL CREATE TABLE but simplified)
            schema_str = f"Table: {fully_qualified_table_name}\nColumns:\n"
            for col_name, dtype, nullable, default in columns_info:
                # Use sql.Identifier to handle potentially problematic column names correctly
                col_identifier_str = sql.Identifier(col_name).as_string(conn) # Use connection context if available
                nullable_info = " (NULLABLE)" if nullable.upper() == 'YES' else ""
                default_info = f" (DEFAULT {default})" if default else ""
                # Simplify data type for LLM (e.g., CHARACTER VARYING(255) -> CHARACTER VARYING)
                simple_dtype = dtype.split('(')[0].upper()
                schema_str += f"  - {col_identifier_str}: {simple_dtype}{nullable_info}{default_info}\n"
            logger.debug(f"Schema string generated for {fully_qualified_table_name}")
            return schema_str.strip()

        except psycopg2.Error as e:
            error_detail = f"{e.pgcode} - {e.pgerror}" if hasattr(e, 'pgcode') else str(e)
            logger.error(f"PostgreSQL Error fetching schema for '{fully_qualified_table_name}': {error_detail}", exc_info=True)
            return f"Error fetching schema: {error_detail}"
        except Exception as e:
            logger.error(f"Unexpected error fetching schema for '{fully_qualified_table_name}': {e}", exc_info=True)
            return f"Error fetching schema: {str(e)}"
        finally:
            if conn: conn.close()

    def get_dataframe_from_table(self, table_name_with_schema: str) -> Optional[pd.DataFrame]:
        """
        Fetches the entire content of a specified table (with schema) as a Pandas DataFrame.
        """
        if not table_name_with_schema:
            logger.error("get_dataframe_from_table: No table name provided.")
            return None

        conn = None
        try:
            conn = self.get_connection()
            if conn is None:
                return None # Error already logged

            # Assuming table_name_with_schema is like "schema.table" or "table"
            # For production, ensure robust quoting or use psycopg2.sql.Identifier
            sql_query = f"SELECT * FROM {table_name_with_schema};"

            logger.debug(f"Executing query to fetch DataFrame: {sql_query}")
            df = pd.read_sql_query(sql_query, conn)
            logger.info(f"Successfully fetched {len(df)} rows from table '{table_name_with_schema}'.")
            return df
        except Exception as e:
            logger.error(f"Error fetching DataFrame from table '{table_name_with_schema}': {e}", exc_info=True)
            return None
        finally:
            if conn:
                conn.close()