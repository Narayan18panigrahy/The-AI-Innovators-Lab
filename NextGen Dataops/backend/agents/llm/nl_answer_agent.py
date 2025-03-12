
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