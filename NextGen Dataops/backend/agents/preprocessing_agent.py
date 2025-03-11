# -*- coding: utf-8 -*-
"""
preprocessing_agent.py

Defines the PreprocessingAgent class responsible for analyzing a DataFrame's
structure, content, identifying potential outliers using DBSCAN, and generating
a structured profiling report.
"""

import pandas as pd
import numpy as np
import logging # Import logging
# import traceback # No longer needed with logger.error(exc_info=True)
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

# (Optional) Import data models if defining a strict report structure
# from core.data_models import ProfilingReport  # Example if using Pydantic

# Get a logger specific to this module
logger = logging.getLogger(__name__)

class PreprocessingAgent:
    """
    Agent responsible for profiling the DataFrame and detecting outliers.
    Does not modify the original DataFrame.
    """

    def __init__(self):
        """Initializes the PreprocessingAgent."""
        # No specific state needed for this agent currently
        logger.debug("PreprocessingAgent initialized.")
        pass

    def profile(self, df: pd.DataFrame, dbscan_params: dict) -> dict:
        """
        Performs data profiling and outlier detection on the DataFrame.

        Args:
            df (pd.DataFrame): The input DataFrame to profile.
            dbscan_params (dict): Dictionary containing 'eps' and 'min_samples'
                                  for DBSCAN outlier detection.

        Returns:
            dict: A structured dictionary containing the profiling results,
                  or an empty dict if profiling fails. Returns None on critical error.
        """
        if df is None or not isinstance(df, pd.DataFrame):
            logger.error("Profiling Error: Input is not a valid DataFrame.")
            return None # Indicate critical failure
        if df.empty:
            logger.warning("Profiling Warning: Input DataFrame is empty.")
            # Return a minimal report for an empty DataFrame
            return {
                "basic_info": {"rows": 0, "columns": 0, "duplicates": 0, "memory_usage": "0 Bytes"},
                "data_types": {}, "missing_values": {}, "descriptive_stats": {},
                "cardinality": {}, "correlation_matrix": None, "skewness": None,
                "kurtosis": None, "outlier_detection": {"method": "DBSCAN", "error": "DataFrame is empty"}
            }

        logger.info("Starting DataFrame profiling...")
        profile_report = {}

        try:
            # 1. Basic Info
            logger.debug("Calculating basic info...")
            profile_report['basic_info'] = {
                "rows": len(df),
                "columns": len(df.columns),
                "duplicates": int(df.duplicated().sum()), # Ensure standard int type
                # Get memory usage string (more informative than just bytes)
                "memory_usage": self._get_memory_usage(df)
            }

            # 2. Data Types
            logger.debug("Identifying data types...")
            # Convert dtypes to string representation for JSON compatibility if needed later
            profile_report['data_types'] = {col: str(dtype) for col, dtype in df.dtypes.items()}

            # 3. Missing Values
            logger.debug("Calculating missing values...")
            missing_counts = df.isnull().sum()
            missing_percentages = (missing_counts / len(df)) * 100 if len(df) > 0 else missing_counts * 0
            profile_report['missing_values'] = {
                col: {"count": int(count), "percentage": round(percentage, 2)}
                for col, count, percentage in zip(missing_counts.index, missing_counts.values, missing_percentages.values)
            }

            # 4. Descriptive Statistics
            logger.debug("Calculating descriptive statistics...")
            numeric_stats = None
            categorical_stats = None
            try:
                # Describe numeric columns
                numeric_cols = df.select_dtypes(include=np.number).columns
                if not numeric_cols.empty:
                    numeric_stats = df[numeric_cols].describe().round(3).to_dict() # Convert to dict
            except Exception as e:
                 logger.warning(f"Could not calculate numeric descriptive stats: {e}")
