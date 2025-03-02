# backend/agents/llm/nl_to_viz_agent.py

# import traceback # Removed
import json
import re
import logging # Import logging
from typing import List, Dict, Tuple, Optional, Any

# Import the centralized client function
try:
    from agents.llm.llm_client import execute_llm_completion
except ImportError:
    # Log this critical error
    logging.critical("CRITICAL ERROR: Could not import llm_client.py in NLtoVizAgent. LLM functionality will be disabled.")
    execute_llm_completion = None # Define as None to allow class definition

# Get a logger specific to this module
logger = logging.getLogger(__name__)

class NLtoVizAgent:
    """
    Agent that uses an LLM to interpret natural language visualization requests
    and output structured parameters for plotting. Includes retry logic for errors.
    """
    SUPPORTED_PLOT_TYPES = [
        'scatter', 'histogram', 'bar', 'line', 'box', 'heatmap'
    ]
    MAX_RETRIES = 1 # Max retries on parameter generation failure

    def __init__(self):
        """Initializes the NLtoVizAgent."""
        logger.debug("NLtoVizAgent initialized.")
        pass # Keep pass as __init__ doesn't do anything else now

    def _construct_prompt(self, nl_request: str, schema_str: str,
                          previous_params_str: Optional[str] = None,
                          error_feedback: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Constructs the prompt messages for the LLM to extract plot parameters.
        Includes optional fields for retry attempts with error feedback.
        """
        supported_types_str = ", ".join(self.SUPPORTED_PLOT_TYPES)
        system_prompt_header = "You are an expert data visualization assistant. Your task is to interpret a natural language request for a plot and extract the necessary parameters into a structured JSON object."

        schema_section = f"DataFrame Schema (`df`):\n```\n{schema_str}\n```"
        instructions_header = "Instructions & Constraints:"
        instructions_body = f"""
        1.  **Analyze Request:** Understand the user's desired visualization (type, data columns, relationships).
        2.  **Use Schema:** Identify the exact column names from the schema that correspond to the user's request. Use the column names as they appear in the schema string.
        3.  **Select Plot Type:** Choose the most appropriate plot type from the 'Available Plot Types' list based on the request and data columns.
        4.  **Identify Columns:** Determine the column(s) for the X-axis (`x_col`), Y-axis (`y_col`), color (`color_col`), size (`size_col`), etc., as applicable to the plot type and request. Use `null` if a parameter is not applicable or not specified.
        5.  **Aggregation (for Bar/Line):** If the request implies aggregation (e.g., "total sales per region", "average price over time"), identify the aggregation function (`aggregation`: 'sum', 'mean', 'count', 'median', etc.) and the column to aggregate (`y_col` usually becomes the aggregated value). The `x_col` is typically the grouping column or time axis. For a simple bar chart of counts, `y_col` might be null and `aggregation` would be 'count'.
        6.  **Output Format:** Respond ONLY with a single, valid JSON object containing the extracted parameters. Do NOT include any explanations, comments, or markdown formatting (like ```json ... ```).

        JSON Output Structure:
        {{
          "plot_type": "...",            // One of [{supported_types_str}]
          "x_col": "...",                // Column name from schema for X-axis, or null
          "y_col": "...",                // Column name from schema for Y-axis, or null
          "color_col": "...",            // Column name for color encoding, or null
          "size_col": "...",             // Column name for size encoding (scatter), or null
          "aggregation": "...",          // Aggregation function ('count', 'sum', 'mean', etc.), or null
          "error": "..."                 // Optional: Error message if request cannot be fulfilled, otherwise null or omit.
        }}

        Example Request 1: "Show distribution of age using a histogram"
        Example Output 1:
        {{
          "plot_type": "histogram",
          "x_col": "age",
          "y_col": null,
          "color_col": null,
          "size_col": null,
          "aggregation": null,
          "error": null
        }}

        Example Request 2: "Plot total sales per region as a bar chart"
        Example Output 2:
        {{
          "plot_type": "bar",
          "x_col": "region",
          "y_col": "sales",
          "color_col": null,
          "size_col": null,
          "aggregation": "sum",
          "error": null
        }}

        Example Request 3: "Scatter plot of marketing spend vs revenue, colored by campaign"
        Example Output 3:
        {{
          "plot_type": "scatter",
          "x_col": "marketing_spend",
          "y_col": "revenue",
          "color_col": "campaign",
          "size_col": null,
          "aggregation": null,
          "error": null
        }}