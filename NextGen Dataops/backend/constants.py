# backend/constants.py

# -*- coding: utf-8 -*-
"""
constants.py

Backend application-wide constants for the NextGen DataOps tool.
"""

# --- LLM Provider Configuration ---
# Defines supported providers and credentials required by UI/backend logic
SUPPORTED_PROVIDERS = {
    "azure": {
        "api_key": "Azure API Key", # Key expected by openai lib when configured for Azure
        "api_base": "Azure API Base URL (Endpoint)", # Expected by openai lib
        "api_version": "Azure API Version" # Expected by openai lib
        # User provides Deployment Name as the 'model_name'
    },
    "nvidia": {
        "nvidia_api_key": "Nvidia API Key", # Key expected by llm_client logic
        "api_base": "Nvidia Base URL"
    }
}

# --- PostgreSQL Configuration ---
# Load these from environment variables for security in production
# For development, you can set defaults here or use a .env file with Flask
DB_HOST = "localhost" # or os.getenv("DB_HOST", "localhost")
DB_PORT = "5432" # Default PostgreSQL port
# For production, consider using os.getenv("DB_PORT", "5432") for flexibility
DB_NAME = "NextGen_DataOps_data" # Choose a database name
DB_USER = "admin" # Replace with your PG user
DB_PASSWORD = "Admin1234" # Replace with your PG password
DB_DEFAULT_SCHEMA_NAME = "public" # Or a dedicated schema if you prefer

# Default model name placeholder
DEFAULT_MODEL_NAME = ""

# --- Preprocessing Agent Defaults ---
DEFAULT_DBSCAN_EPS = 0.5
DEFAULT_DBSCAN_MIN_SAMPLES = 5

# --- File Handling ---
ALLOWED_FILE_EXTENSIONS = ["csv", "xlsx"]
# Max upload size (example: 100MB) - enforce in Flask config if needed
MAX_UPLOAD_MB = 500

# --- Reporting Agent ---
DEFAULT_REPORT_FILENAME = "data_profile_report.pdf"
DEFAULT_PLOT_FILENAME = "plot.png"
DEFAULT_QUERY_RESULTS_FILENAME = "query_results.csv"

# --- Session/Storage ---
# Base directory for temporary data storage
TEMP_DATA_DIR_NAME = "temp_data"
# Session cookie name (matches frontend expectations if needed)
SESSION_COOKIE_NAME = "nextgen_dataops_session_id"

# --- End of Constants ---