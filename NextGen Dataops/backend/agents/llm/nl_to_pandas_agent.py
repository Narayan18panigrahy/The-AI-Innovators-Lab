            validated_code, validation_error = self._parse_and_validate_code(raw_code)
            if validation_error:
                logger.error(f"Generated Pandas code failed validation: {validation_error}")
                return None, validation_error # Return specific parsing/validation error
            else:
                logger.info("Pandas code generated and validated successfully.")
                return validated_code, None # Success
        else:
            # Should ideally be caught by error handling in client, but as fallback:
            logger.warning("LLM client returned empty content without specific error.")
            return None, "LLM client returned empty content without specific error."