
@app.route('/api/generate_viz_params', methods=['POST'])
def generate_viz_params_endpoint():
    """Generates plot parameters from natural language request."""
    session_id = session.get('session_id');
    if not session_id:
        return jsonify({"error": "Session not found"}), 400
    if not session.get('llm_configured'):
        return jsonify({"error": "LLM not configured"}), 400
    working_df = load_df(session_id, 'working') # Use parquet working_df
    if working_df is None:
        return jsonify({"error": "Working data not found."}), 404
    data = request.json
    nl_request = data.get('request') if isinstance(data, dict) else None
    if not nl_request:
        return jsonify({"error": "No visualization request provided."}), 400
    try:
        schema_dict = get_simple_schema_dict(working_df)
        schema_str = "\n".join([f"- {col}: {dtype}" for col, dtype in schema_dict.get('columns', {}).items()])
        app.logger.debug(f"Schema string for Viz Agent:\n{schema_str}")
        params, error = nl_to_viz.generate_viz_params(nl_request, schema_str, session['llm_config'], schema_dict)
        if error:
            app.logger.error(f"Viz params generation failed session {session_id}: {error}")
            return jsonify({"error": f"Viz params generation failed: {error}"}), 500
        if not params:
            return jsonify({"error": "Viz params generation returned empty result"}), 500
        app.logger.info(f"Viz params generated session {session_id}: {params}")
        return jsonify({"params": params}), 200
    except Exception as e:
        app.logger.error(f"Generate viz params error session {session_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed viz params: {e}"}), 500

@app.route('/api/generate_plot', methods=['POST'])
def generate_plot_endpoint():
    session_id = session.get('session_id');
    if not session_id:
        return jsonify({"error": "Session not found"}), 400
    working_df = load_df(session_id, 'working') # Load parquet for plotting
    if working_df is None:
        return jsonify({"error": "Working data not found."}), 404
    data = request.json
    plot_params = data.get('params') if isinstance(data, dict) else None
    if not isinstance(plot_params, dict):
        return jsonify({"error": "Invalid plot parameters."}), 400
    try:
        if not plotter or not hasattr(plotter, 'generate_plot'):
            return jsonify({"error": "Plotting agent unavailable."}), 503
        fig, png_bytes, plot_error = plotter.generate_plot(plot_params, working_df)
        if plot_error:
            app.logger.error(f"Plotting error session {session_id}: {plot_error}")
            return jsonify({"error": f"Plotting failed: {plot_error}"}), 500
        if not fig or not png_bytes:
            return jsonify({"error": "Plot did not return image data."}), 500
        png_base64 = base64.b64encode(png_bytes).decode('utf-8')
        plot_data_url = f"data:image/png;base64,{png_base64}"
        app.logger.info(f"Generated plot image session {session_id}")
        return jsonify({"plot_data_url": plot_data_url, "filename": DEFAULT_PLOT_FILENAME}), 200
    except Exception as e:
        app.logger.error(f"Generate plot error session {session_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed plot: {e}"}), 500

@app.route('/api/download/profile_pdf', methods=['GET'])
def download_profile_pdf():
     session_id = session.get('session_id');
     if not session_id:
         return jsonify({"error": "Session not found"}), 400
     profile_report = session.get('profile_report')
     dataframe_name = session.get('dataframe_name', 'data')

     # Add this logging
     #app.logger.info(f"Profile report for PDF generation: {profile_report}")

     if not profile_report:
         app.logger.error(f"Profile report not found in session for PDF download. Session ID: {session_id}") # More specific log
         return jsonify({"error": "Profile report not found."}), 404
     try:
         pdf_bytes = reporter.generate_report_pdf(profile_report, dataframe_name)
         if not pdf_bytes:
             return jsonify({"error": "Failed PDF generation."}), 500
         filename = f"{secure_filename(dataframe_name)}_profile_report.pdf"
         app.logger.info(f"Serving profile PDF session {session_id}: {filename}")
         response = make_response(pdf_bytes)
         response.headers['Content-Type'] = 'application/pdf'
         response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
         return response
     except Exception as e:
         app.logger.error(f"Download profile PDF error session {session_id}: {e}", exc_info=True)
         return jsonify({"error": f"Failed PDF: {e}"}), 500

@app.route('/api/download/query_result_csv', methods=['GET'])
def download_query_result_csv():
    session_id = session.get('session_id');
    if not session_id:
        return jsonify({"error": "Session not found"}), 400

    # Load the RAW result dataframe stored after the last SUCCESSFUL execution
    # Note: This assumes 'last_query_result_raw' holds the full DF, which is risky for memory.
    # A better approach is still re-executing 'last_generated_sql'.
    sql_to_run = session.get('last_generated_sql')
    last_error = session.get('last_query_error')