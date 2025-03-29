            cols = list(corr_matrix.keys())
            for i in range(len(cols)):
                for j in range(i + 1, len(cols)):
                    col1, col2 = cols[i], cols[j]
                    # Handle potential non-dict values if corr matrix structure is unexpected
                    corr_col1_data = corr_matrix.get(col1)
                    if isinstance(corr_col1_data, dict):
                        corr_val = corr_col1_data.get(col2)
                        if corr_val is not None and abs(corr_val) > 0.7:
                            high_correlations.append(f"{col1} & {col2} ({corr_val:.2f})")
            if high_correlations:
                summary_lines.append(f"- Strong correlations (|corr| > 0.7): {'; '.join(high_correlations)}")
            else:
                summary_lines.append("- No strong pairwise correlations (|corr| > 0.7) found.")

        # --- Outlier Highlights ---
        outlier_info = profile_report.get('outlier_detection', {})
        if outlier_info and not outlier_info.get("error"):
            summary_lines.append(f"\n--- Outlier Detection (DBSCAN) ---")
            summary_lines.append(f"- Found {outlier_info.get('outlier_count', 'N/A'):,} potential outliers ({outlier_info.get('outlier_percentage', 'N/A'):.2f}% of analyzed rows).")
            if outlier_info.get('rows_dropped_nan', 0) > 0:
                 summary_lines.append(f"- Note: {outlier_info['rows_dropped_nan']:,} rows with NaN were excluded from this analysis.")

        # --- NER Highlights (Optional) ---
        if ner_report:
            summary_lines.append(f"\n--- Text Analysis (NER) Highlights ---")
            found_entities = False
            for col, data in ner_report.items():
                 # Check if entities_by_type exists and is not empty
                 if isinstance(data, dict) and data.get('entities_by_type'):
                     summary_lines.append(f"- Column '{col}': Found entity types like {', '.join(data['entities_by_type'].keys())}.")
                     found_entities = True
            if not found_entities:
                 summary_lines.append("- No significant named entities identified in analyzed text columns.")

        return "\n".join(summary_lines)

    # _construct_prompt method remains the same
    def _construct_prompt(self, report_summary: str) -> List[Dict[str, str]]:
        """
        Constructs the prompt messages for the LLM to generate insights.

        Args:
            report_summary: A formatted string summarizing report findings.

        Returns:
            A list of message dictionaries for the LLM API.
        """
        system_prompt = f"""You are a helpful data analysis assistant. Based on the following summary of a data profiling report, please provide a concise, high-level narrative summary of the dataset's characteristics.

Focus on:
1.  **Overall Structure:** Briefly mention size and number of features.
2.  **Data Quality:** Highlight key issues like missing data, duplicates, or potential outliers identified.
3.  **Interesting Features:** Point out any columns with notable characteristics (e.g., high cardinality, strong correlations, identified entities if available).
4.  **Potential Next Steps:** Briefly suggest 1-2 general next steps for analysis or cleaning based *only* on the provided summary (e.g., "investigate missing values in column X", "explore the relationship between correlated columns Y and Z").

Keep the summary easy to read, use bullet points for key findings, and limit the response to 2-3 paragraphs. Do not simply repeat the input summary; synthesize the information.

Profiling Report Summary:
---
{report_summary}
---
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please generate the data summary and insights based on the report provided in the system instructions."} # Simple trigger
        ]
        logger.debug(f"Insight Agent Prompt Messages: {messages}")
        return messages

    # Refactored to use llm_client
    def generate_summary(self, profile_report: Dict[str, Any], llm_config: Dict, ner_report: Optional[Dict[str, Any]] = None, dataframe_name: Optional[str] = None) -> Optional[str]:
        """
        Uses the centralized LLM client to generate a textual summary from reports.

        Args:
            profile_report: The data profiling report.
            llm_config: Dictionary containing provider, model, credentials.
            ner_report: Optional NER report for additional context.
            dataframe_name: Optional name of the dataset.

        Returns:
            The generated summary string, or an error message string if failed.
            Returns None only if configuration is missing before the call.
        """
        logger.info("Generating AI summary via InsightAgent...")
        if execute_llm_completion is None:
             logger.error("LLM client function not available for InsightAgent.")
             return "Error: LLM client is not available."
        if not profile_report or not llm_config:
            logger.error("Missing profiling report or LLM configuration for summary generation.")
            return None # Indicate config issue before attempting call

        model_name = llm_config.get("model_name")
        credentials = llm_config.get("credentials", {})
        if not model_name or not credentials:
             logger.error("LLM model name or credentials missing in configuration.")
             return None # Indicate config issue before attempting call

        # Format the report data concisely for the prompt