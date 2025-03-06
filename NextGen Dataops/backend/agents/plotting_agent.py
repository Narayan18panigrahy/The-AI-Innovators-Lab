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