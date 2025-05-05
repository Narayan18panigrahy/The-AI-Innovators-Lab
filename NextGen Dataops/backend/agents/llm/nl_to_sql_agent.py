        # Check for SELECT keyword more robustly
        if not clean_sql.upper().lstrip().startswith("SELECT"):
            select_pos = clean_sql.upper().find("SELECT ") # Look for SELECT followed by space
            if select_pos != -1:
                logger.warning("LLM included text before SQL. Extracting SELECT.")
                clean_sql = clean_sql[select_pos:].strip().strip(';')
            else: return None, f"LLM response does not appear to be a valid SELECT query. Response: '{raw_sql[:200]}...'"

        # Optional: Basic check for disallowed keywords (can be improved)
        disallowed = ['UPDATE ', 'DELETE ', 'INSERT ', 'DROP ', 'TRUNCATE ', 'ALTER ', 'CREATE ']
        if any(keyword in clean_sql.upper() for keyword in disallowed):
            logger.warning(f"Generated SQL may contain disallowed keywords: '{clean_sql[:200]}...'")
            return None, "Generated query contains potentially disallowed keywords (non-SELECT)."

        logger.debug(f"Validated SQL: '{clean_sql}'")
        return clean_sql, None

    def generate_sql_query(self, nl_question: str, schema_str: str, llm_config: dict,
                        previous_query: Optional[str] = None, db_error: Optional[str] = None
                        ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generates SQL query using LLM, tailored for PostgreSQL, with optional retry info.

        Args:
            nl_question: The natural language question.
            schema_str: String representation of the database schema.
            llm_config: Dictionary containing provider, model, credentials.
            previous_query: The previous failed SQL query (for retries).
            db_error: The database error message from the failed query (for retries).

        Returns:
            (generated_sql_string | None, error_message | None) tuple.
        """
        is_retry = bool(previous_query)
        logger.info(f"Generating SQL query (Retry: {is_retry}). Question: '{nl_question[:100]}...'")

        if execute_llm_completion is None:
            logger.error("LLM client function not available for NLtoSQLAgent.")
            return None, "LLM client function not available."
        if not nl_question or not schema_str or not llm_config:
            logger.error("Missing input(s) for SQL generation.")
            return None, "Missing input(s) for SQL generation."

        # Construct prompt (handles retry logic internally)
        messages = self._construct_prompt(nl_question, schema_str, previous_query, db_error)

        # Adjust parameters slightly? Maybe slightly higher temp for retry?
        temperature = 0.1 if not is_retry else 0.15
        max_tokens = 700 # Allow more tokens for potentially complex queries/retries

        # Call the centralized LLM execution function
        raw_sql, error = execute_llm_completion(
            llm_config=llm_config,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Handle response
        if error:
            logger.error(f"LLM client error during SQL generation: {error}")
            return None, error # Return the error from the client
        elif raw_sql:
            validated_sql, validation_error = self._parse_and_validate_sql(raw_sql)
            if validation_error:
                logger.error(f"Generated SQL failed validation: {validation_error}. Raw SQL: '{raw_sql[:200]}...'")
                return None, validation_error # Return parsing/validation error
            else:
                logger.info(f"SQL generated successfully (Retry: {is_retry}).")
                return validated_sql, None # Success
        else:
            # LLM client returned None content but no error string
            logger.warning("LLM client returned empty SQL content without specific error.")
            return None, "LLM client returned empty content."