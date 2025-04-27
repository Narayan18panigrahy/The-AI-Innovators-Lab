                    selected_sheet = sheet_names[0]
                    if len(sheet_names) > 1:
                         logger.warning(f"Excel file '{file_name_for_log}' has multiple sheets: {sheet_names}. Loading first sheet ('{selected_sheet}').")
                    df = pd.read_excel(xls, sheet_name=selected_sheet)
                    logger.debug(f"Excel sheet '{selected_sheet}' from '{file_name_for_log}' loaded.")
                except Exception as e_excel:
                    logger.error(f"Failed reading Excel file '{file_name_for_log}'. Error: {e_excel}", exc_info=True)
                    return None
            else:
                # If extension was unknown, maybe try sniffing? For now, error out.
                logger.error(f"Unsupported or unknown file type '{file_extension}' for file '{file_name_for_log}'.")
                return None

            # --- Post-Loading Checks ---
            if df is not None and df.empty:
                logger.warning(f"Loaded file '{file_name_for_log}' appears to be empty.")
            elif df is not None:
                 logger.info(f"File '{file_name_for_log}' loaded successfully into DataFrame ({len(df)} rows).")

            return df

        except Exception as e:
            logger.error(f"An unexpected error occurred loading '{file_name_for_log}': {e}", exc_info=True)
            return None