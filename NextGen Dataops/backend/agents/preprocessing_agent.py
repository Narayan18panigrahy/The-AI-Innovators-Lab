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