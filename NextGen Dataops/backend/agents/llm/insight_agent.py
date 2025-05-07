        report_summary_str = self._format_report_for_prompt(profile_report, ner_report, dataframe_name)
        if report_summary_str == "No profiling report available.":
            logger.error("Cannot generate summary: Profiling report is missing or invalid.")
            return "Error: Profiling report is missing or invalid."
        logger.debug(f"Formatted Report Summary for Prompt:\n{report_summary_str}")

        messages = self._construct_prompt(report_summary_str)
        temperature = 0.5 # Allow reasonable creativity for summarization
        max_tokens = 400  # Adjust based on desired summary length

        # Call the centralized LLM execution function
        summary_text, error = execute_llm_completion(
            llm_config=llm_config,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Handle the response
        if error:
            # Error should have been logged by llm_client, just return it
            # No need to log again here unless adding context
            logger.error(f"InsightAgent received error from LLM client: {error}")
            return f"Error generating summary: {error}"
        elif summary_text:
            logger.info(f"Generated Summary Text (snippet): {summary_text[:100]}...") # Log snippet
            return summary_text.strip()
        else:
            logger.warning("Insight Agent: LLM client returned empty content without specific error.")
            return "LLM response was empty."
