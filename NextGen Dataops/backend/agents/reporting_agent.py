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