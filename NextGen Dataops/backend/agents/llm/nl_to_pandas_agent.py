# -*- coding: utf-8 -*-
"""
nl_to_pandas_agent.py

Defines the NLtoPandasAgent class responsible for translating natural language
questions into executable Pandas DataFrame query code using an LLM.
"""


# import traceback # No longer needed
import re
import logging # Import logging
from typing import List, Dict, Tuple, Optional

# Import the centralized client function
try:
    from agents.llm.llm_client import execute_llm_completion
except ImportError:
    # Log this critical error
    logging.critical("CRITICAL ERROR: Could not import llm_client.py in NLtoPandasAgent. LLM functionality will be disabled.")
    execute_llm_completion = None # Define as None to prevent NameError later

# Get a logger specific to this module
logger = logging.getLogger(__name__)

class NLtoPandasAgent:
    """
    Agent that uses an LLM to convert natural language questions
    into executable Python code using the Pandas library.
    """
    def __init__(self):
        """Initializes the NLtoPandasAgent."""
        logger.debug("NLtoPandasAgent initialized.")
        pass

    def _construct_prompt(self, nl_question: str, df_schema_str: str) -> List[Dict[str, str]]:
        """
        Constructs the prompt messages for the LLM to generate Pandas code.

        Args:
            nl_question: The user's natural language question.
            df_schema_str: A string representation of the DataFrame schema (columns and dtypes).

        Returns:
            A list of message dictionaries for the LLM API.
        """
        system_prompt = f"""You are an expert Python Pandas code generator. Your task is to translate a natural language question into a short, executable Python code snippet that uses the Pandas library to answer the question based on a given DataFrame named `df`.

DataFrame Schema (`df`):
{df_schema_str}

Instructions & Constraints:
1.  **Assume DataFrame:** Assume the data is already loaded into a Pandas DataFrame named `df`.
2.  **Use Schema:** Only use column names present in the provided DataFrame schema. Pay attention to exact column names. Column names with spaces or special characters might be represented differently in the schema string (e.g., quoted or modified) - use the exact name shown.
3.  **Generate Pandas Code:** Generate Python code using standard Pandas functions and methods (e.g., `df[...]`, `df.query()`, `df.loc[]`, `df.groupby()`, `.sum()`, `.mean()`, `.count()`, `.value_counts()`, `.sort_values()`, `.head()`, `.tail()`, `.shape`, `.columns`, `.dtypes`, etc.).
4.  **Result Variable:** The generated code *must* assign the final result (which could be a DataFrame, Series, scalar value, list, etc.) to a variable named `result`.
5.  **Concise Code:** Generate only the necessary Python code snippet to produce the `result`.
6.  **Imports:** Do NOT include any `import pandas as pd` or other import statements in your code output. Assume necessary imports are already handled.
7.  **Output Format:** Respond ONLY with the raw Python code snippet. Do not include any explanations, comments, introductory phrases (like "Here is the Python code:"), or markdown formatting (like ```python ... ```).

Example Question 1: "How many rows are there?"
Example Output 1:
result = len(df)

Example Question 2: "Show the first 5 rows"
Example Output 2:
result = df.head(5)

Example Question 3: "What are the unique values in the 'region' column?"
Example Output 3:
result = df['region'].unique().tolist()

Example Question 4: "Calculate the average 'salary' for each 'department'."
Example Output 4:
result = df.groupby('department')['salary'].mean()

Example Question 5: "Show the rows where 'sales' are greater than 1000."
Example Output 5:
result = df[df['sales'] > 1000]

Example Question 6: "What is the maximum value in the 'price' column?"
Example Output 6:
result = df['price'].max()
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": nl_question.strip()}
        ]
        logger.debug(f"NL-to-Pandas Prompt Messages: {messages}")
        return messages

    def _parse_and_validate_code(self, raw_code: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parses and performs basic validation on the raw Python code string from the LLM.

        Args:
            raw_code: The raw string output from the LLM.

        Returns:
            A tuple containing:
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
            validated_code, validation_error = self._parse_and_validate_code(raw_code)
            if validation_error:
                logger.error(f"Generated Pandas code failed validation: {validation_error}")
                return None, validation_error # Return specific parsing/validation error
            else:
                logger.info("Pandas code generated and validated successfully.")
                return validated_code, None # Success
        else:
            # Should ideally be caught by error handling in client, but as fallback:
            logger.warning("LLM client returned empty content without specific error.")
            return None, "LLM client returned empty content without specific error."