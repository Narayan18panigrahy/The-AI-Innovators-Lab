# backend/app.py

import os
import uuid
import io
import traceback
import logging
from pathlib import Path
import json
import base64 # For sending plot image data
from io import BytesIO
from flask import send_file

# Flask and extensions
from flask import Flask, request, jsonify, session, Response as FlaskResponse, send_file, make_response
from flask_session import Session # Server-side sessions
from flask_cors import CORS # For development communication with React frontend
from werkzeug.utils import secure_filename # For safer filename handling

# Data handling
from typing import Dict, Optional
import pandas as pd
import numpy as np

# --- Import Agents (Ensure paths are correct) ---
try:
    from agents.file_loading_agent import FileLoadingAgent
    from agents.preprocessing_agent import PreprocessingAgent
    from agents.reporting_agent import ReportingAgent
    # *** Import the updated DatabaseAgent ***
    from agents.database_agent import DatabaseAgent
    from agents.text_analysis_agent import TextAnalysisAgent
    from agents.cleaning_agent import CleaningAgent
    from agents.feature_engineering_agent import FeatureEngineeringAgent
    # *** Import NLtoSQLAgent and NLAnswerAgent ***
    from agents.llm.nl_to_sql_agent import NLtoSQLAgent
    from agents.llm.nl_answer_agent import NLAnswerAgent # New
    from agents.llm.nl_to_viz_agent import NLtoVizAgent
    from agents.llm.insight_agent import InsightAgent
    from agents.plotting_agent import PlottingAgent
except ImportError as e:
    # Use basic logging here as app logger might not be configured yet
    logging.critical(f"CRITICAL ERROR: Failed to import agents. Check paths and dependencies. {e}")
    exit(1)

# Import Constants
try:
    from constants import (
        SUPPORTED_PROVIDERS, ALLOWED_FILE_EXTENSIONS, MAX_UPLOAD_MB,
        TEMP_DATA_DIR_NAME, SESSION_COOKIE_NAME, DB_DEFAULT_SCHEMA_NAME, # Added DB constant
        DEFAULT_REPORT_FILENAME, DEFAULT_PLOT_FILENAME, DEFAULT_QUERY_RESULTS_FILENAME,
        DEFAULT_DBSCAN_EPS, DEFAULT_DBSCAN_MIN_SAMPLES
    )
except ImportError as e:
     # Use basic logging here
     logging.critical(f"CRITICAL ERROR: Failed to import constants.py: {e}")
     exit(1)


# --- App Initialization & Configuration ---
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', 'dev_change_this_in_prod_!@#$%^&*()'),
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR=os.path.join(app.instance_path, 'flask_session'),
    SESSION_PERMANENT=False,
    SESSION_USE_SIGNER=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024,
)
try:
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
except OSError as e:
    # Use basic logging here
    logging.critical(f"CRITICAL ERROR: Could not create instance/session directory: {e}")
    exit(1)

Session(app)
CORS(app, supports_credentials=True, origins=os.environ.get('CORS_ORIGINS', "http://localhost:3000").split(','))

TEMP_DATA_DIR = Path(TEMP_DATA_DIR_NAME)
TEMP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging AFTER app is created
logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO').upper())
app.logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO').upper())
if app.debug:
    app.logger.setLevel(logging.DEBUG)
app.logger.info("Flask application starting...")

# --- Agent Initialization ---
# Instantiate ALL agents, including DatabaseAgent and NLAnswerAgent
try:
    file_loader = FileLoadingAgent()
    preprocessor = PreprocessingAgent()
    reporter = ReportingAgent()
    database_agent = DatabaseAgent() # Instantiate DatabaseAgent
    text_analyzer = TextAnalysisAgent()
    cleaner = CleaningAgent()
    feature_engineer = FeatureEngineeringAgent()
    nl_to_sql = NLtoSQLAgent() # Use NLtoSQLAgent
    nl_answer_generator = NLAnswerAgent() # Instantiate new agent
    nl_to_viz = NLtoVizAgent()
    insight_generator = InsightAgent()
    plotter = PlottingAgent()
    app.logger.info("Agents initialized successfully.")
