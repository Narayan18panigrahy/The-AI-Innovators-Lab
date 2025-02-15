# -*- coding: utf-8 -*-
"""
reporting_agent.py

Defines the ReportingAgent class responsible for displaying analysis results
(profiling, NER) in the Streamlit UI and generating downloadable reports (PDF).
"""


import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF # For PDF generation
import io # For handling bytes buffer for plots
from datetime import datetime
import numpy as np # For numerical operations
import math # For ceil function in PDF table pagination
import logging # Import logging
from typing import Dict, Optional
# import traceback # No longer needed with logger.error(exc_info=True)

# Get a logger specific to this module
logger = logging.getLogger(__name__)

class ReportingAgent:
    """
    Agent responsible for presenting analysis results in the UI
    and generating downloadable reports.
    """

    def __init__(self):
        """Initializes the ReportingAgent."""
        # No specific state needed currently
        self.pdf_col_width = 55 # Define standard column width for PDF tables
        logger.debug("ReportingAgent initialized.")

    # --- UI Display Methods ---
    # Note: UI display methods using Streamlit (st.*) are removed as this agent
    # should focus on report generation (PDF) and potentially returning structured data
    # for the UI layer (like Flask/React) to handle.

    # --- Helper to safely convert object columns ---
    def _safe_convert_to_str(self, df):
        """Converts object columns to string safely for display/output."""
        if not isinstance(df, (pd.DataFrame, pd.Series)):
            return df # Return original if not pandas object
        display_df = df.copy()
        if isinstance(display_df, pd.DataFrame):
            for col in display_df.select_dtypes(include=['object']).columns:
                try:
                    display_df[col] = display_df[col].astype(str)
                except Exception as e:
                    logger.warning(f"Could not convert column '{col}' to string for display: {e}")
                    pass # Ignore conversion errors for display prep
        elif isinstance(display_df, pd.Series) and display_df.dtype == 'object':
            try:
                display_df = display_df.astype(str)
            except Exception as e:
                 logger.warning(f"Could not convert Series to string for display: {e}")
                 pass
        return display_df

    # --- PDF Report Generation ---

    def generate_report_pdf(self, report: dict, dataframe_name: str) -> Optional[bytes]:
        """
        Generates a PDF summary of the profiling report.

        Args:
            report (dict): The profiling report dictionary.
            dataframe_name (str): The name of the dataframe being reported on.

        Returns:
            Optional[bytes]: The generated PDF content as bytes, or None if error.
        """
        if not report:
            logger.error("Cannot generate PDF: No profiling report data provided.")
            return None

        logger.info(f"Starting PDF report generation for '{dataframe_name}'...")
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)

            # --- Title ---
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, f"Data Profiling Report: {dataframe_name}", ln=True, align='C')
            pdf.set_font("Helvetica", size=8)
            pdf.cell(0, 5, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
            pdf.ln(10)

            # --- Overview Section ---
            self._add_pdf_section_title(pdf, "Overview")
            basic_info = report.get('basic_info', {})
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 5,
                           f"Rows: {basic_info.get('rows', 'N/A'):,} | "
                           f"Columns: {basic_info.get('columns', 'N/A'):,} | "
                           f"Duplicate Rows: {basic_info.get('duplicates', 'N/A'):,} | "