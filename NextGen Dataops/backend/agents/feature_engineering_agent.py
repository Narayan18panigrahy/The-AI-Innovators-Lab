                        else:
                            error_msg = f"Could not extract datetime part '{part}' from '{col}': Column is not datetime or could not be converted."
                    else:
                         error_msg = f"Missing details or column '{col}' not found for datetime extraction."

                elif code == 'polynomial_feature':
                    col = details.get('column')
                    degree = details.get('degree')
                    if col and degree and col in engineered_df.columns:
                         if pd.api.types.is_numeric_dtype(engineered_df[col]):
                              engineered_df[name] = engineered_df[col] ** degree
                              applied_msg = f"Applied '{code}': Created '{name}' as '{col}' to the power of {degree}."
                         else:
                              error_msg = f"Cannot apply polynomial: Column '{col}' is not numeric."
                    else:
                         error_msg = f"Missing details or column '{col}' not found for polynomial feature."

                elif code == 'interaction_feature':
                    cols = details.get('columns')
                    op = details.get('operation')
                    if cols and len(cols) == 2 and op and all(c in engineered_df.columns for c in cols):
                         col1, col2 = cols[0], cols[1]
                         # Check if columns are numeric
                         if not pd.api.types.is_numeric_dtype(engineered_df[col1]) or \
                            not pd.api.types.is_numeric_dtype(engineered_df[col2]):
                             error_msg = f"Cannot create interaction: Columns '{col1}', '{col2}' must both be numeric."
                         else:
                             if op == 'multiply':
                                  engineered_df[name] = engineered_df[col1] * engineered_df[col2]
                                  applied_msg = f"Applied '{code}': Created '{name}' as product of '{col1}' and '{col2}'."
                             elif op == 'divide':
                                  # Handle division by zero - replace with NaN or 0? Let's use NaN.
                                  engineered_df[name] = (engineered_df[col1] / engineered_df[col2].replace(0, np.nan))
                                  applied_msg = f"Applied '{code}': Created '{name}' as ratio of '{col1}' / '{col2}' (div by zero -> NaN)."
                             else:
                                  error_msg = f"Unsupported interaction operation: {op}"
                    else:
                         error_msg = f"Missing details, invalid column count/names for interaction feature."

                # --- Add other feature creation actions here ---
                # elif code == 'bin_numeric':
                #     # Implement binning logic (e.g., pd.qcut for quantiles, pd.cut for fixed bins)
                #     pass

                elif code: # If code exists but isn't handled
                     error_msg = f"Warning: Feature action code '{code}' not implemented yet."

                # Log results
                if applied_msg:
                    logs.append(applied_msg)
                    logger.info(applied_msg)
                elif error_msg:
                     # Log warnings as warnings, others as errors potentially
                     if error_msg.startswith("Warning:"):
                         logs.append(error_msg)
                         logger.warning(error_msg)
                     else:
                         logs.append(f"Error: {error_msg}")
                         logger.error(error_msg)

            except Exception as e:
                 error_msg = f"Failed to apply feature '{name}' (Code: {code}): {type(e).__name__} - {e}"
                 logs.append(f"Error: {error_msg}")
                 logger.error(error_msg, exc_info=True) # Log traceback for debugging
                 # Remove potentially partially created column on error
                 if name in engineered_df.columns:
                     try:
                         engineered_df.drop(columns=[name], inplace=True)
                         logger.debug(f"Removed partially created column '{name}' due to error.")
                     except Exception: pass # Ignore error during cleanup

        logger.info("Finished applying feature engineering steps.")
        return engineered_df, logs

    # --- (Optional) LLM Suggestion Helper ---
    # def _get_llm_feature_suggestions(self, dtypes, llm_config):
    #     # 1. Format dtypes/column names for prompt
    #     # 2. Construct prompt asking LLM for feature ideas based on columns/types
    #     # 3. Call litellm.completion
    #     # 4. Parse LLM response into the suggestion dictionary format
    #     # 5. Return list of suggestion dictionaries
    #     pass