except Exception as agent_init_error:
     app.logger.critical(f"CRITICAL: Agent initialization failed: {agent_init_error}", exc_info=True)
     exit(1)

# --- Helper Functions ---
# Keep get_session_data_dir, save_df, load_df (for working df parquet),
# get_simple_schema_dict, clean_session_data

def get_session_data_dir(session_id: str) -> Path:
    path = TEMP_DATA_DIR / session_id
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_df(session_id: str, df_type: str, df: pd.DataFrame):
    # Saves DF to parquet in session-specific dir
    filepath = get_session_data_dir(session_id) / f"{df_type}_df.parquet"
    try:
        df.to_parquet(filepath, index=False, engine='pyarrow')
        session[f'{df_type}_df_path'] = str(filepath) # Store path string
        app.logger.debug(f"Saved '{df_type}' DF (parquet) session {session_id} to {filepath}")
    except Exception as e:
        app.logger.error(f"Failed to save '{df_type}' parquet session {session_id} to {filepath}: {e}", exc_info=True)
        session.pop(f'{df_type}_df_path', None) # Remove path if save failed

def load_df(session_id: str, df_type: str) -> Optional[pd.DataFrame]:
    # Loads the WORKING df from parquet
    filepath_str = session.get(f'{df_type}_df_path');
    if not filepath_str:
        app.logger.warning(f"No path found for '{df_type}' DF session {session_id}")
        return None
    filepath = Path(filepath_str)
    if filepath.exists() and filepath.is_file():
        try:
            df = pd.read_parquet(filepath, engine='pyarrow')
            app.logger.debug(f"Loaded '{df_type}' DF (parquet) session {session_id} from {filepath} ({len(df)} rows)")
            return df
        except Exception as e:
            app.logger.error(f"Failed to load '{df_type}' parquet session {session_id} from {filepath}: {e}", exc_info=True)
            return None
    else:
        app.logger.warning(f"Parquet file not found for '{df_type}' DF session {session_id} at {filepath}")
        session.pop(f'{df_type}_df_path', None)
        return None

# Keep get_simple_schema_dict for viz validation
def get_simple_schema_dict(df: pd.DataFrame) -> Dict:
     if df is None: return {"columns": {}}
     return {"columns": {col: str(dtype) for col, dtype in df.dtypes.items()}}

def clean_session_data(session_id: str):
    # Clean parquet files
    data_dir = get_session_data_dir(session_id)
    if data_dir.exists():
        deleted_count = 0
        try:
            for item in data_dir.iterdir():
                if item.is_file() and item.name.endswith(('.parquet', '.tmp', '.upload')): # Clean parquet and potential temp uploads
                    os.remove(item)
                    deleted_count += 1
            if deleted_count > 0:
                app.logger.info(f"Removed {deleted_count} temp file(s) for session {session_id}")
        except Exception as e:
            app.logger.error(f"Error cleaning session data {session_id}: {e}", exc_info=True)
    # Note: Doesn't automatically clean PG tables, handled by DROP IF EXISTS on upload.

def clear_downstream_session_state(reason: str):
    """Clears session keys potentially invalidated by data modifications."""
    keys_to_clear = [
        'profile_report', 'ner_report', 'cleaning_suggestions',
        'feature_suggestions', 'llm_summary', 'generated_plots_metadata',
        'last_nl_query', 'last_query_result_raw', 'last_nl_answer',
        'last_query_error', 'last_generated_sql'
        # Keep pg_table_name, pg_schema_for_llm, dataframe_name, llm_config
    ]
    cleared = []
    for key in keys_to_clear:
        if session.pop(key, None) is not None:
            cleared.append(key)
    if cleared:
        app.logger.debug(f"Cleared downstream session state due to '{reason}': {cleared}")

# --- API Routes ---

@app.before_request
def ensure_session():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        app.logger.info(f"New session initialized: {session['session_id']}")
    app.logger.debug(f"Request: {request.method} {request.path} | Session: {session.get('session_id')}")


@app.route('/api/session', methods=['GET'])
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