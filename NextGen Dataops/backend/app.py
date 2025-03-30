@app.route('/api/generate_query', methods=['POST'])
def generate_query_endpoint():
    session_id = session.get('session_id');
    if not session_id:
        return jsonify({"error": "Session not found"}), 400
    app.logger.info(f"Generating SQL query for session {session_id}")
    if not session.get('llm_configured'):
        return jsonify({"error": "LLM not configured"}), 400

    # *** Get PG table and schema NAMES from session ***
    pg_table_name_full = session.get('pg_table_name') # e.g., "public.sample___superstore"
    if not pg_table_name_full:
        return jsonify({"error": "Database table information not found in session."}), 404

    data = request.json
    nl_query = data.get('query') if isinstance(data, dict) else None
    if not nl_query:
        return jsonify({"error": "No query provided."}), 400

    # *** Extract schema and table name parts ***
    # Handle potential quoting if Identifier added them (unlikely for simple names)
    schema_parts = pg_table_name_full.replace('"', '').split('.')
    db_schema_name = schema_parts[0] if len(schema_parts) > 1 else DB_DEFAULT_SCHEMA_NAME
    db_table_name = schema_parts[-1]
    app.logger.debug(f"Extracted Schema: '{db_schema_name}', Table: '{db_table_name}' for schema lookup.")

    # *** Call the CORRECT DatabaseAgent method to get the schema string ***
    schema_str = database_agent.get_table_schema_for_llm(db_table_name, db_schema_name)
    if schema_str.startswith("Error:"):
        app.logger.error(f"Failed to get schema string for {db_schema_name}.{db_table_name}: {schema_str}")
        return jsonify({"error": f"Database schema not found or failed to load ({schema_str})."}), 404

    app.logger.debug(f"Schema string being passed to NLtoSQLAgent:\n{schema_str}") # Log the schema string

    # Call NLtoSQLAgent with the formatted schema string
    sql_query, error = nl_to_sql.generate_sql_query(nl_query, schema_str, session['llm_config'])

    if error:
        app.logger.error(f"SQL generation failed session {session_id}: {error}")
        return jsonify({"error": f"SQL generation failed: {error}"}), 500
    if not sql_query:
         return jsonify({"error": "SQL generation returned empty result"}), 500

    # Store query info in session
    session['last_nl_query'] = nl_query
    session['last_generated_sql'] = sql_query
    session.pop('last_query_result_raw', None)
    session.pop('last_nl_answer', None)
    session.pop('last_query_error', None)

    app.logger.info(f"SQL query generated for session {session_id}")
    return jsonify({"query": sql_query}), 200 # Return the generated SQL query

# *** Renamed & Refactored Endpoint: Executes SQL and gets NL answer ***
@app.route('/api/execute_query', methods=['POST'])
def execute_query_endpoint():
    session_id = session.get('session_id');
    if not session_id:
        return jsonify({"error": "Session not found"}), 400

    data = request.json
    sql_query_to_execute = data.get('sql_query') if isinstance(data, dict) else session.get('last_generated_sql')
    if not sql_query_to_execute:
        return jsonify({"error": "No SQL query provided or found in session."}), 400

    app.logger.info(f"Attempting to execute SQL for session {session_id}: {sql_query_to_execute[:200]}...")
    original_nl_query = session.get('last_nl_query', "the user's question") # Needed for NL answer

    max_retries = nl_to_sql.MAX_RETRIES # Get from agent
    attempt = 0
    results_df = None
    db_error_feedback = None
    llm_config = session.get('llm_config')
    if not llm_config:
        return jsonify({"error": "LLM config not found in session."}), 400 # Needed for retry

    while attempt <= max_retries:
        results_df, db_error = database_agent.execute_query(sql_query_to_execute)
        if db_error:
            db_error_feedback = str(db_error)
            session['last_query_error'] = db_error_feedback
            app.logger.error(f"SQL exec attempt {attempt+1} failed session {session_id}. Error: {db_error_feedback}")
            if attempt < max_retries:
                app.logger.info(f"Attempting LLM retry ({attempt+1}/{max_retries}) to fix SQL.")
                # Get schema string again for retry prompt
                pg_table_name_full = session.get('pg_table_name')
                if not pg_table_name_full: return jsonify({"error": "Table name not found for retry."}), 500
                schema_parts = pg_table_name_full.replace('"', '').split('.')
                db_schema_name = schema_parts[0] if len(schema_parts) > 1 else DB_DEFAULT_SCHEMA_NAME
                db_table_name = schema_parts[-1]
                schema_str = database_agent.get_table_schema_for_llm(db_table_name, db_schema_name)
                if schema_str.startswith("Error:"): return jsonify({"error": f"Schema not found for retry ({schema_str})."}), 500

                corrected_sql, gen_error = nl_to_sql.generate_sql_query(
                    nl_question=original_nl_query, schema_str=schema_str, llm_config=llm_config,
                    previous_query=sql_query_to_execute, db_error=db_error_feedback
                )
                if gen_error:
                    return jsonify({"error": f"SQL Execution Failed: {db_error_feedback}. LLM retry also failed: {gen_error}"}), 500
                if not corrected_sql: