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