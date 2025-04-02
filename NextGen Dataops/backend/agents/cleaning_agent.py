            else:
                log_msg = "Applied 'remove_duplicates': No duplicate rows found to remove."
                logs.append(log_msg)
                logger.info(log_msg)
            # Remove this action from the list so it's not processed again
            selected_actions = [a for a in selected_actions if a['action_code'] != 'remove_duplicates']


        # Apply column dropping actions next
        cols_to_drop = set()
        actions_remaining = []
        for action in selected_actions:
            if action['action_code'] == 'drop_column':
                col = action.get('column')
                if col and col not in cols_to_drop:
                    cols_to_drop.add(col)
                    log_msg = f"Marked column '{col}' for dropping due to '{action.get('issue', 'N/A')}'."
                    logs.append(log_msg)
                    logger.debug(log_msg)
                # Don't add this action to remaining list
            else:
                actions_remaining.append(action)
        selected_actions = actions_remaining

        if cols_to_drop:
            try:
                cleaned_df.drop(columns=list(cols_to_drop), inplace=True)
                log_msg = f"Dropped columns: {list(cols_to_drop)}"
                logs.append(log_msg)
                logger.info(log_msg)
            except KeyError as e:
                 log_msg = f"Warning: Could not drop columns - {e}. They might have been dropped already."
                 logs.append(log_msg)
                 logger.warning(log_msg)
            except Exception as e:
                 log_msg = f"Error during column dropping: {e}"
                 logs.append(log_msg)
                 logger.error(log_msg, exc_info=True)

        # Apply remaining column-level actions (imputation, type conversion etc.)
        for action in selected_actions:
            col = action.get('column')
            code = action.get('action_code')
            details = action.get('details', {})

            # Check if column still exists (might have been dropped)
            if col not in cleaned_df.columns:
                 log_msg = f"Skipping action '{code}' for column '{col}': Column no longer exists."
                 logs.append(log_msg)
                 logger.warning(log_msg)
                 continue

            # --- Imputation ---
            imputer = None
            fill_val = None
            strategy = None
            applied_msg = None

            try:
                if code == 'impute_median':
                    imputer = SimpleImputer(strategy='median')
                    strategy = 'median'
                elif code == 'impute_mean':
                    imputer = SimpleImputer(strategy='mean')
                    strategy = 'mean'
                elif code == 'impute_mode':
                     # SimpleImputer strategy='most_frequent' handles mode for categorical/numeric
                    imputer = SimpleImputer(strategy='most_frequent')
                    strategy = 'mode (most frequent)'
                elif code == 'impute_constant':
                    fill_val = details.get('fill_value', 'Unknown') # Get constant value
                    imputer = SimpleImputer(strategy='constant', fill_value=fill_val)
                    strategy = f'constant ({fill_val})'

                if imputer:
                    # Check if imputation already applied with different strategy for this column
                    prev_action = applied_codes_for_col.get(col)
                    if prev_action and prev_action.startswith("impute"):
                         log_msg = f"Skipping '{code}' for '{col}': Imputation '{prev_action}' already applied."
                         logs.append(log_msg); logger.warning(log_msg); continue

                    # Fit and transform
                    # Reshape needed as SimpleImputer expects 2D array
                    logger.debug(f"Applying imputation '{code}' (strategy: {strategy}) to column '{col}'.")
                    cleaned_df[col] = imputer.fit_transform(cleaned_df[[col]])
                    applied_msg = f"Applied '{code}': Imputed missing values in '{col}' with {strategy}."
                    applied_codes_for_col[col] = code # Mark imputation as done for this column

                # --- Add other actions here ---
                # elif code == 'convert_dtype':
                #     target_type = details.get('target_type', 'string')
                #     try:
                #         logger.debug(f"Applying type conversion '{code}' to column '{col}' (target: {target_type}).")
                #         cleaned_df[col] = cleaned_df[col].astype(target_type)
                #         applied_msg = f"Applied '{code}': Converted column '{col}' to {target_type}."
                #         applied_codes_for_col[col] = code
                #     except Exception as type_err:
                #          log_msg = f"Error converting '{col}' to {target_type}: {type_err}"
                #          logs.append(log_msg); logger.error(log_msg); continue
