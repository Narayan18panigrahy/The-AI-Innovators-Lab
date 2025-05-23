# -*- coding: utf-8 -*-
"""
insight_agent.py

Defines the InsightAgent class responsible for generating textual summaries
and potential insights from data profiles using the centralized LLM client.
"""


# import traceback # No longer needed with logger.error(exc_info=True)
import json # Could be used for more complex formatting if needed
import logging # Import logging
from typing import List, Dict, Tuple, Optional, Any

# Import the centralized client function
try:
    from agents.llm.llm_client import execute_llm_completion
except ImportError:
    # This critical error should be logged centrally, maybe raise exception
    logging.critical("CRITICAL ERROR: Could not import llm_client.py in InsightAgent. LLM functionality will be disabled.")
    execute_llm_completion = None # Define as None to allow class definition

# Get a logger specific to this module
logger = logging.getLogger(__name__)

class InsightAgent:
    """
    Agent that uses an LLM to generate textual summaries and
    insights based on profiling reports and other context.
    """

    def __init__(self):
        """Initializes the InsightAgent."""
        logger.debug("InsightAgent initialized.")
        pass

    # _format_report_for_prompt remains the same
    def _format_report_for_prompt(self, profile_report: Dict[str, Any], ner_report: Optional[Dict[str, Any]], dataframe_name: Optional[str]) -> str:
        """
        Formats the profiling and NER reports into a concise string for the LLM prompt.

        Args:
            profile_report: The data profiling report dictionary.
            ner_report: Optional NER report dictionary.
            dataframe_name: Optional name of the dataframe.

        Returns:
            A formatted string summarizing the reports, or a message indicating no report.
        """
        if not profile_report:
            logger.warning("Cannot format report for prompt: No profiling report provided.")
            return "No profiling report available."

        logger.debug("Formatting report summary for LLM prompt...")
        summary_lines = []
        df_name = dataframe_name if dataframe_name else "the dataset"

        # --- Basic Info ---
        basic_info = profile_report.get('basic_info', {})
        summary_lines.append(f"--- Overview of {df_name} ---")
        summary_lines.append(f"- Rows: {basic_info.get('rows', 'N/A'):,}")
        summary_lines.append(f"- Columns: {basic_info.get('columns', 'N/A'):,}")
        summary_lines.append(f"- Duplicate Rows: {basic_info.get('duplicates', 'N/A'):,}")
        summary_lines.append(f"- Memory Usage: {basic_info.get('memory_usage', 'N/A')}")

        # --- Missing Values Highlights ---
        missing_values = profile_report.get('missing_values', {})
        high_missing = {col: data['percentage'] for col, data in missing_values.items() if data.get('percentage', 0) > 10}
        total_missing_cols = sum(1 for data in missing_values.values() if data.get('count', 0) > 0)
        if total_missing_cols > 0:
            summary_lines.append(f"\n--- Data Quality: Missing Values ---")
            summary_lines.append(f"- {total_missing_cols} columns have missing values.")
            if high_missing:
                summary_lines.append(f"- Columns with >10% missing: {', '.join([f'{col} ({perc:.1f}%)' for col, perc in high_missing.items()])}")
            else:
                summary_lines.append("- No columns have high percentages (>10%) of missing values.")

        # --- Cardinality Highlights ---
        cardinality = profile_report.get('cardinality', {})
        if cardinality:
            summary_lines.append(f"\n--- Cardinality Highlights ---")
            object_cols = profile_report.get('data_types', {})
            high_card_categoricals = {
                col: count for col, count in cardinality.items()
                if object_cols.get(col, '').lower() in ['object', 'string', 'category'] and count > 50
            }
            if high_card_categoricals:
                 summary_lines.append(f"- Potential high cardinality categorical columns (>50 unique): {', '.join(high_card_categoricals.keys())}")

            rows = basic_info.get('rows', 0)
            if rows > 0:
                 potential_ids = [col for col, count in cardinality.items() if count == rows]
                 if potential_ids:
                      summary_lines.append(f"- Columns with unique values for every row (potential IDs): {', '.join(potential_ids)}")

        # --- Correlation Highlights ---
        corr_matrix = profile_report.get('correlation_matrix')
        if corr_matrix:
            summary_lines.append(f"\n--- Correlation Highlights ---")
            high_correlations = []
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
        report_summary_str = self._format_report_for_prompt(profile_report, ner_report, dataframe_name)
        if report_summary_str == "No profiling report available.":
            logger.error("Cannot generate summary: Profiling report is missing or invalid.")
            return "Error: Profiling report is missing or invalid."
        logger.debug(f"Formatted Report Summary for Prompt:\n{report_summary_str}")

        messages = self._construct_prompt(report_summary_str)
        temperature = 0.5 # Allow reasonable creativity for summarization
        max_tokens = 400  # Adjust based on desired summary length

        # Call the centralized LLM execution function
        summary_text, error = execute_llm_completion(
            llm_config=llm_config,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Handle the response
        if error:
            # Error should have been logged by llm_client, just return it
            # No need to log again here unless adding context
            logger.error(f"InsightAgent received error from LLM client: {error}")
            return f"Error generating summary: {error}"
        elif summary_text:
            logger.info(f"Generated Summary Text (snippet): {summary_text[:100]}...") # Log snippet
            return summary_text.strip()
        else:
            logger.warning("Insight Agent: LLM client returned empty content without specific error.")
            return "LLM response was empty."
