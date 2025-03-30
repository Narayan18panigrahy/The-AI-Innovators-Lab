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