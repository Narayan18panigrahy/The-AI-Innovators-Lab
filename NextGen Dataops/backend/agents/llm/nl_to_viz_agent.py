# backend/agents/llm/nl_to_viz_agent.py

# import traceback # Removed
import json
import re
import logging # Import logging
from typing import List, Dict, Tuple, Optional, Any

# Import the centralized client function
try:
    from agents.llm.llm_client import execute_llm_completion
except ImportError:
    # Log this critical error
    logging.critical("CRITICAL ERROR: Could not import llm_client.py in NLtoVizAgent. LLM functionality will be disabled.")
    execute_llm_completion = None # Define as None to allow class definition

# Get a logger specific to this module
logger = logging.getLogger(__name__)

class NLtoVizAgent:
    """
    Agent that uses an LLM to interpret natural language visualization requests
    and output structured parameters for plotting. Includes retry logic for errors.
    """
    SUPPORTED_PLOT_TYPES = [
        'scatter', 'histogram', 'bar', 'line', 'box', 'heatmap'
    ]
    MAX_RETRIES = 1 # Max retries on parameter generation failure

    def __init__(self):
        """Initializes the NLtoVizAgent."""
        logger.debug("NLtoVizAgent initialized.")
        pass # Keep pass as __init__ doesn't do anything else now

    def _construct_prompt(self, nl_request: str, schema_str: str,
                          previous_params_str: Optional[str] = None,
                          error_feedback: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Constructs the prompt messages for the LLM to extract plot parameters.
        Includes optional fields for retry attempts with error feedback.
        """
        supported_types_str = ", ".join(self.SUPPORTED_PLOT_TYPES)
        system_prompt_header = "You are an expert data visualization assistant. Your task is to interpret a natural language request for a plot and extract the necessary parameters into a structured JSON object."

        schema_section = f"DataFrame Schema (`df`):\n```\n{schema_str}\n```"
        instructions_header = "Instructions & Constraints:"
        instructions_body = f"""
        1.  **Analyze Request:** Understand the user's desired visualization (type, data columns, relationships).
        2.  **Use Schema:** Identify the exact column names from the schema that correspond to the user's request. Use the column names as they appear in the schema string.
        3.  **Select Plot Type:** Choose the most appropriate plot type from the 'Available Plot Types' list based on the request and data columns.
        4.  **Identify Columns:** Determine the column(s) for the X-axis (`x_col`), Y-axis (`y_col`), color (`color_col`), size (`size_col`), etc., as applicable to the plot type and request. Use `null` if a parameter is not applicable or not specified.
        5.  **Aggregation (for Bar/Line):** If the request implies aggregation (e.g., "total sales per region", "average price over time"), identify the aggregation function (`aggregation`: 'sum', 'mean', 'count', 'median', etc.) and the column to aggregate (`y_col` usually becomes the aggregated value). The `x_col` is typically the grouping column or time axis. For a simple bar chart of counts, `y_col` might be null and `aggregation` would be 'count'.
        6.  **Output Format:** Respond ONLY with a single, valid JSON object containing the extracted parameters. Do NOT include any explanations, comments, or markdown formatting (like ```json ... ```).

        JSON Output Structure:
        {{
          "plot_type": "...",            // One of [{supported_types_str}]
          "x_col": "...",                // Column name from schema for X-axis, or null
          "y_col": "...",                // Column name from schema for Y-axis, or null
          "color_col": "...",            // Column name for color encoding, or null
          "size_col": "...",             // Column name for size encoding (scatter), or null
          "aggregation": "...",          // Aggregation function ('count', 'sum', 'mean', etc.), or null
          "error": "..."                 // Optional: Error message if request cannot be fulfilled, otherwise null or omit.
        }}

        Example Request 1: "Show distribution of age using a histogram"
        Example Output 1:
        {{
          "plot_type": "histogram",
          "x_col": "age",
          "y_col": null,
          "color_col": null,
          "size_col": null,
          "aggregation": null,
          "error": null
        }}

        Example Request 2: "Plot total sales per region as a bar chart"
        Example Output 2:
        {{
          "plot_type": "bar",
          "x_col": "region",
          "y_col": "sales",
          "color_col": null,
          "size_col": null,
          "aggregation": "sum",
          "error": null
        }}

        Example Request 3: "Scatter plot of marketing spend vs revenue, colored by campaign"
        Example Output 3:
        {{
          "plot_type": "scatter",
          "x_col": "marketing_spend",
          "y_col": "revenue",
          "color_col": "campaign",
          "size_col": null,
          "aggregation": null,
          "error": null
        }}

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