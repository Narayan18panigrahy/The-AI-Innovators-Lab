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