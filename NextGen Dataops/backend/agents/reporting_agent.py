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
                           f"Memory Usage: {basic_info.get('memory_usage', 'N/A')}"
                           )
            pdf.ln(5)

            # --- Missing Values Summary ---
            self._add_pdf_section_title(pdf, "Missing Values Summary")
            missing_data = report.get('missing_values', {})
            if missing_data:
                missing_df = pd.DataFrame.from_dict(missing_data, orient='index')
                missing_df.columns = ['Count', 'Percentage (%)']
                missing_df = missing_df[missing_df['Count'] > 0].sort_values(by='Percentage (%)', ascending=False)
                if not missing_df.empty:
                    self._add_df_to_pdf(pdf, missing_df.reset_index().rename(columns={'index': 'Column'}), title="Columns with Missing Values")
                else:
                    pdf.cell(0, 5, "No missing values found.", ln=True)
            else:
                pdf.cell(0, 5, "Missing value information not available.", ln=True)
            pdf.ln(5)

            # --- Descriptive Statistics Summary ---
            self._add_pdf_section_title(pdf, "Descriptive Statistics Highlights (Numeric)")
            numeric_stats_data = report.get('descriptive_stats', {}).get('numeric')
            if numeric_stats_data:
                try:
                    numeric_stats_df = pd.DataFrame(numeric_stats_data)
                    # Select key stats for summary (e.g., mean, std, min, max) - adjust as needed
                    summary_stats = numeric_stats_df.loc[['mean', 'std', 'min', '25%', '50%', '75%', 'max']].reset_index()
                    summary_stats.rename(columns={'index': 'Statistic'}, inplace=True)
                    self._add_df_to_pdf(pdf, summary_stats, title="Numeric Statistics Summary", max_cols=4) # Show fewer columns
                except KeyError as ke:
                     logger.warning(f"Could not display numeric stats in PDF, missing expected index: {ke}")
                     pdf.cell(0, 5, f"Could not display numeric stats, missing expected index: {ke}", ln=True)
                except Exception as e:
                     logger.warning(f"Could not display numeric stats in PDF: {e}")
                     pdf.cell(0, 5, f"Could not display numeric stats: {e}", ln=True)
            else:
                pdf.cell(0, 5, "No numeric statistics available.", ln=True)
            pdf.ln(5)

            # --- Outlier Summary ---
            self._add_pdf_section_title(pdf, "Outlier Detection Summary (DBSCAN)")
            outlier_info = report.get('outlier_detection', {})
            if outlier_info:
                if outlier_info.get("error"):
                    pdf.multi_cell(0, 5, f"DBSCAN Error: {outlier_info['error']}")
                else:
                     pdf.multi_cell(0, 5,
                           f"Potential Outliers Found: {outlier_info.get('outlier_count', 'N/A'):,} "
                           f"({outlier_info.get('outlier_percentage', 'N/A'):.2f}%) | "
                           f"Rows Analyzed (non-NaN): {outlier_info.get('rows_analyzed', 'N/A'):,} | "
                           f"Params: eps={outlier_info.get('parameters', {}).get('eps', 'N/A')}, "
                           f"min_samples={outlier_info.get('parameters', {}).get('min_samples', 'N/A')}"
                           )
            else:
                 pdf.cell(0, 5, "Outlier detection information not available.", ln=True)
            pdf.ln(5)


            # --- (Optional) Add Correlation Heatmap Image ---
            # This requires saving the plot generated earlier or regenerating it
            # Example (requires plot object to be passed or regenerated):
            corr_matrix_data = report.get('correlation_matrix')
            if corr_matrix_data is not None:
                try:
                    corr_df = pd.DataFrame(corr_matrix_data)
                    if not corr_df.empty and len(corr_df.columns) > 1:
                        self._add_pdf_section_title(pdf, "Correlation Heatmap")
                        img_buffer = self._generate_plot_image_buffer(corr_df)
                        if img_buffer:
                            # Calculate image width to fit page (adjust as needed)
                            img_width = 180 # Max width in mm for A4 page approx
                            # Add image - FPDF needs a file path or BytesIO
                            pdf.image(img_buffer, x=pdf.get_x() + (pdf.w - pdf.l_margin - pdf.r_margin - img_width) / 2, y=pdf.get_y(), w=img_width)
                            # Estimate height based on common aspect ratio (adjust if needed)
                            img_height_estimate = img_width * 0.6
                            pdf.ln(img_height_estimate + 5) # Add line break after image
                        else:
                             pdf.cell(0, 5, "Could not generate correlation plot image.", ln=True)
                             logger.warning("Correlation matrix data present, but failed to generate heatmap image for PDF.")
                except Exception as img_err:
                     pdf.cell(0, 5, f"Error adding correlation plot image: {img_err}", ln=True)
                     logger.error(f"Error adding correlation plot image to PDF: {img_err}", exc_info=True)
            pdf.ln(5)


            # --- Generate PDF bytes ---
            # The comment below might be based on a misunderstanding or different fpdf version.
            # The error "AttributeError: 'bytearray' object has no attribute 'encode'"
            # indicates that pdf.output(dest='S') is returning a bytearray in your environment.
            pdf_output_content = pdf.output(dest='S')

            # Since pdf_output_content is a bytearray (as per the error),
            # we convert it to bytes to match the function's type hint.
            # We do not call .encode() on a bytearray.
            if isinstance(pdf_output_content, bytearray):
                return bytes(pdf_output_content)
            elif isinstance(pdf_output_content, bytes): # If it's already bytes
                return pdf_output_content
            elif isinstance(pdf_output_content, str):
                # This would be the case for standard fpdf2 dest='S' behavior
                return pdf_output_content.encode('latin-1')
            else:
                logger.error(f"Unexpected type from FPDF output with dest='S': {type(pdf_output_content)}")
                return None

        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}", exc_info=True)
            return None

    # --- PDF Helper Methods ---

    def _add_pdf_section_title(self, pdf: FPDF, title: str):
        """Adds a formatted section title to the PDF."""
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, title, ln=True, border='B') # Add bottom border
        pdf.ln(2) # Add a little space after title

    def _add_df_to_pdf(self, pdf: FPDF, df: pd.DataFrame, title: str = "", max_cols=6):
        """Adds a Pandas DataFrame as a table to the PDF."""
        if df.empty:
            pdf.cell(0, 5, f"{title}: No data available.", ln=True)
            return

        pdf.set_font("Helvetica", "B", 10)
        if title:
            pdf.cell(0, 6, title, ln=True)
        pdf.ln(1)
        pdf.set_font("Helvetica", size=8)

        # Limit columns for better PDF layout
        df_to_render = df.iloc[:, :max_cols]
        if len(df.columns) > max_cols:
            pdf.set_font("Helvetica", "I", 8) # Italic font for note
            pdf.cell(0, 4, f"(Displaying first {max_cols} of {len(df.columns)} columns)", ln=True)
            pdf.set_font("Helvetica", size=8) # Reset font

        cols = df_to_render.columns.tolist()
        # Calculate available width and distribute
        available_width = pdf.w - pdf.l_margin - pdf.r_margin
        num_cols = len(cols)
        col_width = available_width / num_cols if num_cols > 0 else available_width
        # Ensure minimum width? Maybe not necessary, let FPDF handle wrapping.
        col_widths = [col_width] * num_cols

        # Header
        pdf.set_fill_color(224, 235, 255) # Light blue background
        for i, col_name in enumerate(cols):
            pdf.cell(col_widths[i], 7, str(col_name), border=1, align='C', fill=True)
        pdf.ln()

        # Data rows
        pdf.set_fill_color(255, 255, 255) # White background
        fill = False
        df_safe = self._safe_convert_to_str(df_to_render) # Ensure strings
        for index, row in df_safe.iterrows():
            # Calculate max height needed for this row (due to potential wrapping)
            row_height = 7 # Default height
            # This part is tricky with FPDF's basic cell; multi_cell is better for wrapping
            # but harder to align in a grid. We'll stick to basic cell and truncate.
            # For proper wrapping, a more complex table drawing logic would be needed.

            for i, item in enumerate(row):
                # Truncate long strings within cells
                cell_text = str(item)
                max_chars_per_cell = 40 # Adjust based on typical col_width
                if len(cell_text) > max_chars_per_cell:
                    cell_text = cell_text[:max_chars_per_cell-3] + '...'
                pdf.cell(col_widths[i], row_height, cell_text, border=1, align='L', fill=fill) # Left align data
            pdf.ln()
            fill = not fill # Alternate row fill

    def _generate_plot_image_buffer(self, corr_df: pd.DataFrame) -> io.BytesIO | None:
         """Generates a plot image in memory."""
         logger.debug("Generating correlation heatmap image for PDF...")
         try:
             fig, ax = plt.subplots(figsize=(8, 6)) # Adjust size as needed
             mask = np.triu(np.ones_like(corr_df, dtype=bool))
             sns.heatmap(corr_df, annot=True, fmt=".2f", cmap='coolwarm', ax=ax, mask=mask, linewidths=.5, cbar=False) # No cbar for smaller pdf image
             plt.xticks(rotation=45, ha='right')
             plt.yticks(rotation=0)
             plt.tight_layout()

             img_buffer = io.BytesIO()
             fig.savefig(img_buffer, format='png', dpi=150) # Save to buffer
             img_buffer.seek(0)
             plt.close(fig) # Close plot to free memory
             logger.debug("Correlation heatmap image generated successfully.")
             return img_buffer
         except Exception as e:
             logger.error(f"Could not generate plot image buffer: {e}", exc_info=True)
             plt.close(fig) # Ensure plot is closed even on error
             return None