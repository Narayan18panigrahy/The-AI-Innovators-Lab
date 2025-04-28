                            "column": col, "issue": f"{missing_perc:.1f}% Missing",
                            "suggestion": "Impute with Mode (Most Frequent)",
                            "action_code": "impute_mode", "details": {}
                         })
                         suggestions.append({
                            "column": col, "issue": f"{missing_perc:.1f}% Missing",
                            "suggestion": "Impute with Constant 'Missing'",
                            "action_code": "impute_constant", "details": {"fill_value": "Missing"}
                         })
                         logger.debug(f"Suggesting impute_mode/constant for categorical column '{col}' (<30% missing).")
                     else:
                          suggestions.append({
                            "column": col, "issue": f"{missing_perc:.1f}% Missing",
                            "suggestion": "Drop Column (High Missing %)",
                            "action_code": "drop_column", "details": {}
                          })
                          logger.debug(f"Suggesting drop_column for categorical column '{col}' (>=30% missing).")

        # 2. Handling Duplicate Rows
        duplicate_count = basic_info.get('duplicates', 0)
        if duplicate_count > 0:
            suggestions.append({
                "column": "ALL", # Apply to whole DataFrame
                "issue": f"{duplicate_count:,} Duplicate Rows",
                "suggestion": "Remove Duplicate Rows",
                "action_code": "remove_duplicates", "details": {}
            })
            logger.debug(f"Suggesting remove_duplicates for {duplicate_count} duplicate rows.")

        # 3. Handling Outliers (Based on DBSCAN report) - Suggesting removal is simple
        #    More advanced: suggest capping, transformation. For now, suggest removal.
        if outlier_info and outlier_info.get("outlier_count", 0) > 0 and not outlier_info.get("error"):
             logger.debug(f"Outliers detected ({outlier_info.get('outlier_count', 0)}), but automatic removal suggestion based on DBSCAN is currently skipped.")
             # Note: DBSCAN flags rows, not specific columns. Applying removal removes the whole row.
             # Also, DBSCAN was run only on numeric columns after dropping NaNs there.
             # This suggestion is complex to apply perfectly without outlier indices.
             # Let's skip suggesting automatic outlier removal based on DBSCAN for now,
             # as it requires storing and using the outlier indices which we didn't implement.
             # A simpler rule could be IQR-based outlier suggestion per column.
             # TODO: Implement IQR or Z-score based outlier suggestions per numeric column.
             pass # Placeholder for future outlier handling suggestions


        # 4. Mixed Data Types (Requires more sophisticated detection in profiling)
        # TODO: Add profiling check for mixed types within a column.
        # If mixed types found (e.g., numbers and strings in same column):
        # suggestions.append({"column": col, "issue": "Mixed Data Types", "suggestion": "Convert to String / Attempt Numeric Conversion", "action_code": "convert_dtype", "details": {"target_type": "string"}})
        logger.debug("Mixed data type suggestion generation is currently skipped (TODO).")

        # 5. High Cardinality Categoricals (Suggest grouping less frequent)
        # TODO: Implement suggestion for grouping less frequent categories.
        logger.debug("High cardinality suggestion generation is currently skipped (TODO).")

        # --- (Optional) LLM-Powered Suggestions ---
        # This would involve formatting the profile summary and prompting an LLM
        # Example placeholder:
        # if use_llm_suggestions:
        #    try:
        #        llm_suggestions = self._get_llm_cleaning_suggestions(profile_report, llm_config)
        #        suggestions.extend(llm_suggestions) # Assuming LLM returns suggestions in the same format
        #    except Exception as e:
        #        logger.error(f"Could not get LLM-powered cleaning suggestions: {e}", exc_info=True)

        logger.info(f"Generated {len(suggestions)} cleaning suggestions.")
        return suggestions

    # --- Application of Cleaning Steps ---

    def apply_cleaning_steps(self, df: pd.DataFrame, selected_actions: list[dict]) -> tuple[pd.DataFrame, list[str]]:
        """
        Applies the selected cleaning actions to the DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame to clean.
            selected_actions (list[dict]): A list of suggestion dictionaries
                                            that the user chose to apply.

        Returns:
            tuple[pd.DataFrame, list[str]]: (cleaned_dataframe, log_messages)
        """
        if df is None:
            logger.error("Cannot apply cleaning steps: Input DataFrame is None.")
            return None, ["Error: Input DataFrame is None."]

        cleaned_df = df.copy() # Work on a copy
        logs = []
        applied_codes_for_col = {} # Track actions applied per column

        logger.info(f"Applying {len(selected_actions)} selected cleaning actions.")

        # --- Apply Actions Systematically ---
        # Apply row-level actions first (like remove duplicates)
        if any(action['action_code'] == 'remove_duplicates' for action in selected_actions):
            initial_rows = len(cleaned_df)
            cleaned_df.drop_duplicates(inplace=True)
            rows_removed = initial_rows - len(cleaned_df)
            if rows_removed > 0:
                log_msg = f"Applied 'remove_duplicates': Removed {rows_removed:,} duplicate rows."
                logs.append(log_msg)
                logger.info(log_msg)