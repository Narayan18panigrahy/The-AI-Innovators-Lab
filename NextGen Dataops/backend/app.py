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