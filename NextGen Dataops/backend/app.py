def get_session_state_endpoint():
    session_id = session.get('session_id', 'N/A')
    # Check if PG table exists in session state
    pg_table_exists = session.get('pg_table_name') is not None
    return jsonify({
        "session_id": session_id,
        "dataframe_name": session.get("dataframe_name"),
        "llm_config": session.get("llm_config"),
        "llm_configured": session.get("llm_configured", False),
        "profile_report": session.get("profile_report"),
        "working_df_available": pg_table_exists, # Base availability on PG table now
        "pg_table_name": session.get("pg_table_name") # Return table name if exists
    })

@app.route('/api/upload', methods=['POST'])
def upload_file_endpoint():
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    app.logger.info(f"Upload request for session {session_id}")
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    filename = secure_filename(file.filename)
    if not file or not filename:
        return jsonify({"error": "No selected file or invalid filename"}), 400
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in ALLOWED_FILE_EXTENSIONS:
        return jsonify({"error": f"Invalid file type. Allowed: {', '.join(ALLOWED_FILE_EXTENSIONS)}"}), 400
    try:
        # Clear previous session state associated with old data
        keys_to_clear = ['pg_table_name', 'pg_schema_for_llm', 'dataframe_name', 'profile_report', 'ner_report', 'cleaning_suggestions', 'feature_suggestions', 'llm_summary', 'generated_plots_metadata', 'last_nl_query', 'last_query_result_raw', 'last_nl_answer', 'last_query_error', 'last_generated_sql', 'original_df_path', 'working_df_path']
        for key in keys_to_clear:
            session.pop(key, None)
        clean_session_data(session_id) # Clean old temp files

        # Load DataFrame using FileLoadingAgent
        temp_upload_dir = get_session_data_dir(session_id)
        temp_upload_path = temp_upload_dir / f"upload_{uuid.uuid4().hex}_{filename}"
        file.save(temp_upload_path)
        df = file_loader.load_data(temp_upload_path);
        try:
            os.remove(temp_upload_path)
        except OSError:
            pass # Ignore if file already gone

        if df is None:
            return jsonify({"error": "Failed to load data from file"}), 400
        session['dataframe_name'] = filename # Store original filename

        # --- Create table in PostgreSQL and load data ---
        base_table_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        pg_table_name, pg_schema_for_llm = database_agent.create_table_from_df(df, base_table_name)

        if not pg_table_name or not pg_schema_for_llm:
            app.logger.error(f"Failed to create/load table in PostgreSQL for session {session_id}")
            return jsonify({"error": "Failed to prepare data in the database."}), 500

        session['pg_table_name'] = pg_table_name
        session['pg_schema_for_llm'] = pg_schema_for_llm
        app.logger.info(f"DataFrame loaded into PostgreSQL table: {pg_table_name} for session {session_id}")

        # --- Save working DF to parquet as well, for agents that might need it ---
        # This allows cleaning/FE to operate on pandas DF easily before reloading to PG
        save_df(session_id, 'working', df.copy())

        # Run profiling on the initial DataFrame
        profile_report = preprocessor.profile(df, {'eps': DEFAULT_DBSCAN_EPS, 'min_samples': DEFAULT_DBSCAN_MIN_SAMPLES})
        if profile_report is None:
            app.logger.error(f"Data profiling failed for session {session_id}")
        session['profile_report'] = profile_report

        app.logger.info(f"File '{filename}' uploaded and processed for session {session_id}.")
        return jsonify({
                "message": f"File '{filename}' processed. Data available for querying in table '{pg_table_name}'.",
                "rows": len(df), "columns": len(df.columns), "profile_report": profile_report, "db_table": pg_table_name
                }), 200

    except Exception as e:
        app.logger.error(f"Upload failed for session {session_id}: {e}", exc_info=True)
        clean_session_data(session_id)
        session.pop('original_df_path', None)
        session.pop('working_df_path', None)
        session.pop('pg_table_name', None) # Clean up state
        return jsonify({"error": f"An internal error occurred during upload: {str(e)}"}), 500

@app.route('/api/config_llm', methods=['POST'])
def config_llm_endpoint():
    session_id = session.get('session_id');
    if not session_id:
        return jsonify({"error": "Session not found"}), 400
    config_data = request.json
    if not isinstance(config_data, dict) or not all(k in config_data for k in ['provider', 'model_name', 'credentials']):
        return jsonify({"error": "Invalid LLM configuration data format"}), 400
    if config_data['provider'] not in SUPPORTED_PROVIDERS:
        return jsonify({"error": f"Unsupported provider: {config_data['provider']}"}), 400
    session['llm_config'] = config_data
    session['llm_configured'] = True
    app.logger.info(f"LLM Config updated for session {session_id}")
    return jsonify({"message": "LLM configured successfully", "config": config_data}), 200

# *** Renamed Endpoint: Generates SQL Query ***