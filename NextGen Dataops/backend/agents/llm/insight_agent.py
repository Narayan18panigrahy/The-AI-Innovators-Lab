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