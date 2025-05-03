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