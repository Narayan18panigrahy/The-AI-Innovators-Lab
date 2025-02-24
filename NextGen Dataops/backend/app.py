                    return jsonify({"error": f"SQL Execution Failed: {db_error_feedback}. LLM retry returned empty SQL."}), 500
                sql_query_to_execute = corrected_sql
                session['last_generated_sql'] = sql_query_to_execute # Update stored SQL
                app.logger.info(f"LLM generated corrected SQL (attempt {attempt+2}): {sql_query_to_execute[:200]}...")
                attempt += 1
                continue # Retry execution
            else:
                app.logger.error(f"Max retries reached for SQL execution session {session_id}. Final error: {db_error_feedback}")
                return jsonify({"error": f"SQL Execution Failed after {max_retries+1} attempts: {db_error_feedback}"}), 500
        else:
            # SQL Success
            session.pop('last_query_error', None)
            session['last_query_result_raw'] = results_df # Store for NL Answer Agent
            app.logger.info(f"SQL query executed successfully session {session_id}.")
            break # Exit retry loop

    # --- Generate Natural Language Answer from SQL results ---
    nl_answer = None # Initialize
    nl_gen_error = None
    llm_skipped_due_to_size = False

    if results_df is not None and session.get('llm_configured'):
        app.logger.info(f"Generating NL answer for session {session_id}...")
        original_nl_query = session.get('last_nl_query', "the user's question")
        llm_config = session.get('llm_config')

        # Call the updated NLAnswerAgent method
        answer_text, error_msg, llm_was_called = nl_answer_generator.generate_nl_answer(
            original_question=original_nl_query,
            data_results=results_df,
            llm_config=llm_config,
            max_input_tokens=500 # Or make configurable
        )

        if not llm_was_called:
            # LLM was skipped due to data size
            nl_answer = "The data result is too large to generate a natural language summary. Displaying raw data snippet."
            llm_skipped_due_to_size = True
            app.logger.warning(f"NL answer skipped due to data size for session {session_id}")
        elif error_msg:
            # LLM was called but failed
            nl_gen_error = error_msg
            nl_answer = f"Could not generate a natural language answer (Error: {nl_gen_error}). Raw data is available."
            app.logger.error(f"NL answer generation failed for session {session_id}: {nl_gen_error}")
        elif answer_text:
            # LLM was called and succeeded
            nl_answer = answer_text
            session['last_nl_answer'] = nl_answer
            app.logger.info(f"NL Answer generated session {session_id}: {nl_answer[:100]}...")
        else:
            # LLM was called but returned empty
            nl_answer = "Could not generate a natural language answer (LLM returned empty). Raw data is available."
            app.logger.warning(f"NL answer generation returned empty for session {session_id}")

    elif results_df is not None: # SQL success but LLM not configured
        nl_answer = "LLM not configured for natural language summary. Displaying raw data."

    # --- Prepare Response ---
    raw_data_snippet = None
    raw_data_type = "NotApplicable"
    if results_df is not None:
        # session['last_query_result_raw'] = results_df # Already stored above
        max_rows_to_send = 50
        row_count = len(results_df)
        try:
             # Prepare snippet for frontend display
             if isinstance(results_df, pd.DataFrame):
                 raw_data_snippet = results_df.head(max_rows_to_send).to_dict(orient="records")
                 raw_data_type = f"DataFrame (showing first {min(row_count, max_rows_to_send)} of {row_count} rows)"
             elif isinstance(results_df, pd.Series):
                  raw_data_snippet = results_df.head(max_rows_to_send).reset_index().to_dict(orient="records")
                  raw_data_type = f"Series (showing first {min(row_count, max_rows_to_send)} of {row_count} items)"
             # Add handling for scalar/list if needed, though less likely for SQL results
             else:
                 raw_data_snippet = str(results_df) # Fallback
                 raw_data_type = str(type(results_df).__name__) + " (stringified)"

        except Exception as e:
            app.logger.error(f"Error preparing raw data snippet for session {session_id}: {e}")
            raw_data_snippet = "[Error preparing raw data view]"
            raw_data_type = "Error"


    if results_df is not None: # If SQL was successful
        return jsonify({
            "nl_answer": nl_answer, # The main result for the user
            "raw_data": raw_data_snippet,
            "raw_data_type": raw_data_type,
            "sql_query_executed": sql_query_to_execute,
            "llm_skipped": llm_skipped_due_to_size # Add flag for frontend
            }), 200
    else:
        # SQL execution failed after retries
        return jsonify({"error": f"SQL execution failed: {db_error_feedback or 'Unknown execution error'}"}), 500

# --- Cleaning & FE Endpoints (Updated to reload PG table) ---

MAX_PREVIEW_ROWS = 50 # Define how many rows for the preview

@app.route('/api/apply_cleaning', methods=['POST'])