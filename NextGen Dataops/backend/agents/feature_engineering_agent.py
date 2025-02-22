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