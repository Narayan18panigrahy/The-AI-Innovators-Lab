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