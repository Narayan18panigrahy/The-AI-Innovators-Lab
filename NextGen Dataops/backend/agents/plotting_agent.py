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
                    params['y_col_agg'] = aggregated_col_name # Store the name of the aggregated column
                    logger.debug(f"Aggregation result columns: {agg_df.columns.tolist()}. Result shape: {agg_df.shape}")
                    return agg_df, None
                except KeyError:
                     err_msg = f"Aggregation function '{aggregation}' not recognized by pandas."
                     logger.error(err_msg)
                     return None, err_msg
                except Exception as e:
                     err_msg = f"Failed to aggregate '{y_col}' by '{x_col}' using '{aggregation}': {e}"
                     logger.error(err_msg, exc_info=True)
                     return None, err_msg
            else:
                err_msg = f"Aggregation '{aggregation}' requires a 'y_col' to aggregate (unless aggregation is 'count')."
                logger.error(err_msg)
                return None, err_msg
        else:
             # No aggregation needed or applicable for this plot type
             logger.debug("No aggregation applied.")
             return plot_df, None # Return the original (copied) df

    def generate_plot(self, params: dict, df: pd.DataFrame) -> tuple[plt.Figure | None, bytes | None, str | None]:
        """
        Generates a plot based on the parameters and data.

        Args:
            params (dict): Dictionary of plot parameters from NLtoVizAgent.
            df (pd.DataFrame): The DataFrame to plot (usually working_df).

        Returns:
            tuple[plt.Figure | None, bytes | None, str | None]:
                (matplotlib_figure, png_bytes, error_message)
        """
        if df is None or df.empty:
            logger.error("Plot generation failed: Input DataFrame is empty or None.")
            return None, None, "Input DataFrame is empty or None."
        if not params or 'plot_type' not in params:
            logger.error("Plot generation failed: Invalid or missing plot parameters.")
            return None, None, "Invalid or missing plot parameters."

        plot_type = params.get('plot_type')
        logger.info(f"Attempting to generate plot type: '{plot_type}' with params: {params}")

        # --- Validate Columns ---
        validation_error = self._validate_columns(df, params)
        if validation_error:
            # Error already logged by _validate_columns
            return None, None, validation_error

        # --- Prepare Data (Aggregation) ---
        plot_df, prep_error = self._prepare_data_for_plot(df, params)
        if prep_error:
            # Error already logged by _prepare_data_for_plot
            return None, None, f"Data preparation error: {prep_error}"
        if plot_df is None or plot_df.empty:
            logger.error("Plot generation failed: Data became empty after preparation/aggregation.")
            return None, None, "Data became empty after preparation/aggregation."

        # Determine actual columns to use after potential aggregation
        x_col = params.get('x_col')
        # If aggregation happened, y_col might now be the aggregated column name
        y_col = params.get('y_col_agg') if params.get('y_col_agg') else params.get('y_col')
        color_col = params.get('color_col')
        size_col = params.get('size_col') # Note: Aggregation usually loses original color/size cols
        logger.debug(f"Plotting with columns: x='{x_col}', y='{y_col}', color='{color_col}', size='{size_col}'")

        fig, ax = plt.subplots(figsize=(10, 6)) # Create figure and axes

        try:
            # --- Plotting Logic based on plot_type ---
            plot_title = f"{plot_type.capitalize()} Plot" # Default title

            if plot_type == 'scatter':
                if not x_col or not y_col: raise ValueError("Scatter plot requires both x_col and y_col.")
                logger.debug(f"Generating scatter plot: x='{x_col}', y='{y_col}', hue='{color_col}', size='{size_col}'")
                sns.scatterplot(data=plot_df, x=x_col, y=y_col, hue=color_col, size=size_col, ax=ax, legend="auto")
                plot_title = f"Scatter Plot of {y_col} vs {x_col}" + (f" by {color_col}" if color_col else "")

            elif plot_type == 'histogram':
                if not x_col: raise ValueError("Histogram requires x_col.")
                logger.debug(f"Generating histogram: x='{x_col}', hue='{color_col}'")
                sns.histplot(data=plot_df, x=x_col, hue=color_col, kde=True, ax=ax) # Add KDE for smoothness
                plot_title = f"Distribution of {x_col}" + (f" by {color_col}" if color_col else "")

            elif plot_type == 'bar':
                if not x_col or not y_col: raise ValueError("Bar plot requires x_col and a value column (y_col or aggregated).")
                logger.debug(f"Generating bar plot: x='{x_col}', y='{y_col}', hue='{color_col}'")
                # Ensure x_col is treated as categorical for ordering if necessary
                # plot_df[x_col] = plot_df[x_col].astype('category') # Optional: might affect order
                sns.barplot(data=plot_df, x=x_col, y=y_col, hue=color_col, ax=ax, errorbar=None) # Use aggregated data
                plt.xticks(rotation=45, ha='right')
                plot_title = f"Bar Chart: {y_col} by {x_col}" + (f" colored by {color_col}" if color_col else "")

            elif plot_type == 'line':
                 if not x_col or not y_col: raise ValueError("Line plot requires both x_col and y_col.")
                 logger.debug(f"Generating line plot: x='{x_col}', y='{y_col}', hue='{color_col}'")
                 # Consider sorting by x_col if it's numeric/datetime for sensible line
                 if pd.api.types.is_numeric_dtype(plot_df[x_col]) or pd.api.types.is_datetime64_any_dtype(plot_df[x_col]):
                     logger.debug(f"Sorting data by '{x_col}' for line plot.")
                     plot_df = plot_df.sort_values(by=x_col)
                 sns.lineplot(data=plot_df, x=x_col, y=y_col, hue=color_col, marker='o', ax=ax, legend="auto") # Add markers
                 plt.xticks(rotation=45, ha='right')
                 plot_title = f"Line Plot of {y_col} over {x_col}" + (f" by {color_col}" if color_col else "")

            elif plot_type == 'box':
                 # Box plot typically needs categorical x and numeric y
                 if not x_col: raise ValueError("Box plot requires x_col (category).")
                 if y_col and not pd.api.types.is_numeric_dtype(plot_df[y_col]):
                      raise ValueError(f"y_col ('{y_col}') must be numeric for Box plot.")
                 logger.debug(f"Generating box plot: x='{x_col}', y='{y_col}', hue='{color_col}'")
                 sns.boxplot(data=plot_df, x=x_col, y=y_col, hue=color_col, ax=ax)
                 plt.xticks(rotation=45, ha='right')
                 plot_title = f"Box Plot of {y_col if y_col else x_col}" + (f" by {x_col}" if y_col else "") + (f" grouped by {color_col}" if color_col else "")


            elif plot_type == 'heatmap':
                # Heatmap usually requires data in a matrix format (e.g., correlation matrix)
                # This agent expects parameters like 'x_col', 'y_col'. Generating a heatmap
                # from raw data based on NL is complex. We'll assume the user provided
                # a correlation matrix or pivot table results if they ask for a heatmap.
                # For now, let's handle the simple case where the data *is* the matrix.
                # This might need refinement based on how NL-to-Viz handles heatmap requests.
                # A more robust approach might involve pivoting data here based on params.
                logger.debug("Generating heatmap. Assuming input df is the matrix.")
                if isinstance(plot_df, pd.DataFrame) and plot_df.shape[0] > 0 and plot_df.shape[1] > 0 and pd.api.types.is_numeric_dtype(plot_df.iloc[:, 0]): # Basic check if it looks like a matrix
                    sns.heatmap(plot_df, annot=True, fmt=".2f", cmap='viridis', ax=ax)
                    plot_title = "Heatmap"
                else:
                    raise ValueError("Heatmap requires input data to be in a suitable matrix format (e.g., correlation matrix). Direct generation from raw columns is complex.")

            else:
                raise ValueError(f"Unsupported plot type provided: '{plot_type}'")

            # --- Final Touches ---
            ax.set_title(plot_title, fontsize=14)
            # Set labels using original names if available in params (enhancement)
            ax.set_xlabel(params.get('x_col_original', x_col) if x_col else None)
            ax.set_ylabel(params.get('y_col_original', y_col) if y_col else None)
            plt.tight_layout() # Adjust layout

            # --- Save plot to buffer ---
            img_buffer = io.BytesIO()
            try:
                logger.debug(f"Saving plot '{plot_title}' to PNG buffer...")
                fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
                img_buffer.seek(0)
                logger.info(f"Plot '{plot_title}' generated and saved to buffer successfully.")
                png_bytes = img_buffer.getvalue()
                plt.close(fig) # IMPORTANT: Close plot to free memory
                return fig, png_bytes, None # Success
            except Exception as save_err:
                 plt.close(fig) # Close plot even if saving fails
                 logger.error(f"Failed to save plot to buffer: {save_err}", exc_info=True)
                 raise Exception(f"Failed to save plot to buffer: {save_err}") # Re-raise

        except ValueError as ve:
            plt.close(fig) # Ensure plot is closed on error
            error_msg = f"Plotting Error (ValueError): {ve}"
            logger.error(error_msg) # Log the specific value error
            return None, None, error_msg
        except TypeError as te:
             plt.close(fig)
             error_msg = f"Plotting Error (TypeError): Likely incompatible data type for plot/axis. Details: {te}"
             logger.error(error_msg, exc_info=True) # Log with traceback for type errors
             return None, None, error_msg
        except Exception as e:
            plt.close(fig) # Ensure plot is closed on error
            error_msg = f"An unexpected error occurred during plotting: {type(e).__name__} - {e}"
            logger.error(error_msg, exc_info=True) # Log general errors with traceback
            return None, None, error_msg