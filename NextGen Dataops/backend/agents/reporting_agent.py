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