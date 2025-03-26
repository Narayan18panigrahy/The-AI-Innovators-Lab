                elif code: # If code exists but isn't handled
                     log_msg = f"Warning: Action code '{code}' not implemented yet."
                     logs.append(log_msg); logger.warning(log_msg); continue


                if applied_msg:
                     logs.append(applied_msg)
                     logger.info(applied_msg)

            except Exception as e:
                 error_msg = f"Error applying action '{code}' to column '{col}': {e}"
                 logs.append(error_msg)
                 logger.error(error_msg, exc_info=True) # Log traceback for debugging

        logger.info("Finished applying cleaning steps.")
        return cleaned_df, logs

    # --- (Optional) LLM Suggestion Helper ---
    # def _get_llm_cleaning_suggestions(self, profile_report, llm_config):
    #     # 1. Format profile_report summary for prompt
    #     # 2. Construct prompt asking LLM for cleaning suggestions in specific format
    #     # 3. Call litellm.completion
    #     # 4. Parse LLM response (likely JSON) into the suggestion dictionary format
    #     # 5. Return list of suggestion dictionaries
    #     pass