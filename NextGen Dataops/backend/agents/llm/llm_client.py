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
                azure_endpoint=azure_endpoint, # Use azure_endpoint for base_url
                api_version=api_version,
                # Azure credentials type is implicitly handled by passing these specific args
            )
            # Model for Azure is the DEPLOYMENT NAME (remove potential 'azure/' prefix)
            model_to_use = model_name.split('/')[-1] if '/' in model_name else model_name
            logger.info(f"Configured OpenAI client for Azure. Endpoint: {azure_endpoint}, Version: {api_version}, Deployment: {model_to_use}")


        elif provider == 'nvidia':
            # Extract Nvidia credentials
            api_key = credentials.get('nvidia_api_key')
            # Allow overriding base URL via credentials if needed, otherwise use default
            base_url = credentials.get('api_base', NVIDIA_BASE_URL)

            if not api_key:
                logger.error("Nvidia API Key is missing in credentials.")
                return None, "Nvidia API Key is missing in credentials."

            # Configure the OpenAI client FOR Nvidia
            client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            # Model for Nvidia is the full model identifier string
            model_to_use = model_name
            logger.info(f"Configured OpenAI client for Nvidia. Base URL: {base_url}, Model: {model_to_use}")


        # --- Execute the API Call (Common for both using OpenAI client) ---
        if client and model_to_use:
            logger.info(f"Calling client.chat.completions.create for {provider}. Model: {model_to_use}")
            response = client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                # Add other common parameters here if needed
                # top_p=llm_config.get('top_p', 1.0)
            )
            response_content = response.choices[0].message.content
            logger.info(f"LLM call successful via llm_client for {provider}.")
            return response_content, None # Success
        else:
            # This case should not be reached if validation above is correct
             logger.error("Client or model configuration failed unexpectedly.")
             return None, "Client or model configuration failed unexpectedly."


    # --- Centralized Exception Handling (Using OpenAI library exceptions) ---
    except AuthenticationError as e:
         error_message = f"LLM Auth Error ({provider}): Check API Key/Credentials. Details: {e}"
    except BadRequestError as e:
         error_message = f"LLM Bad Request ({provider}) - Check Model ('{model_to_use}')/Params. Details: {e}"
    except RateLimitError as e:
         error_message = f"LLM Rate Limit ({provider}). Wait & retry. Details: {e}"
    except APIConnectionError as e:
          error_message = f"LLM Connection Error ({provider}): Check Endpoint/Network ({client.base_url if client else 'N/A'}). Details: {e}"
    except NotFoundError as e: # Catches 404 errors, often invalid model or endpoint
         error_message = f"LLM Not Found Error ({provider}): Check Model Name ('{model_to_use}')/Endpoint ({client.base_url if client else 'N/A'}). Details: {e}"
    except Exception as e: # Catch any other unexpected error
        error_message = f"Unexpected error in llm_client ({provider}): {type(e).__name__}"
        # Log the error with traceback
        logger.error(f"{error_message}: {e}", exc_info=True)
        return None, error_message # Return None content and the error message

    # If an error occurred and was caught, error_message will be set
    if error_message:
        logger.error(error_message) # Log the specific error message
        return None, error_message
    else:
        # Fallback if logic is flawed (should not happen ideally)
        logger.warning("LLM client reached end of execution without returning content or error.")
        return response_content, None