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

            try:
                # Describe categorical/object columns
                object_cols = df.select_dtypes(include=['object', 'string', 'category']).columns
                if not object_cols.empty:
                    categorical_stats = df[object_cols].describe().to_dict() # Convert to dict
            except Exception as e:
                 logger.warning(f"Could not calculate categorical descriptive stats: {e}")

            profile_report['descriptive_stats'] = {
                "numeric": numeric_stats,
                "categorical": categorical_stats
            }

            # 5. Cardinality (Unique Values)
            logger.debug("Calculating cardinality...")
            try:
                profile_report['cardinality'] = df.nunique().astype(int).to_dict() # Convert to dict of ints
            except Exception as e:
                 logger.warning(f"Could not calculate cardinality: {e}")
                 profile_report['cardinality'] = {}


            # --- Numerical Analysis ---
            numeric_df = df.select_dtypes(include=np.number)
            if not numeric_df.empty:
                # 6. Correlation Matrix
                logger.debug("Calculating correlation matrix...")
                try:
                    # Only calculate if more than 1 numeric column
                    if len(numeric_df.columns) > 1:
                        profile_report['correlation_matrix'] = numeric_df.corr().round(3).to_dict()
                    else:
                         profile_report['correlation_matrix'] = None # Not applicable
                         logger.debug("Skipping correlation: <= 1 numeric column.")
                except Exception as e:
                    logger.warning(f"Could not calculate correlation matrix: {e}")
                    profile_report['correlation_matrix'] = None

                # 7. Skewness
                logger.debug("Calculating skewness...")
                try:
                    profile_report['skewness'] = numeric_df.skew().round(3).to_dict()
                except Exception as e:
                    logger.warning(f"Could not calculate skewness: {e}")
                    profile_report['skewness'] = None

                # 8. Kurtosis
                logger.debug("Calculating kurtosis...")
                try:
                    profile_report['kurtosis'] = numeric_df.kurt().round(3).to_dict()
                except Exception as e:
                    logger.warning(f"Could not calculate kurtosis: {e}")
                    profile_report['kurtosis'] = None

                # 9. Outlier Detection (DBSCAN)
                logger.debug("Performing DBSCAN outlier detection...")
                profile_report['outlier_detection'] = self._perform_dbscan(numeric_df, dbscan_params)

            else:
                # Handle case with no numeric columns
                logger.warning("No numeric columns found. Skipping Correlation, Skewness, Kurtosis, and DBSCAN Outlier Detection.")
                profile_report['correlation_matrix'] = None
                profile_report['skewness'] = None
                profile_report['kurtosis'] = None
                profile_report['outlier_detection'] = {
                    "method": "DBSCAN",
                    "error": "No numeric columns found in the dataset."
                }

            # --- (Optional Additions Section - can be added later) ---
            # - Value Distribution for low-cardinality categoricals
            # - Zero/Negative checks for specific numeric columns

            logger.info("Profiling complete.")
            return profile_report

        except Exception as e:
            logger.error(f"An unexpected error occurred during profiling: {e}", exc_info=True)
            # Return None or empty dict based on how critical the error is
            # Returning None indicates a more severe failure
            return None # Indicate a significant failure in profiling

    def _get_memory_usage(self, df: pd.DataFrame) -> str:
        """Calculates and formats memory usage."""
        try:
            mem = df.memory_usage(index=True, deep=True).sum()
            if mem < 1024:
                return f"{mem} Bytes"
            elif mem < 1024**2:
                return f"{mem/1024:.2f} KB"
            elif mem < 1024**3:
                return f"{mem/1024**2:.2f} MB"
            else:
                return f"{mem/1024**3:.2f} GB"
        except Exception as e:
            logger.warning(f"Could not calculate memory usage: {e}")
            return "N/A" # Handle potential errors in memory calculation

    def _perform_dbscan(self, numeric_df: pd.DataFrame, params: dict) -> dict:
        """
        Performs DBSCAN clustering on numeric columns to identify outliers.

        Args:
            numeric_df (pd.DataFrame): DataFrame containing only numeric columns.
            params (dict): Dictionary with 'eps' and 'min_samples'.

        Returns:
            dict: Results including outlier count, percentage, and parameters used.
                  Includes an 'error' key if DBSCAN fails.
        """
        results = {
            "method": "DBSCAN",
            "parameters": params,
            "outlier_count": 0,
            "outlier_percentage": 0.0,
            "rows_analyzed": 0,
            "rows_dropped_nan": 0,
            "error": None
        }
        logger.debug(f"Starting DBSCAN with params: {params}")

        if numeric_df.empty:
            results["error"] = "Input numeric DataFrame is empty."
            logger.warning("DBSCAN skipped: Input numeric DataFrame is empty.")
            return results

        original_count = len(numeric_df)
        # Drop rows with any NaN in the numeric columns being considered
        numeric_df_clean = numeric_df.dropna()
        dropped_count = original_count - len(numeric_df_clean)
        if dropped_count > 0:
             logger.info(f"DBSCAN: Dropped {dropped_count} rows with NaN values in numeric columns before clustering.")

        if len(numeric_df_clean) < params.get('min_samples', 5):
            results["error"] = f"Not enough non-NaN data points ({len(numeric_df_clean)}) for DBSCAN min_samples ({params.get('min_samples', 5)})."
            logger.warning(f"DBSCAN skipped: {results['error']}")
            return results

        try:
            # 1. Scale the data
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(numeric_df_clean)
            logger.debug(f"DBSCAN: Scaled data shape: {scaled_data.shape}")

            # 2. Apply DBSCAN
            dbscan = DBSCAN(eps=params.get('eps', 0.5), min_samples=params.get('min_samples', 5))
            clusters = dbscan.fit_predict(scaled_data)
            logger.debug(f"DBSCAN: Cluster labels generated (first 10): {clusters[:10]}")

            # 3. Identify outliers (cluster label -1)
            outlier_indices_clean = np.where(clusters == -1)[0] # Indices within the cleaned df
            outlier_count = len(outlier_indices_clean)

            # Map back to original DataFrame indices if needed (more complex, skip for now)
            # outlier_original_indices = numeric_df_clean.index[outlier_indices_clean]

            total_rows_analyzed = len(numeric_df_clean) # Base percentage on non-NaN rows
            outlier_percentage = (outlier_count / total_rows_analyzed) * 100 if total_rows_analyzed > 0 else 0

            results.update({
                "outlier_count": outlier_count,
                "outlier_percentage": round(outlier_percentage, 2),
                "rows_analyzed": total_rows_analyzed, # Number of rows used after dropping NaNs
                "rows_dropped_nan": dropped_count,
                "error": None
            })
            logger.info(f"DBSCAN found {outlier_count} potential outliers.")

        except ValueError as ve:
             # Common error if eps is too small or data has issues
             results["error"] = f"ValueError during DBSCAN (check parameters/data): {ve}"
             logger.error(f"DBSCAN Error: {results['error']}")
        except Exception as e:
            error_msg = f"An unexpected error occurred during DBSCAN: {e}"
            results["error"] = error_msg
            logger.error(error_msg, exc_info=True)

        return results