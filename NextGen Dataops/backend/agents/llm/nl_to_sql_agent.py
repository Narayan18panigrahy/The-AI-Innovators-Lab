# backend/agents/llm/nl_to_sql_agent.py
# import traceback # Removed - No longer needed
import re
import logging
from typing import List, Dict, Tuple, Optional

# Import the centralized client function
try:
    from agents.llm.llm_client import execute_llm_completion
except ImportError:
    # This critical error should be logged centrally, maybe raise exception
    logging.critical("CRITICAL ERROR: Could not import llm_client.py in NLtoSQLAgent. LLM functionality will be disabled.")
    execute_llm_completion = None # Define as None to allow class definition

logger = logging.getLogger(__name__)

class NLtoSQLAgent:
    """
    Agent that uses an LLM to convert natural language questions
    into executable PostgreSQL SELECT queries based on a provided database schema.
    Includes logic for retrying with error feedback.
    """
    MAX_RETRIES = 1 # Number of retries for SQL generation if initial query fails

    def __init__(self):
        """Initializes the NLtoSQLAgent."""
        logger.debug("NLtoSQLAgent initialized.")
        pass

    def _construct_prompt(self, nl_question: str, schema_str: str, previous_query: Optional[str] = None, db_error: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Constructs the prompt messages for the LLM for PostgreSQL.
        Includes optional fields for retry attempts with error feedback.
        """
        system_prompt_header = "You are an expert PostgreSQL database assistant. Your task is to translate a natural language question into a single, syntactically correct PostgreSQL SELECT query."

        schema_section = f"Database Schema (PostgreSQL - table and column names might be quoted if they required sanitization):\n```sql\n{schema_str}\n```"

        instructions = """
        Instructions & Constraints:
        1.  **Analyze the Question:** Understand the user's intent and the specific data requested.
        2.  **Use the Schema:** MUST only use the table name(s) and column names provided in the schema above. Pay close attention to exact names and quoting (e.g., use `"Column Name"` if the schema shows it quoted). PostgreSQL treats unquoted identifiers as lowercase unless quoted.
        3.  **Generate SELECT Only:** Generate ONLY a single PostgreSQL `SELECT` statement.
        4.  **DO NOT Generate:** `UPDATE`, `DELETE`, `INSERT`, `DROP`, `CREATE`, `ALTER`, or any other DDL/DML statements.
        5.  **PostgreSQL Syntax:** Ensure the query uses valid PostgreSQL syntax (e.g., date functions `DATE_TRUNC()`, `EXTRACT(FIELD FROM source)`, string concatenation `||`, case-insensitive comparison `ILIKE`, standard aggregate functions, window functions if appropriate). Use single quotes for string literals (e.g., `WHERE category = 'Electronics'`).
        6.  **Clarity:** If the question is ambiguous, generate the most probable and useful query based on the schema. Do not ask clarifying questions.
        7.  **Output Format:** Respond ONLY with the generated SQL query. Do not include explanations, comments, introductory phrases, or markdown formatting (like ```sql ... ```). Just the raw SQL query.
        """
        user_message_content = f"Natural Language Question: {nl_question.strip()}"

        # --- Fallback / Retry Logic Prompting ---
        if previous_query and db_error:
            logger.debug("Constructing NL-to-SQL retry prompt with error feedback.")
            system_prompt_header = "You are an expert PostgreSQL database assistant. Your previous attempt to generate SQL resulted in an error. Analyze the error and provide a corrected PostgreSQL SELECT query."
            # Clean up common error parts that might confuse the LLM
            db_error_cleaned = re.sub(r'LINE \d+: |HINT:.*|CONTEXT:.*', '', db_error, flags=re.IGNORECASE).strip()

            user_message_content = f"""
            Original Natural Language Question: {nl_question.strip()}

            The following PostgreSQL schema was used:
            ```sql
            {schema_str}

            Your previously generated SQL query, which FAILED:
            {previous_query.strip()}

            Resulted in the following database error:
            {db_error_cleaned}

            Please carefully review the schema, the original question, your previous query, and the database error (especially regarding table/column names and syntax). Provide a corrected and valid PostgreSQL SELECT query based only on the schema and question.
            Respond ONLY with the corrected SQL query, without any explanations or markdown.
            """

        system_prompt = f"{system_prompt_header}\n\n{schema_section}\n{instructions}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message_content.strip()},
        ]
        # Avoid logging potentially large schema/prompts at info level
        logger.debug(f"NL-to-SQL Prompt Messages (Retry: {bool(previous_query)}): First 100 chars user msg: {user_message_content[:100]}...")
        return messages

    def _parse_and_validate_sql(self, raw_sql: str) -> Tuple[Optional[str], Optional[str]]:
        """Parses and performs basic validation on raw SQL from LLM."""
        if not raw_sql: return None, "LLM returned an empty response."
        logger.debug(f"Raw SQL from LLM: '{raw_sql}'")
        # Basic cleaning (same as before)
        clean_sql = raw_sql.strip()
        match = re.match(r"^\s*```(?:sql)?\s*(.*?)\s*```\s*$", clean_sql, re.IGNORECASE | re.DOTALL)
        if match: clean_sql = match.group(1).strip()
        else:
            if clean_sql.lower().startswith("```sql"): clean_sql = clean_sql[6:].strip()
            elif clean_sql.startswith("```"): clean_sql = clean_sql[3:].strip()
            if clean_sql.endswith("```"): clean_sql = clean_sql[:-3].strip()

        clean_sql = clean_sql.strip().strip(';') # Remove leading/trailing whitespace and semicolons

        if not clean_sql: return None, "LLM response was empty after cleaning formatting."