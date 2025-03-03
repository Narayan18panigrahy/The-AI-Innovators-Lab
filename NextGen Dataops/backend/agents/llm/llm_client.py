# -*- coding: utf-8 -*-
"""
llm_client.py

Provides a unified interface to interact with Azure OpenAI (via openai sdk legacy config)
and Nvidia NIM (via openai sdk compatible API). Handles client initialization,
API calls, and error handling for these two providers using only the openai library.
"""


# import traceback # No longer needed with logger.error(exc_info=True)
import logging # Import logging
from typing import List, Dict, Tuple, Any, Optional

# --- SDK Import ---
# Only import the openai library
try:
    from openai import OpenAI,AzureOpenAI, AuthenticationError, BadRequestError, RateLimitError, APIConnectionError, NotFoundError
    OPENAI_AVAILABLE = True
except ImportError:
    # Log this critical error
    logging.critical("OpenAI library not installed. Run `pip install openai>=1.10.0`.")
    OpenAI = None # type: ignore
    AzureOpenAI = None # type: ignore
    AuthenticationError = None # type: ignore
    BadRequestError = None # type: ignore
    RateLimitError = None # type: ignore
    APIConnectionError = None # type: ignore
    NotFoundError = None # type: ignore
    OPENAI_AVAILABLE = False

# Get a logger specific to this module
logger = logging.getLogger(__name__)

# --- Constants ---
# Default Nvidia API base URL
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# --- Main Client Function ---
def execute_llm_completion(
    llm_config: Dict[str, Any],
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int
) -> Tuple[Optional[str], Optional[str]]:
    """
    Executes a chat completion call using the openai library configured for
    either Azure OpenAI or Nvidia NIM.

    Args:
        llm_config: Dictionary containing 'provider' (must be 'azure' or 'nvidia'),
                    'model_name', and 'credentials'.
        messages: The list of prompt messages.
        temperature: The desired temperature for the completion.
        max_tokens: The maximum number of tokens for the response.

    Returns:
        A tuple containing:
            - str | None: The response content string if successful, otherwise None.
            - str | None: An error message string if an error occurred, otherwise None.
    """
    provider: Optional[str] = llm_config.get("provider")
    model_name: Optional[str] = llm_config.get("model_name")
    credentials: Dict[str, Any] = llm_config.get("credentials", {})

    logger.info(f"Executing LLM completion via llm_client (openai lib). Provider: {provider}, Model: {model_name}")

    # --- Input Validation ---
    if not OPENAI_AVAILABLE:
        logger.critical("OpenAI library is required but not installed.")
        return None, "OpenAI library is required but not installed."
    if not provider or not model_name or not credentials:
         logger.error("LLM provider, model name, or credentials missing in configuration.")
         return None, "LLM provider, model name, or credentials missing in configuration."
    if provider not in ['azure', 'nvidia']:
        error_message = f"Unsupported LLM provider '{provider}'. This client only supports 'azure' and 'nvidia' via the OpenAI library."
        logger.error(error_message)
        return None, error_message

    client: Any = None
    response_content: Optional[str] = None
    error_message: Optional[str] = None
    model_to_use: str = ""

    try:
        # --- Provider Specific Configuration for OpenAI client ---

        if provider == 'azure':
            # Extract Azure credentials
            api_key = credentials.get('api_key') # Matches key from constants.py/UI
            azure_endpoint = credentials.get('api_base') # API Base URL from UI
            api_version = credentials.get('api_version')

            if not api_key or not azure_endpoint or not api_version:
                logger.error("Azure API Key, API Base URL (Endpoint), or API Version is missing in credentials.")
                return None, "Azure API Key, API Base URL (Endpoint), or API Version is missing in credentials."

            # Configure the OpenAI client FOR Azure
            client = AzureOpenAI(
                api_key=api_key,