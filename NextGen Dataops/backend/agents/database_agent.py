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