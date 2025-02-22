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