def apply_cleaning_endpoint():
    session_id = session.get('session_id');
    if not session_id:
        return jsonify({"error": "Session not found"}), 400
    working_df = load_df(session_id, 'working') # Load from parquet
    if working_df is None:
        return jsonify({"error": "Working data (parquet) not found."}), 404
    data = request.json
    actions = data.get('actions') if isinstance(data, dict) else None
    if not isinstance(actions, list):
        return jsonify({"error": "Invalid 'actions' list."}), 400
    if not actions:
        return jsonify({"message": "No actions provided.", "logs": [], "data_preview": None}), 200 # Added data_preview
    try:
        modified_df, logs = cleaner.apply_cleaning_steps(working_df, actions)
        save_df(session_id, 'working', modified_df) # Save modified parquet

        base_table_name = session.get('dataframe_name', 'cleaned_data').rsplit('.', 1)[0]
        new_pg_table, new_pg_schema = database_agent.create_table_from_df(modified_df, base_table_name)
        if not new_pg_table:
            return jsonify({"error": "Failed to update data in database after cleaning."}), 500
        session['pg_table_name'] = new_pg_table
        session['pg_schema_for_llm'] = new_pg_schema

        clear_downstream_session_state("cleaning")
        app.logger.info(f"Applied cleaning session {session_id}. DB table '{new_pg_table}' updated.")

        preview_df = modified_df.head(MAX_PREVIEW_ROWS)
        # Using orient='split' is good for reconstructing DataFrame in JS
        data_preview_json = preview_df.to_json(orient="split", date_format="iso", default_handler=str)

        return jsonify({
            "message": "Cleaning actions applied and data updated.",
            "logs": logs,
            "data_preview": data_preview_json # Add data preview to response
        }), 200
    except Exception as e:
        app.logger.error(f"Apply cleaning error session {session_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to apply actions: {e}"}), 500

@app.route('/api/apply_features', methods=['POST'])
def apply_features_endpoint():
    session_id = session.get('session_id');
    if not session_id:
        return jsonify({"error": "Session not found"}), 400
    working_df = load_df(session_id, 'working') # Load from parquet
    if working_df is None:
        return jsonify({"error": "Working data (parquet) not found."}), 404
    data = request.json
    features_to_create = data.get('features') if isinstance(data, dict) else None
    if not isinstance(features_to_create, list):
        return jsonify({"error": "Invalid 'features' list."}), 400
    if not features_to_create:
        return jsonify({"message": "No features provided.", "logs": [], "data_preview": None}), 200 # Added data_preview
    try:
        modified_df, logs = feature_engineer.apply_features(working_df, features_to_create)
        save_df(session_id, 'working', modified_df) # Save modified parquet

        base_table_name = session.get('dataframe_name', 'engineered_data').rsplit('.', 1)[0]
        new_pg_table, new_pg_schema = database_agent.create_table_from_df(modified_df, base_table_name)
        if not new_pg_table:
            return jsonify({"error": "Failed to update data in database after FE."}), 500
        session['pg_table_name'] = new_pg_table
        session['pg_schema_for_llm'] = new_pg_schema

        clear_downstream_session_state("feature engineering")
        app.logger.info(f"Applied features session {session_id}. DB table '{new_pg_table}' updated.")

        preview_df = modified_df.head(MAX_PREVIEW_ROWS)
        data_preview_json = preview_df.to_json(orient="split", date_format="iso", default_handler=str)

        return jsonify({
            "message": "Features created successfully.",
            "logs": logs,
            "data_preview": data_preview_json # Add data preview to response
        }), 200
    except Exception as e:
        app.logger.error(f"Apply features error session {session_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to create features: {e}"}), 500

@app.route('/api/download_data/excel', methods=['GET'])
def download_data_excel_endpoint():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({"error": "Session not found"}), 400

    working_df = load_df(session_id, 'working')
    if working_df is None:
        return jsonify({"error": "No working data found to download."}), 404

    dataframe_name = session.get('dataframe_name', 'exported_data')
    # Basic filename sanitization and ensure .xlsx extension
    excel_filename = "".join(c if c.isalnum() or c in ['_', '.'] else '_' for c in dataframe_name)
    if not excel_filename.lower().endswith(('.xlsx', '.xls')):
        excel_filename += ".xlsx"
    excel_filename = f"{excel_filename.split('.')[0]}_modified.xlsx"


    try:
        output = BytesIO()