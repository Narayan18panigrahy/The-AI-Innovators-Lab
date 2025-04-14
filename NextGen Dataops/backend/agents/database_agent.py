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