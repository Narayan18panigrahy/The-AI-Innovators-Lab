# -*- coding: utf-8 -*-
"""
plotting_agent.py

Defines the PlottingAgent class responsible for generating visualizations
(using Seaborn/Matplotlib) based on structured parameters and data.
"""
import matplotlib
matplotlib.use('Agg')
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io # For saving plot to buffer
# import traceback # No longer needed with logger.error(exc_info=True)
import numpy as np # For handling potential inf/-inf
import logging # Import logging

# Get a logger specific to this module
logger = logging.getLogger(__name__)

class PlottingAgent:
    """
    Agent responsible for creating plots using Seaborn/Matplotlib
    based on structured parameters and a DataFrame.
    """

    def __init__(self):
        """Initializes the PlottingAgent."""
        sns.set_theme(style="whitegrid") # Set a default Seaborn theme
        logger.debug("PlottingAgent initialized with Seaborn theme 'whitegrid'.")

    def _validate_columns(self, df: pd.DataFrame, params: dict) -> str | None:
        """Check if required columns exist in the DataFrame."""
        required_cols = [params.get('x_col'), params.get('y_col'), params.get('color_col'), params.get('size_col')]
        error = None
        for col in required_cols:
            if col is not None and col not in df.columns:
                error = f"Column '{col}' specified for plotting not found in the DataFrame."
                logger.error(f"Validation Error: {error}. Available columns: {df.columns.tolist()}")
                return error
        logger.debug("Column validation successful for plotting.")
        return None # No error

    def _prepare_data_for_plot(self, df: pd.DataFrame, params: dict) -> tuple[pd.DataFrame | None, str | None]:
        """Handles aggregation and basic data preparation before plotting."""
        plot_type = params.get('plot_type')
        x_col = params.get('x_col')
        y_col = params.get('y_col')
        aggregation = params.get('aggregation')
        plot_df = df.copy() # Work on a copy
        logger.debug(f"Preparing data for plot type '{plot_type}' with aggregation '{aggregation}'.")

        # --- Aggregation Logic (primarily for bar/line plots) ---
        if aggregation and plot_type in ['bar', 'line']:
            logger.debug(f"Applying aggregation '{aggregation}' for x='{x_col}', y='{y_col}'.")
            if not x_col:
                err_msg = f"Aggregation ('{aggregation}') requires an 'x_col' for grouping."
                logger.error(err_msg)
                return None, err_msg
            if aggregation == 'count':
                # Count occurrences of x_col categories
                try:
                    agg_df = plot_df.groupby(x_col).size().reset_index(name='count')
                    # Rename 'count' to y_col if y_col was specified conceptually,
                    # or just use 'count' as the value column. Let's use 'count'.
                    params['y_col_agg'] = 'count' # Store the name of the aggregated column
                    logger.debug(f"Performed 'count' aggregation on '{x_col}'. Result shape: {agg_df.shape}")
                    return agg_df, None
                except Exception as e:
                    err_msg = f"Failed to perform 'count' aggregation on '{x_col}': {e}"
                    logger.error(err_msg, exc_info=True)
                    return None, err_msg
            elif y_col:
                # Aggregate y_col based on x_col groups
                if y_col not in plot_df.columns:
                     err_msg = f"Column '{y_col}' needed for aggregation '{aggregation}' not found."
                     logger.error(err_msg)
                     return None, err_msg
                if not pd.api.types.is_numeric_dtype(plot_df[y_col]):
                     # Attempt conversion? For now, require numeric.
                     # Check if conversion is feasible before erroring?
                     # Example: try: plot_df[y_col] = pd.to_numeric(plot_df[y_col], errors='raise'); except ValueError: ...
                     err_msg = f"Column '{y_col}' must be numeric for aggregation '{aggregation}'."
                     logger.error(err_msg)
                     return None, err_msg

                try:
                    # Replace infinite values before aggregation
                    if pd.api.types.is_numeric_dtype(plot_df[y_col]):
                        inf_count = np.isinf(plot_df[y_col]).sum()
                        if inf_count > 0:
                            logger.warning(f"Replacing {inf_count} infinite values in '{y_col}' with NaN before aggregation.")
                            plot_df[y_col] = plot_df[y_col].replace([np.inf, -np.inf], np.nan)

                    # Perform aggregation
                    logger.debug(f"Performing '{aggregation}' aggregation on '{y_col}' grouped by '{x_col}'.")
                    agg_df = plot_df.groupby(x_col)[y_col].agg(aggregation).reset_index()
                    # Rename the aggregated column to keep track
                    aggregated_col_name = f"{y_col}_{aggregation}"
                    agg_df.rename(columns={y_col: aggregated_col_name}, inplace=True)