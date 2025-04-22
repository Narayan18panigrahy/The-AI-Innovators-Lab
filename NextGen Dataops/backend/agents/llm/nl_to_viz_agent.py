            return None, f"LLM response contained invalid JSON structure: {e}. Tried to parse: '{potential_json[:100]}...'"


        # --- Validation ---
        if params.get("error"):
            logger.warning(f"LLM indicated an error in parameters: {params['error']}")
            return None, f"LLM indicated an error: {params['error']}" # Treat LLM error as validation failure

        plot_type = params.get("plot_type")
        if not plot_type: return None, "LLM response missing required 'plot_type'."
        if plot_type not in self.SUPPORTED_PLOT_TYPES: return None, f"Unsupported plot type '{plot_type}'. Supported: {', '.join(self.SUPPORTED_PLOT_TYPES)}."

        valid_columns = list(schema_dict.get("columns", {}).keys()) if schema_dict and isinstance(schema_dict.get("columns"), dict) else []
        if not valid_columns: return None, "Schema dictionary missing/invalid for column validation."
        cols_to_check = ["x_col", "y_col", "color_col", "size_col"]
        for col_key in cols_to_check:
            col_name = params.get(col_key)
            if col_name is not None and col_name not in valid_columns: return None, f"Invalid column '{col_name}' for '{col_key}'. Valid: {', '.join(valid_columns)}."

        x_col = params.get("x_col"); y_col = params.get("y_col"); aggregation = params.get("aggregation")
        if plot_type == 'histogram' and not x_col: return None, "Histogram requires 'x_col'."
        if plot_type in ['scatter', 'line'] and (not x_col or not y_col): return None, f"{plot_type.capitalize()} typically requires 'x_col' and 'y_col'."
        if plot_type == 'bar' and not x_col: return None, "Bar plot requires 'x_col'."
        if plot_type == 'box' and not x_col: return None, "Box plot typically requires 'x_col'."
        if aggregation and not y_col and aggregation != 'count': return None, f"Aggregation '{aggregation}' typically requires 'y_col' (unless 'count')."

        logger.debug(f"Validated plot parameters: {params}")
        return params, None # Success

    def generate_viz_params(self, nl_request: str, schema_str: str, llm_config: Dict, schema_dict: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Generates visualization parameters using LLM, with retry logic.

        Args:
            nl_request: The natural language request for visualization.
            schema_str: String representation of the DataFrame schema.
            llm_config: Dictionary containing provider, model, credentials.
            schema_dict: Dictionary representation of schema for validation.

        Returns:
            (params_dict | None, error_message | None) tuple.
        """
        logger.debug(f"Generating viz params for request: '{nl_request[:100]}...'")
        if execute_llm_completion is None: return None, "LLM client function not available."
        if not all([nl_request, schema_str, llm_config, schema_dict]): return None, "Missing input(s)."

        last_error = None; last_attempt_json = None

        for attempt in range(self.MAX_RETRIES + 1):
            is_retry = attempt > 0; logger.info(f"Viz Params Attempt #{attempt + 1} (Retry: {is_retry})")
            messages = self._construct_prompt(nl_request, schema_str, last_attempt_json, last_error)
            logger.debug(f"Prompt messages: {messages}") # Replaced print
            temperature = 0.2 if not is_retry else 0.3; max_tokens = 300

            raw_json_str, llm_error = execute_llm_completion(
                llm_config=llm_config, messages=messages, temperature=temperature, max_tokens=max_tokens
            )
            logger.debug(f"Raw JSON response nl to viz: {raw_json_str}") # Replaced print

            if llm_error: logger.error(f"LLM client error to viz attempt {attempt+1}: {llm_error}"); last_error = llm_error; last_attempt_json = None;
            elif raw_json_str:
                # Call the validation function
                validated_params, validation_error = self._parse_and_validate_json(raw_json_str, schema_dict)
                if validation_error: logger.warning(f"Validation failed attempt {attempt+1}: {validation_error}. Raw: '{raw_json_str[:200]}...'"); last_error = validation_error; last_attempt_json = raw_json_str;
                else: logger.info("Plot parameters validated successfully."); return validated_params, None # SUCCESS
            else: logger.warning(f"LLM returned empty content attempt {attempt+1}."); last_error = "LLM empty content."; last_attempt_json = None;

            if attempt >= self.MAX_RETRIES: break # Exit loop after last retry

        logger.error(f"Failed viz params after {self.MAX_RETRIES + 1} attempts. Last error: {last_error}")
        return None, f"Failed after retries. Last error: {last_error or 'Unknown failure.'}"