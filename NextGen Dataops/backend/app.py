
    if last_error:
        return jsonify({"error": f"Cannot download, last query failed: {last_error}"}), 400
    if not sql_to_run:
        return jsonify({"error": "No successful query found to download results for."}), 404

    app.logger.info(f"Preparing CSV download session {session_id} by re-executing: {sql_to_run[:100]}...")
    results_df, error = database_agent.execute_query(sql_to_run) # Re-execute query
    if error or results_df is None:
        app.logger.error(f"CSV download: SQL re-exec failed session {session_id}. Error: {error}")
        return jsonify({"error": f"Failed data retrieval. Error: {error}"}), 500
    try:
        is_df = isinstance(results_df, pd.DataFrame)
        csv_data = results_df.to_csv(index=is_df).encode('utf-8')
        filename = DEFAULT_QUERY_RESULTS_FILENAME
        app.logger.info(f"Serving query result CSV session {session_id}: {filename}")
        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        app.logger.error(f"Download CSV error session {session_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed CSV: {e}"}), 500

# NEW Endpoint to regenerate and fetch the profile report
@app.route('/api/profile/refresh', methods=['POST']) # POST to indicate action
def refresh_profile_report_endpoint():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({"error": "Session not found"}), 400

    pg_table_name = session.get('pg_table_name')
    if not pg_table_name:
        return jsonify({"error": "No active data table found in session to profile."}), 404

    app.logger.info(f"Refreshing profile report for session {session_id}, table '{pg_table_name}'")
    try:
        # Load the current state of the data from PostgreSQL
        current_df = database_agent.get_dataframe_from_table(pg_table_name)
        if current_df is None:
            app.logger.error(f"Failed to load DataFrame from table '{pg_table_name}' for reprofiling session {session_id}.")
            return jsonify({"error": f"Could not load data from table '{pg_table_name}' for profiling."}), 500

        # Update the working_df.parquet to reflect the current state of the database.
        # This is crucial for other agents that might use the parquet file.
        save_df(session_id, 'working', current_df.copy())
        app.logger.debug(f"Updated working_df.parquet from database table '{pg_table_name}' during reprofile for session {session_id}")

        # Generate new profile report
        dbscan_params = {
            'eps': DEFAULT_DBSCAN_EPS,
            'min_samples': DEFAULT_DBSCAN_MIN_SAMPLES
        }
        profile_report = preprocessor.profile(current_df, dbscan_params)
        if profile_report is None:
            app.logger.error(f"Data re-profiling failed for session {session_id}, table '{pg_table_name}'")
            return jsonify({"error": "Failed to generate new profile report."}), 500

        session['profile_report'] = profile_report
        app.logger.info(f"Profile report refreshed and updated in session {session_id} for table '{pg_table_name}'.")
        return jsonify({"profile_report": profile_report, "message": "Profile report refreshed."}), 200

    except Exception as e:
        app.logger.error(f"Error refreshing profile report session {session_id}: {e}", exc_info=True)
        return jsonify({"error": f"An internal error occurred while refreshing profile: {str(e)}"}), 500

# --- Main Execution ---
if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.logger.info(f"Starting Flask server on {host}:{port} (Debug: {debug})...")
    # Use Waitress for better performance than dev server if needed on Windows/other OS
    # from waitress import serve
    # serve(app, host=host, port=port)
    app.run(host=host, port=port, debug=debug, use_reloader=debug)