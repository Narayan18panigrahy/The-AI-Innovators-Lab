            logger.debug(f"Added polynomial feature suggestions for column '{col}'.")

        # 3. Interaction Features (between pairs of numeric columns)
        # Limit combinations to avoid too many suggestions
        max_interaction_cols = 5 # Consider only first N numeric cols for pairwise interactions
        cols_for_interaction = numeric_cols[:max_interaction_cols]
        if len(cols_for_interaction) >= 2:
            for col1, col2 in itertools.combinations(cols_for_interaction, 2):
                 suggestions.append({
                    "name": f"{col1}_x_{col2}", "type": "Interaction",
                    "description": f"Product of '{col1}' and '{col2}'",
                    "action_code": "interaction_feature", "details": {"columns": [col1, col2], "operation": "multiply"}
                 })
                 # Optional: Add division/ratio interaction if meaningful
                 # suggestions.append({
                 #    "name": f"{col1}_div_{col2}", "type": "Interaction",
                 #    "description": f"Ratio of '{col1}' / '{col2}'",
                 #    "action_code": "interaction_feature", "details": {"columns": [col1, col2], "operation": "divide"}
                 # })
            logger.debug(f"Added interaction feature suggestions for columns: {cols_for_interaction}.")

        # 4. Binning/Discretization (for numeric columns)
        # Suggest binning for columns that aren't likely identifiers (e.g., based on cardinality?)
        # TODO: Implement suggestion for binning numeric columns (e.g., into quartiles or fixed bins)
        logger.debug("Binning suggestion generation is currently skipped (TODO).")


        # --- (Optional) LLM-Powered Suggestions ---
        # if use_llm_suggestions:
        #    try:
        #        # Format column names/types for prompt
        #        # Prompt LLM to suggest features based on column names and types
        #        llm_suggestions = self._get_llm_feature_suggestions(df.dtypes, llm_config)
        #        suggestions.extend(llm_suggestions)
        #    except Exception as e:
        #        logger.error(f"Could not get LLM-powered feature suggestions: {e}", exc_info=True)

        logger.info(f"Generated {len(suggestions)} feature suggestions.")
        return suggestions

    # --- Application of Feature Engineering Steps ---

    def apply_features(self, df: pd.DataFrame, selected_features: list[dict]) -> tuple[pd.DataFrame, list[str]]:
        """
        Applies the selected feature engineering actions to the DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame to add features to.
            selected_features (list[dict]): A list of feature suggestion dictionaries
                                             that the user chose to apply.

        Returns:
            tuple[pd.DataFrame, list[str]]: (dataframe_with_new_features, log_messages)
        """
        if df is None:
            logger.error("Cannot apply features: Input DataFrame is None.")
            return None, ["Error: Input DataFrame is None."]

        engineered_df = df.copy() # Work on a copy
        logs = []

        logger.info(f"Applying {len(selected_features)} selected feature engineering steps.")

        for feature in selected_features:
            name = feature.get('name')
            code = feature.get('action_code')
            details = feature.get('details', {})
            applied_msg = None
            error_msg = None

            # Prevent overwriting existing columns (maybe allow later with option?)
            if name in engineered_df.columns:
                 error_msg = f"Skipping feature '{name}': Column already exists."
                 logs.append(f"Warning: {error_msg}")
                 logger.warning(error_msg)
                 continue

            try:
                if code == 'extract_datetime':
                    col = details.get('column')
                    part = details.get('part')
                    if col and part and col in engineered_df.columns:
                        # Ensure column is datetime
                        if not pd.api.types.is_datetime64_any_dtype(engineered_df[col]):
                             logger.debug(f"Attempting to convert column '{col}' to datetime for feature '{name}'.")
                             engineered_df[col] = pd.to_datetime(engineered_df[col], errors='coerce') # Attempt conversion
                        # Check again after conversion attempt
                        if pd.api.types.is_datetime64_any_dtype(engineered_df[col]):
                             if part == 'year': engineered_df[name] = engineered_df[col].dt.year
                             elif part == 'month': engineered_df[name] = engineered_df[col].dt.month
                             elif part == 'day': engineered_df[name] = engineered_df[col].dt.day
                             elif part == 'weekday': engineered_df[name] = engineered_df[col].dt.weekday
                             elif part == 'hour': engineered_df[name] = engineered_df[col].dt.hour
                             # Add other parts as needed
                             else: raise ValueError(f"Unsupported datetime part: {part}")
                             # Fill NaNs potentially introduced by to_datetime(errors='coerce') or in original dt extraction
                             if engineered_df[name].isnull().any():
                                engineered_df[name].fillna(-1, inplace=True) # Fill with -1 or suitable placeholder
                                engineered_df[name] = engineered_df[name].astype(int) # Convert if possible
                             applied_msg = f"Applied '{code}': Extracted '{part}' from '{col}' into '{name}'."