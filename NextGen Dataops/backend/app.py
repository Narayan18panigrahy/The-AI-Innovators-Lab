        # Use openpyxl engine for .xlsx format
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            working_df.to_excel(writer, index=False, sheet_name='Sheet1')
        output.seek(0)

        app.logger.info(f"Prepared Excel download for session {session_id}, filename: {excel_filename}")
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=excel_filename
        )
    except Exception as e:
        app.logger.error(f"Error generating Excel file for session {session_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to generate Excel file: {str(e)}"}), 500

@app.route('/api/suggest_cleaning', methods=['GET'])
def suggest_cleaning_endpoint():
    session_id = session.get('session_id');
    if not session_id:
        return jsonify({"error": "Session not found"}), 400
    profile_report = session.get('profile_report')
    working_df = load_df(session_id, 'working') # Use parquet working_df
    if working_df is None or profile_report is None:
        return jsonify({"error": "Data or profile not available."}), 404
    try:
        suggestions = cleaner.suggest_cleaning_steps(profile_report, working_df)
        app.logger.info(f"Generated {len(suggestions)} cleaning suggestions session {session_id}")
        return jsonify({"suggestions": suggestions}), 200
    except Exception as e:
        app.logger.error(f"Suggest cleaning error session {session_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed suggestions: {e}"}), 500

@app.route('/api/suggest_features', methods=['GET'])
def suggest_features_endpoint():
    session_id = session.get('session_id');
    if not session_id:
        return jsonify({"error": "Session not found"}), 400
    working_df = load_df(session_id, 'working') # Use parquet working_df
    if working_df is None:
        return jsonify({"error": "Working data not found."}), 404
    try:
        suggestions = feature_engineer.suggest_features(working_df)
        app.logger.info(f"Generated {len(suggestions)} feature suggestions session {session_id}")
        return jsonify({"suggestions": suggestions}), 200
    except Exception as e:
        app.logger.error(f"Suggest features error session {session_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed suggestions: {e}"}), 500

@app.route('/api/ner_analyze', methods=['POST'])
def ner_analyze_endpoint():
    session_id = session.get('session_id');
    if not session_id:
        return jsonify({"error": "Session not found"}), 400
    working_df = load_df(session_id, 'working') # Use parquet working_df
    if working_df is None:
        return jsonify({"error": "Working data not found."}), 404
    data = request.json
    columns_to_analyze = data.get('columns') if isinstance(data, dict) else None
    if not isinstance(columns_to_analyze, list):
        return jsonify({"error": "Invalid 'columns' list."}), 400
    try:
        if not text_analyzer or not hasattr(text_analyzer, 'nlp') or not text_analyzer.nlp:
            return jsonify({"error": "Text Analysis agent/model unavailable."}), 503
        ner_report = text_analyzer.analyze_entities(working_df, columns_to_analyze)
        if ner_report is None:
            return jsonify({"error": "NER analysis could not be performed."}), 500
        session['ner_report'] = ner_report
        app.logger.info(f"NER analysis completed session {session_id}")
        return jsonify(ner_report), 200
    except Exception as e:
        app.logger.error(f"NER analysis error session {session_id}: {e}", exc_info=True)
        return jsonify({"error": f"NER analysis failed: {e}"}), 500

@app.route('/api/generate_summary', methods=['POST'])
def generate_summary_endpoint():
    session_id = session.get('session_id');
    if not session_id:
        return jsonify({"error": "Session not found"}), 400
    if not session.get('llm_configured'):
        return jsonify({"error": "LLM not configured"}), 400
    profile_report = session.get('profile_report')
    if profile_report is None:
        return jsonify({"error": "Profile report not available."}), 404
    try:
        summary = insight_generator.generate_summary(
            profile_report=profile_report, llm_config=session['llm_config'],
            ner_report=session.get('ner_report'), dataframe_name=session.get('dataframe_name')
        )
        if summary and not summary.startswith("Error:"):
            session['llm_summary'] = summary
            app.logger.info(f"Generated AI summary session {session_id}")
            return jsonify({"summary": summary}), 200
        else:
            error_msg = summary if summary else "Summary generation returned empty."
            app.logger.error(f"Generate summary error session {session_id}: {error_msg}")
            return jsonify({"error": error_msg}), 500
    except Exception as e:
        app.logger.error(f"Generate summary error session {session_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed summary: {e}"}), 500