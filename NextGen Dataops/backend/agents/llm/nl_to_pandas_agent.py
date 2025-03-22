                - str | None: The cleaned code string if valid, otherwise None.
                - str | None: An error message string if validation fails, otherwise None.
        """
        if not raw_code:
            return None, "LLM returned an empty response."

        logger.debug(f"Raw Python code from LLM: '{raw_code}'")
        # Basic cleaning: remove potential markdown fences and leading/trailing whitespace
        clean_code = raw_code.strip()
        # Regex to find code block, handling optional 'python' language identifier
        match = re.match(r"^\s*```(?:python)?\s*(.*?)\s*```\s*$", clean_code, re.IGNORECASE | re.DOTALL)
        if match:
             clean_code = match.group(1).strip()
        else:
             # Fallback cleaning if regex fails (e.g., missing closing ```)
             if clean_code.lower().startswith("```python"): clean_code = clean_code[9:].strip()
             elif clean_code.startswith("```"): clean_code = clean_code[3:].strip()
             if clean_code.endswith("```"): clean_code = clean_code[:-3].strip()

        logger.debug(f"Cleaned Python code attempt: '{clean_code}'")

        # --- Basic Validation ---
        if not clean_code:
            return None, "LLM response was empty after cleaning formatting."

        # Check if it assigns to the 'result' variable (essential for extraction)
        # Use regex for more robust check allowing whitespace around '='
        if not re.search(r"\bresult\s*=", clean_code):
            # If no 'result =', try to wrap the last line if it looks like an expression
            lines = clean_code.strip().split('\n')
            last_line = lines[-1].strip()
            if last_line and not last_line.startswith(('result =', 'result=', 'print(', '#', 'import ')):
                 logger.warning("LLM code didn't assign to 'result'. Wrapping last line with 'result = ...'.")
                 lines[-1] = f"result = {last_line}"
                 clean_code = "\n".join(lines)
                 # Recheck if result assignment is now present
                 if not re.search(r"\bresult\s*=", clean_code):
                      return None, "Generated code does not assign to the required 'result' variable, even after attempting to wrap the last line."
            else:
                 return None, "Generated code does not assign to the required 'result' variable."

        # Check for disallowed imports (basic check)
        if 'import ' in clean_code:
            return None, "Generated code contains disallowed 'import' statements."

        # (Optional) More advanced validation using ast.parse
        try:
            import ast
            ast.parse(clean_code)
            logger.debug("Code passed basic AST syntax check.")
        except SyntaxError as e:
            logger.error(f"Generated code has a Python syntax error according to AST: {e}")
            return None, f"Generated code has a Python syntax error: {e}"
        except Exception as e:
             logger.warning(f"AST parsing failed with unexpected error: {e}") # Less critical, might proceed

        logger.debug(f"Validated Python code: '{clean_code}'")
        return clean_code, None

    def generate_pandas_query(self, nl_question: str, df_schema_str: str, llm_config: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Generates Pandas query code by calling the centralized LLM client.

        Args:
            nl_question: The natural language question.
            df_schema_str: String representation of the DataFrame schema.
            llm_config: Dictionary containing provider, model, credentials.

        Returns:
             A tuple containing:
                - str | None: The generated code string if successful, otherwise None.
                - str | None: An error message string if an error occurred, otherwise None.
        """
        logger.info(f"Generating Pandas code for question: '{nl_question}'")
        if execute_llm_completion is None:
            logger.error("LLM client function not available for NLtoPandasAgent.")
            return None, "LLM client function not available."
        if not nl_question or not df_schema_str or not llm_config:
            logger.error("Missing input question, schema, or LLM configuration for code generation.")
            return None, "Missing input question, schema, or LLM configuration for code generation."

        messages = self._construct_prompt(nl_question, df_schema_str)
        temperature = 0.1 # Low temperature for predictable code
        max_tokens = 300  # Code snippets should generally be short

        # Call the centralized LLM execution function
        raw_code, error = execute_llm_completion(
            llm_config=llm_config,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Handle the response from the client function
        if error:
            # Error already logged by llm_client, just return it
            logger.error(f"LLM client error during Pandas code generation: {error}")
            return None, error
        elif raw_code:
            # Parse and validate the raw code content received