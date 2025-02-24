# -*- coding: utf-8 -*-
"""
feature_engineering_agent.py

Defines the FeatureEngineeringAgent class responsible for suggesting potential
new features based on existing columns and applying selected feature creation
steps to a DataFrame.
"""
import pandas as pd
import numpy as np
import itertools # For interaction terms
import logging # Import logging
# import traceback # No longer needed if using logger.error(exc_info=True)

# (Optional) LLM integration for suggestions
# import litellm

# Get a logger specific to this module
logger = logging.getLogger(__name__)

class FeatureEngineeringAgent:
    """
    Agent for suggesting and creating new features in a DataFrame.
    """

    def __init__(self):
        """Initializes the FeatureEngineeringAgent."""
        logger.debug("FeatureEngineeringAgent initialized.")
        pass

    # --- Suggestion Generation ---

    def suggest_features(self, df: pd.DataFrame) -> list[dict]:
        """
        Analyzes the DataFrame columns to suggest potential new features.

        Args:
            df (pd.DataFrame): The current working DataFrame.

        Returns:
            list[dict]: A list of suggested feature creation actions, each
                        represented as a dictionary with keys like 'name',
                        'description', 'action_code', 'details'.
        """
        if df is None or df.empty:
            logger.warning("Cannot suggest features: Input DataFrame is empty or None.")
            return []

        suggestions = []
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime', 'datetime64', 'datetime64[ns]']).columns.tolist()
        # Note: Object/string columns could also be used (e.g., length, word count), but start simple.

        logger.debug(f"Suggesting features based on: Numeric={numeric_cols}, Datetime={datetime_cols}")

        # --- Rule-Based Suggestions ---

        # 1. Datetime Feature Extraction
        for col in datetime_cols:
            suggestions.append({
                "name": f"{col}_year", "type": "Datetime Extraction",
                "description": f"Extract Year from '{col}'",
                "action_code": "extract_datetime", "details": {"column": col, "part": "year"}
            })
            suggestions.append({
                "name": f"{col}_month", "type": "Datetime Extraction",
                "description": f"Extract Month from '{col}'",
                "action_code": "extract_datetime", "details": {"column": col, "part": "month"}
            })
            suggestions.append({
                "name": f"{col}_day", "type": "Datetime Extraction",
                "description": f"Extract Day of Month from '{col}'",
                "action_code": "extract_datetime", "details": {"column": col, "part": "day"}
            })
            suggestions.append({
                "name": f"{col}_weekday", "type": "Datetime Extraction",
                "description": f"Extract Day of Week from '{col}' (0=Mon)",
                "action_code": "extract_datetime", "details": {"column": col, "part": "weekday"}
            })
            suggestions.append({
                "name": f"{col}_hour", "type": "Datetime Extraction",
                "description": f"Extract Hour from '{col}'",
                "action_code": "extract_datetime", "details": {"column": col, "part": "hour"}
            })
            # Add more extractions if needed (dayofyear, weekofyear, quarter)
            logger.debug(f"Added datetime extraction suggestions for column '{col}'.")

        # 2. Polynomial Features (for numeric columns)
        for col in numeric_cols:
            # Suggest square and cube terms as simple non-linear features
            suggestions.append({
                "name": f"{col}_sq", "type": "Polynomial",
                "description": f"Square of '{col}' ({col}^2)",
                "action_code": "polynomial_feature", "details": {"column": col, "degree": 2}
            })
            # suggestions.append({
            #     "name": f"{col}_cub", "type": "Polynomial",
            #     "description": f"Cube of '{col}' ({col}^3)",
            #     "action_code": "polynomial_feature", "details": {"column": col, "degree": 3}
            # }) # Cube might be less common, optional
            logger.debug(f"Added polynomial feature suggestions for column '{col}'.")

        # 3. Interaction Features (between pairs of numeric columns)
        # Limit combinations to avoid too many suggestions
        max_interaction_cols = 5 # Consider only first N numeric cols for pairwise interactions
        cols_for_interaction = numeric_cols[:max_interaction_cols]
        if len(cols_for_interaction) >= 2:
            for col1, col2 in itertools.combinations(cols_for_interaction, 2):
                 suggestions.append({
                    "name": f"{col1}_x_{col2}", "type": "Interaction",
                    "description": f"Product of '{col1}' and '{col2}'",
                    "action_code": "interaction_feature", "details": {"columns": [col1, col2], "operation": "multiply"}
                 })
                 # Optional: Add division/ratio interaction if meaningful
                 # suggestions.append({
                 #    "name": f"{col1}_div_{col2}", "type": "Interaction",
                 #    "description": f"Ratio of '{col1}' / '{col2}'",
                 #    "action_code": "interaction_feature", "details": {"columns": [col1, col2], "operation": "divide"}
                 # })
            logger.debug(f"Added interaction feature suggestions for columns: {cols_for_interaction}.")

        # 4. Binning/Discretization (for numeric columns)
        # Suggest binning for columns that aren't likely identifiers (e.g., based on cardinality?)
        # TODO: Implement suggestion for binning numeric columns (e.g., into quartiles or fixed bins)
        logger.debug("Binning suggestion generation is currently skipped (TODO).")


        # --- (Optional) LLM-Powered Suggestions ---
        # if use_llm_suggestions:
        #    try:
        #        # Format column names/types for prompt
        #        # Prompt LLM to suggest features based on column names and types
        #        llm_suggestions = self._get_llm_feature_suggestions(df.dtypes, llm_config)
        #        suggestions.extend(llm_suggestions)
        #    except Exception as e:
        #        logger.error(f"Could not get LLM-powered feature suggestions: {e}", exc_info=True)

        logger.info(f"Generated {len(suggestions)} feature suggestions.")
        return suggestions

    # --- Application of Feature Engineering Steps ---

    def apply_features(self, df: pd.DataFrame, selected_features: list[dict]) -> tuple[pd.DataFrame, list[str]]:
        """
        Applies the selected feature engineering actions to the DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame to add features to.
            selected_features (list[dict]): A list of feature suggestion dictionaries
                                             that the user chose to apply.

        Returns:
            tuple[pd.DataFrame, list[str]]: (dataframe_with_new_features, log_messages)
        """
        if df is None:
            logger.error("Cannot apply features: Input DataFrame is None.")
            return None, ["Error: Input DataFrame is None."]

        engineered_df = df.copy() # Work on a copy
        logs = []

        logger.info(f"Applying {len(selected_features)} selected feature engineering steps.")

        for feature in selected_features:
            name = feature.get('name')
            code = feature.get('action_code')
            details = feature.get('details', {})
            applied_msg = None
            error_msg = None

            # Prevent overwriting existing columns (maybe allow later with option?)
            if name in engineered_df.columns:
                 error_msg = f"Skipping feature '{name}': Column already exists."
                 logs.append(f"Warning: {error_msg}")
                 logger.warning(error_msg)
                 continue

            try:
                if code == 'extract_datetime':
                    col = details.get('column')
                    part = details.get('part')
                    if col and part and col in engineered_df.columns:
                        # Ensure column is datetime
                        if not pd.api.types.is_datetime64_any_dtype(engineered_df[col]):
                             logger.debug(f"Attempting to convert column '{col}' to datetime for feature '{name}'.")
                             engineered_df[col] = pd.to_datetime(engineered_df[col], errors='coerce') # Attempt conversion
                        # Check again after conversion attempt
                        if pd.api.types.is_datetime64_any_dtype(engineered_df[col]):
                             if part == 'year': engineered_df[name] = engineered_df[col].dt.year
                             elif part == 'month': engineered_df[name] = engineered_df[col].dt.month
                             elif part == 'day': engineered_df[name] = engineered_df[col].dt.day
                             elif part == 'weekday': engineered_df[name] = engineered_df[col].dt.weekday
                             elif part == 'hour': engineered_df[name] = engineered_df[col].dt.hour
                             # Add other parts as needed
                             else: raise ValueError(f"Unsupported datetime part: {part}")
                             # Fill NaNs potentially introduced by to_datetime(errors='coerce') or in original dt extraction
                             if engineered_df[name].isnull().any():
                                engineered_df[name].fillna(-1, inplace=True) # Fill with -1 or suitable placeholder
                                engineered_df[name] = engineered_df[name].astype(int) # Convert if possible
                             applied_msg = f"Applied '{code}': Extracted '{part}' from '{col}' into '{name}'."
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