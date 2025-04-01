# backend/agents/llm/nl_answer_agent.py

# import streamlit as st # Removed - For debug only
# import traceback # Removed - No longer needed
import logging
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any
import math # For token estimation

# Import the centralized client function
try:
    from agents.llm.llm_client import execute_llm_completion
except ImportError:
    # Log this critical error
    logging.critical("CRITICAL ERROR: Could not import llm_client.py in NLAnswerAgent. LLM functionality will be disabled.")
    execute_llm_completion = None

logger = logging.getLogger(__name__)

# Simple heuristic: characters per token (adjust based on model/language)
CHARS_PER_TOKEN_ESTIMATE = 4

class NLAnswerAgent:
    """
    Agent that uses an LLM to generate a user-friendly rephrasing of
    structured data results, or returns raw data if results are too large.
    """

    def __init__(self):
        logger.debug("NLAnswerAgent initialized.")
        pass

    def _format_data_for_prompt(self, data_results: Any, max_rows=15, max_items=20, max_chars=2000) -> Tuple[str, bool]:
        """
        Converts data into a string for LLM prompt, returns string and truncation flag.
        Limits the string length to avoid excessive prompt size.
        """
        data_str = ""
        is_truncated = False
        original_len = 0
        logger.debug(f"Formatting data for prompt. Type: {type(data_results)}")

        try:
            if isinstance(data_results, pd.DataFrame):
                original_len = len(data_results)
                if data_results.empty: data_str = "No matching data was found."
                else:
                    data_str = "Data found:\n"
                    data_str += data_results.head(max_rows).to_string(index=False, na_rep='NULL')
                    if original_len > max_rows: is_truncated = True; data_str += f"\n... ({original_len - max_rows} more rows exist)"
            elif isinstance(data_results, pd.Series):
                original_len = len(data_results)
                if data_results.empty: data_str = "No data was found."
                else:
                    data_str = "Data found:\n"
                    data_str += data_results.head(max_rows).to_string(index=False, na_rep='NULL')
                    if original_len > max_rows: is_truncated = True; data_str += f"\n... ({original_len - max_rows} more items exist)"
            elif isinstance(data_results, (list, tuple)):
                original_len = len(data_results)
                if not data_results: data_str = "No data was returned."
                elif original_len > max_items:
                    is_truncated = True; data_str = f"Resulting list/tuple (first {max_items} items): {str(data_results[:max_items])} ..."
                else: data_str = f"Resulting list/tuple: {str(data_results)}"
            elif data_results is None: data_str = "The query returned no specific data (NULL result)."
            else: data_str = f"The result is: {str(data_results)}" # Scalar or other

            # Final truncation based on character length
            if len(data_str) > max_chars:
                 data_str = data_str[:max_chars] + "\n... (data display truncated due to length)"
                 is_truncated = True # Mark as truncated even if row/item limit wasn't hit
                 logger.debug(f"Data string truncated to {max_chars} characters.")

        except Exception as e: logger.error(f"Error formatting data: {e}", exc_info=True); data_str = "[Error formatting data results]"; is_truncated = True

        logger.debug(f"Formatted data string (truncated={is_truncated}): {data_str[:200]}...") # Log snippet
        return data_str, is_truncated

    def _construct_prompt(self, original_question: str, data_results_str: str, is_truncated: bool) -> List[Dict[str, str]]:
        """ Constructs prompt for LLM to simply rephrase the provided data. """
        system_prompt = """You are a helpful data assistant. Rephrase the provided data results concisely and clearly in natural language to answer the user's original question.

Instructions:
1.  Directly use the information presented in the "Data Results" section.
2.  Present the answer in a user-friendly way (e.g., "The total profit for the West region is $X.", "The available departments are A, B, C.").
3.  If the data is tabular, list the key findings or values relevant to the question.
4.  If the data indicates "No data", state that clearly.
5.  **Do NOT perform any calculations or summaries beyond what is explicitly shown in the data.**
6.  **Do NOT add opinions or information not present in the data.**
7.  If the data provided seems incomplete or truncated (as indicated), simply state the answer based on the available data and **do not** mention that it might be incomplete unless the data string itself says "...".
8.  Avoid technical jargon (SQL, query, database, etc.). Refer to it as "the information" or "the data".
9.  Be concise.
"""

        user_prompt_content = f"""
Original Question: {original_question}

Data Results:
---
{data_results_str}
---

Please rephrase the data results above to directly answer the original question in a user-friendly sentence or list:
"""
        messages = [ {"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt_content.strip()} ]
        logger.debug(f"NL Answer Agent Prompt Messages constructed for question: '{original_question[:100]}...'")
        return messages

    def estimate_token_count(self, text: str) -> int:
        """ Rough estimate of token count based on character length. """
        return math.ceil(len(text) / CHARS_PER_TOKEN_ESTIMATE)

    def generate_nl_answer(self, original_question: str, data_results: Any, llm_config: Dict, max_input_tokens: int = 500) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Generates a natural language answer by rephrasing data results,
        or indicates if data is too large for LLM processing.

        Args:
            original_question: The user's original NL question.
            data_results: The data returned from the successful query.
            llm_config: LLM configuration dictionary.
            max_input_tokens: Approx token limit for data sent to LLM.

        Returns:
            (natural_language_answer | None, error_message | None, data_sent_to_llm: bool) tuple.
            If data_sent_to_llm is False, nl_answer will be None, and frontend should display raw data.
        """
        logger.info(f"Generating NL answer for question: '{original_question[:100]}...'")
        if execute_llm_completion is None:
            logger.error("LLM client function not available for NLAnswerAgent.")
            return None, "LLM client function not available.", False
        if not original_question or not llm_config:
            logger.error("Missing original question or LLM config for NL answer generation.")
            return None, "Missing question or LLM config.", False

        # Format data sample for prompt, get truncation flag
        data_results_str, _ = self._format_data_for_prompt(data_results) # Truncation flag not strictly needed now
        if "[Error formatting data results]" in data_results_str:
            logger.error("Error occurred during data formatting for NL answer prompt.")
            return None, "Error formatting results.", False

        # *** Check estimated token count BEFORE calling LLM ***
        estimated_tokens = self.estimate_token_count(data_results_str)
        logger.debug(f"Estimated token count for data results string: {estimated_tokens}")
        if estimated_tokens > max_input_tokens:
            logger.warning(f"Data results too large ({estimated_tokens} estimated tokens > {max_input_tokens}). Skipping LLM refinement.")
            # Return None for answer, None for error, and False for data_sent_to_llm
            return None, None, False # Indicate LLM was skipped

        # --- Proceed with LLM call if data size is acceptable ---
        messages = self._construct_prompt(original_question, data_results_str, False) # Pass is_truncated=False as prompt handles it now
        temperature = 0.2 # Lower temperature for direct rephrasing
        max_tokens = 300  # Output answer should still be reasonable

        logger.info("Calling LLM to generate natural language answer...")
        answer_text, error = execute_llm_completion(
            llm_config=llm_config, messages=messages,
            temperature=temperature, max_tokens=max_tokens
        )

        if error:
            logger.error(f"LLM client error during NL answer generation: {error}")
            return None, error, True # LLM was called but failed
        elif answer_text:
            logger.info("LLM generated NL answer successfully.")
            return answer_text.strip(), None, True # Success, LLM was called
        else:
            logger.warning("LLM client returned empty content for NL answer without specific error.")
            return None, "LLM client returned empty content.", True # LLM was called but returned empty