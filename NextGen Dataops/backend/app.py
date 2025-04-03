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