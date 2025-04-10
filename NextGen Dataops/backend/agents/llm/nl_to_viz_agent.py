
        Example Request 4: "Can you plot profit?" (Ambiguous)
        Example Output 4:
        {{
          "plot_type": null,
          "x_col": null,
          "y_col": null,
          "color_col": null,
          "size_col": null,
          "aggregation": null,
          "error": "Ambiguous request: Please specify the type of plot and any other relevant columns (e.g., 'histogram of profit', 'profit over time')."
        }}
        """
        # --- Retry Logic Prompting ---
        if previous_params_str and error_feedback:
            logger.debug("Constructing NL-to-Viz retry prompt with error feedback.") # Replaced print
            system_prompt_header = "You are an expert data visualization assistant. Your previous attempt to generate plot parameters resulted in an error or invalid output. Please analyze the feedback and provide corrected parameters."
            user_message_content = f"""
            Original Natural Language Request: {nl_request.strip()}

            DataFrame Schema Used:
            {schema_str}


            Your previously generated JSON parameters (which were invalid):
            ```json
            {previous_params_str}
            ```

            Error/Validation Feedback:
            {error_feedback}

            Please carefully review the schema, original request, previous attempt, and the error feedback. Generate a corrected, valid JSON object containing appropriate plot parameters based only on the schema and the user's original request. Ensure the plot_type is supported ({supported_types_str}) and all specified column names (x_col, y_col, etc.) exist exactly as shown in the schema. If the request truly cannot be fulfilled based on the schema, set the "error" field in the JSON.
            Respond ONLY with the corrected JSON object.
            """

        else: # Standard initial prompt
            user_message_content = f"Natural Language Request: {nl_request.strip()}\n\nPlease generate the plot parameters JSON based on the schema and instructions."

        # --- End Retry Logic ---

        system_prompt = f"{system_prompt_header}\n\n{schema_section}\n\n{instructions_header}\n{instructions_body}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message_content.strip()},
        ]
        logger.debug(f"NL-to-Viz Prompt Messages (Retry: {bool(previous_params_str)}): User msg start: {user_message_content[:100]}...")
        return messages

    def _parse_and_validate_json(self, raw_json_str: str, schema_dict: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Parses and validates the JSON string from LLM, handling potential trailing text.
        Returns (params_dict | None, error_message | None)
        """
        if not raw_json_str:
            return None, "LLM returned an empty response."

        logger.debug(f"Raw JSON from LLM (Viz): '{raw_json_str}'")
        text_to_parse = raw_json_str.strip()

        # Find the first opening brace '{'
        start_index = text_to_parse.find('{')
        if start_index == -1:
            logger.warning("Could not find starting '{' in LLM response.")
            return None, "LLM response does not contain a JSON object structure."

        # Find the matching closing brace '}' by tracking brace count
        brace_level = 0
        end_index = -1
        for i, char in enumerate(text_to_parse):
            if i < start_index: # Skip characters before the first '{'
                continue
            if char == '{':
                brace_level += 1
            elif char == '}':
                brace_level -= 1
                if brace_level == 0:
                    # Found the matching closing brace for the initial opening brace
                    end_index = i + 1 # Include the closing brace
                    break # Stop searching

        if end_index == -1:
            logger.warning("Could not find matching '}' for the JSON object in LLM response.")
            return None, "LLM response contains incomplete JSON object structure."

        # Extract the potential JSON block
        potential_json = text_to_parse[start_index:end_index]
        logger.debug(f"Extracted potential JSON block: '{potential_json}'")

        try:
            # Attempt to parse ONLY the extracted block
            params = json.loads(potential_json)
            if not isinstance(params, dict):
                # Should not happen if braces matched, but check anyway
                raise json.JSONDecodeError("Parsed result is not a dictionary.", potential_json, 0)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode extracted JSON block: {e}. Block: '{potential_json}'")
            # Return specific error including the block we tried to parse