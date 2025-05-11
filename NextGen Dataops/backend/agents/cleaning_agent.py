# -*- coding: utf-8 -*-
"""
cleaning_agent.py

Defines the CleaningAgent class responsible for suggesting data cleaning steps
based on a profiling report and applying selected steps to a DataFrame.
"""

import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer # For imputation strategies
import logging # Import the logging library

# (Optional) LLM integration for suggestions (more advanced)
# import litellm

# Get a logger specific to this module
logger = logging.getLogger(__name__)

class CleaningAgent:
    """
    Agent for suggesting and applying data cleaning operations.
    """

    def __init__(self):
        """Initializes the CleaningAgent."""
        logger.debug("CleaningAgent initialized.")
        pass # No specific state needed currently

    # --- Suggestion Generation ---

    def suggest_cleaning_steps(self, profile_report: dict, df: pd.DataFrame) -> list[dict]:
        """
        Analyzes the profiling report and DataFrame to suggest cleaning steps.

        Args:
            profile_report (dict): The profiling report from PreprocessingAgent.
            df (pd.DataFrame): The current working DataFrame.

        Returns:
            list[dict]: A list of suggested cleaning actions, each represented
                        as a dictionary with keys like 'column', 'issue',
                        'suggestion', 'action_code', 'details'.
        """
        if not profile_report or df is None:
            logger.warning("Cleaning suggestions require a valid profile report and DataFrame.")
            return []

        suggestions = []
        missing_values = profile_report.get('missing_values', {})
        data_types = profile_report.get('data_types', {})
        basic_info = profile_report.get('basic_info', {})
        outlier_info = profile_report.get('outlier_detection', {})

        logger.debug("Starting rule-based cleaning suggestion generation.")

        # --- Rule-Based Suggestions ---

        # 1. Handling Missing Values
        for col, data in missing_values.items():
            missing_perc = data.get('percentage', 0)
            missing_count = data.get('count', 0)
            col_dtype = data_types.get(col)

            if missing_count > 0:
                logger.debug(f"Analyzing missing values for column '{col}' ({missing_perc:.1f}% missing).")
                # Suggest dropping columns with very high missing %
                if missing_perc > 90: # Threshold: > 90% missing
                    suggestions.append({
                        "column": col, "issue": f"{missing_perc:.1f}% Missing",
                        "suggestion": "Drop Column (Very High Missing %)",
                        "action_code": "drop_column", "details": {}
                    })
                    logger.debug(f"Suggesting drop_column for '{col}' due to >90% missing values.")
                # Suggest imputation for numeric columns with moderate missing %
                elif 'int' in col_dtype or 'float' in col_dtype:
                    if missing_perc < 30: # Threshold: < 30% missing for imputation
                        suggestions.append({
                            "column": col, "issue": f"{missing_perc:.1f}% Missing",
                            "suggestion": "Impute with Median",
                            "action_code": "impute_median", "details": {}
                        })
                        suggestions.append({
                            "column": col, "issue": f"{missing_perc:.1f}% Missing",
                            "suggestion": "Impute with Mean",
                            "action_code": "impute_mean", "details": {}
                        })
                        logger.debug(f"Suggesting impute_median/mean for numeric column '{col}' (<30% missing).")
                    else: # Higher missing % might still warrant dropping or advanced imputation
                         suggestions.append({
                            "column": col, "issue": f"{missing_perc:.1f}% Missing",
                            "suggestion": "Drop Column (High Missing %)",
                            "action_code": "drop_column", "details": {}
                         })
                         logger.debug(f"Suggesting drop_column for numeric column '{col}' (>=30% missing).")

                # Suggest imputation for categorical columns with moderate missing %
                elif 'object' in col_dtype or 'string' in col_dtype or 'category' in col_dtype:
                     if missing_perc < 30:
                         suggestions.append({
                            "column": col, "issue": f"{missing_perc:.1f}% Missing",
                            "suggestion": "Impute with Mode (Most Frequent)",
                            "action_code": "impute_mode", "details": {}
                         })
                         suggestions.append({
                            "column": col, "issue": f"{missing_perc:.1f}% Missing",
                            "suggestion": "Impute with Constant 'Missing'",
                            "action_code": "impute_constant", "details": {"fill_value": "Missing"}
                         })
                         logger.debug(f"Suggesting impute_mode/constant for categorical column '{col}' (<30% missing).")
                     else:
                          suggestions.append({
                            "column": col, "issue": f"{missing_perc:.1f}% Missing",
                            "suggestion": "Drop Column (High Missing %)",
                            "action_code": "drop_column", "details": {}
                          })
                          logger.debug(f"Suggesting drop_column for categorical column '{col}' (>=30% missing).")

        # 2. Handling Duplicate Rows
        duplicate_count = basic_info.get('duplicates', 0)
        if duplicate_count > 0:
            suggestions.append({
                "column": "ALL", # Apply to whole DataFrame
                "issue": f"{duplicate_count:,} Duplicate Rows",
                "suggestion": "Remove Duplicate Rows",
                "action_code": "remove_duplicates", "details": {}
            })
            logger.debug(f"Suggesting remove_duplicates for {duplicate_count} duplicate rows.")

        # 3. Handling Outliers (Based on DBSCAN report) - Suggesting removal is simple
        #    More advanced: suggest capping, transformation. For now, suggest removal.
        if outlier_info and outlier_info.get("outlier_count", 0) > 0 and not outlier_info.get("error"):
             logger.debug(f"Outliers detected ({outlier_info.get('outlier_count', 0)}), but automatic removal suggestion based on DBSCAN is currently skipped.")
             # Note: DBSCAN flags rows, not specific columns. Applying removal removes the whole row.
             # Also, DBSCAN was run only on numeric columns after dropping NaNs there.
             # This suggestion is complex to apply perfectly without outlier indices.
             # Let's skip suggesting automatic outlier removal based on DBSCAN for now,
             # as it requires storing and using the outlier indices which we didn't implement.
             # A simpler rule could be IQR-based outlier suggestion per column.
             # TODO: Implement IQR or Z-score based outlier suggestions per numeric column.
             pass # Placeholder for future outlier handling suggestions


        # 4. Mixed Data Types (Requires more sophisticated detection in profiling)
        # TODO: Add profiling check for mixed types within a column.
        # If mixed types found (e.g., numbers and strings in same column):
        # suggestions.append({"column": col, "issue": "Mixed Data Types", "suggestion": "Convert to String / Attempt Numeric Conversion", "action_code": "convert_dtype", "details": {"target_type": "string"}})
        logger.debug("Mixed data type suggestion generation is currently skipped (TODO).")

        # 5. High Cardinality Categoricals (Suggest grouping less frequent)
        # TODO: Implement suggestion for grouping less frequent categories.
        logger.debug("High cardinality suggestion generation is currently skipped (TODO).")

        # --- (Optional) LLM-Powered Suggestions ---
        # This would involve formatting the profile summary and prompting an LLM
        # Example placeholder:
        # if use_llm_suggestions:
        #    try:
        #        llm_suggestions = self._get_llm_cleaning_suggestions(profile_report, llm_config)
        #        suggestions.extend(llm_suggestions) # Assuming LLM returns suggestions in the same format
        #    except Exception as e:
        #        logger.error(f"Could not get LLM-powered cleaning suggestions: {e}", exc_info=True)

        logger.info(f"Generated {len(suggestions)} cleaning suggestions.")
        return suggestions

    # --- Application of Cleaning Steps ---

    def apply_cleaning_steps(self, df: pd.DataFrame, selected_actions: list[dict]) -> tuple[pd.DataFrame, list[str]]:
        """
        Applies the selected cleaning actions to the DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame to clean.
            selected_actions (list[dict]): A list of suggestion dictionaries
                                            that the user chose to apply.

        Returns:
            tuple[pd.DataFrame, list[str]]: (cleaned_dataframe, log_messages)
        """
        if df is None:
            logger.error("Cannot apply cleaning steps: Input DataFrame is None.")
            return None, ["Error: Input DataFrame is None."]

        cleaned_df = df.copy() # Work on a copy
        logs = []
        applied_codes_for_col = {} # Track actions applied per column

        logger.info(f"Applying {len(selected_actions)} selected cleaning actions.")

        # --- Apply Actions Systematically ---
        # Apply row-level actions first (like remove duplicates)
        if any(action['action_code'] == 'remove_duplicates' for action in selected_actions):
            initial_rows = len(cleaned_df)
            cleaned_df.drop_duplicates(inplace=True)
            rows_removed = initial_rows - len(cleaned_df)
            if rows_removed > 0:
                log_msg = f"Applied 'remove_duplicates': Removed {rows_removed:,} duplicate rows."
                logs.append(log_msg)
                logger.info(log_msg)
            else:
                log_msg = "Applied 'remove_duplicates': No duplicate rows found to remove."
                logs.append(log_msg)
                logger.info(log_msg)
            # Remove this action from the list so it's not processed again
            selected_actions = [a for a in selected_actions if a['action_code'] != 'remove_duplicates']


        # Apply column dropping actions next
        cols_to_drop = set()
        actions_remaining = []
        for action in selected_actions:
            if action['action_code'] == 'drop_column':
                col = action.get('column')
                if col and col not in cols_to_drop:
                    cols_to_drop.add(col)
                    log_msg = f"Marked column '{col}' for dropping due to '{action.get('issue', 'N/A')}'."
                    logs.append(log_msg)
                    logger.debug(log_msg)
                # Don't add this action to remaining list
            else:
                actions_remaining.append(action)
        selected_actions = actions_remaining

        if cols_to_drop:
            try:
                cleaned_df.drop(columns=list(cols_to_drop), inplace=True)
                log_msg = f"Dropped columns: {list(cols_to_drop)}"
                logs.append(log_msg)
                logger.info(log_msg)
            except KeyError as e:
                 log_msg = f"Warning: Could not drop columns - {e}. They might have been dropped already."
                 logs.append(log_msg)
                 logger.warning(log_msg)
            except Exception as e:
                 log_msg = f"Error during column dropping: {e}"
                 logs.append(log_msg)
                 logger.error(log_msg, exc_info=True)

        # Apply remaining column-level actions (imputation, type conversion etc.)
        for action in selected_actions:
            col = action.get('column')
            code = action.get('action_code')
            details = action.get('details', {})

            # Check if column still exists (might have been dropped)
            if col not in cleaned_df.columns:
                 log_msg = f"Skipping action '{code}' for column '{col}': Column no longer exists."
                 logs.append(log_msg)
                 logger.warning(log_msg)
                 continue

            # --- Imputation ---
            imputer = None
            fill_val = None
            strategy = None
            applied_msg = None

            try:
                if code == 'impute_median':
                    imputer = SimpleImputer(strategy='median')
                    strategy = 'median'
                elif code == 'impute_mean':
                    imputer = SimpleImputer(strategy='mean')
                    strategy = 'mean'
                elif code == 'impute_mode':
                     # SimpleImputer strategy='most_frequent' handles mode for categorical/numeric
                    imputer = SimpleImputer(strategy='most_frequent')
                    strategy = 'mode (most frequent)'
                elif code == 'impute_constant':
                    fill_val = details.get('fill_value', 'Unknown') # Get constant value
                    imputer = SimpleImputer(strategy='constant', fill_value=fill_val)
                    strategy = f'constant ({fill_val})'

                if imputer:
                    # Check if imputation already applied with different strategy for this column
                    prev_action = applied_codes_for_col.get(col)
                    if prev_action and prev_action.startswith("impute"):
                         log_msg = f"Skipping '{code}' for '{col}': Imputation '{prev_action}' already applied."
                         logs.append(log_msg); logger.warning(log_msg); continue

                    # Fit and transform
                    # Reshape needed as SimpleImputer expects 2D array
                    logger.debug(f"Applying imputation '{code}' (strategy: {strategy}) to column '{col}'.")
                    cleaned_df[col] = imputer.fit_transform(cleaned_df[[col]])
                    applied_msg = f"Applied '{code}': Imputed missing values in '{col}' with {strategy}."
                    applied_codes_for_col[col] = code # Mark imputation as done for this column

                # --- Add other actions here ---
                # elif code == 'convert_dtype':
                #     target_type = details.get('target_type', 'string')
                #     try:
                #         logger.debug(f"Applying type conversion '{code}' to column '{col}' (target: {target_type}).")
                #         cleaned_df[col] = cleaned_df[col].astype(target_type)
                #         applied_msg = f"Applied '{code}': Converted column '{col}' to {target_type}."
                #         applied_codes_for_col[col] = code
                #     except Exception as type_err:
                #          log_msg = f"Error converting '{col}' to {target_type}: {type_err}"
                #          logs.append(log_msg); logger.error(log_msg); continue

                elif code: # If code exists but isn't handled
                     log_msg = f"Warning: Action code '{code}' not implemented yet."
                     logs.append(log_msg); logger.warning(log_msg); continue


                if applied_msg:
                     logs.append(applied_msg)
                     logger.info(applied_msg)

            except Exception as e:
                 error_msg = f"Error applying action '{code}' to column '{col}': {e}"
                 logs.append(error_msg)
                 logger.error(error_msg, exc_info=True) # Log traceback for debugging

        logger.info("Finished applying cleaning steps.")
        return cleaned_df, logs

    # --- (Optional) LLM Suggestion Helper ---
    # def _get_llm_cleaning_suggestions(self, profile_report, llm_config):
    #     # 1. Format profile_report summary for prompt
    #     # 2. Construct prompt asking LLM for cleaning suggestions in specific format
    #     # 3. Call litellm.completion
    #     # 4. Parse LLM response (likely JSON) into the suggestion dictionary format
    #     # 5. Return list of suggestion dictionaries
    #     pass