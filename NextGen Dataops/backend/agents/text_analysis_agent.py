# -*- coding: utf-8 -*-
"""
text_analysis_agent.py

Defines the TextAnalysisAgent class responsible for performing text analysis,
specifically Named Entity Recognition (NER), on selected DataFrame columns using spaCy.
"""


import pandas as pd
import spacy
from collections import Counter
# import traceback # No longer needed with logger.error(exc_info=True)
import logging # Import logging

# Get a logger specific to this module
logger = logging.getLogger(__name__)

class TextAnalysisAgent:
    """
    Agent responsible for performing text analysis tasks like NER.
    """
    SPACY_MODEL_NAME = "en_core_web_sm" # Use the small English model

    def __init__(self):
        """Initializes the TextAnalysisAgent and loads the spaCy model."""
        self.nlp = self._load_spacy_model()
        if self.nlp:
            logger.info(f"spaCy model '{self.SPACY_MODEL_NAME}' loaded successfully.")
        else:
            # Error logged by _load_spacy_model
            pass

    def _load_spacy_model(self):
        """Loads the specified spaCy language model."""
        try:
            logger.info(f"Attempting to load spaCy model: {self.SPACY_MODEL_NAME}")
            # Disable components we don't need for NER to speed up processing
            # Adjust based on actual needs if using other components later.
            disabled_pipes = ["tok2vec", "tagger", "parser", "attribute_ruler", "lemmatizer"]
            return spacy.load(self.SPACY_MODEL_NAME, disable=disabled_pipes)
        except OSError:
            logger.error(
                f"spaCy model '{self.SPACY_MODEL_NAME}' not found. "
                f"Please download it by running:\n"
                f"`python -m spacy download {self.SPACY_MODEL_NAME}`"
            )
            # Stop the app or return None to indicate failure
            # Returning None allows the calling code to handle the absence of the model
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading the spaCy model: {e}", exc_info=True)
            return None

    def analyze_entities(self, df: pd.DataFrame, columns_to_analyze: list[str]) -> dict | None:
        """
        Performs Named Entity Recognition (NER) on the specified text columns.

        Args:
            df (pd.DataFrame): The DataFrame containing the text data.
            columns_to_analyze (list[str]): A list of column names to analyze.

        Returns:
            dict | None: A dictionary where keys are column names and values are
                         dicts containing 'entities_by_type' and 'top_entities'.
                         Returns None if the spaCy model failed to load or on critical error.
        """
        if self.nlp is None:
            logger.error("NER analysis cannot proceed because the spaCy model failed to load.")
            return None # Indicate failure due to model load issue

        if df is None or df.empty:
            logger.warning("Input DataFrame is empty. Skipping NER analysis.")
            return {}

        if not columns_to_analyze:
            logger.warning("No columns selected for NER analysis.")
            return {}

        logger.info(f"Starting NER analysis on columns: {columns_to_analyze}")
        ner_report = {}

        for col_name in columns_to_analyze:
            if col_name not in df.columns:
                logger.warning(f"Column '{col_name}' selected for NER not found in DataFrame. Skipping.")
                ner_report[col_name] = {"error": f"Column '{col_name}' not found."}
                continue

            # Ensure the column is treated as string and handle NaNs
            try:
                # Convert to string and fill NaN with empty string to avoid errors in nlp.pipe
                texts = df[col_name].astype(str).fillna('').tolist()
                if not texts:
                     logger.warning(f"Column '{col_name}' contains no text data after cleaning NaNs.")
                     ner_report[col_name] = {'entities_by_type': {}, 'top_entities': []}
                     continue

                logger.debug(f"Processing column '{col_name}' with {len(texts)} text entries...")

                entities_by_type = Counter()
                all_entities = []

                # Process text in batches using nlp.pipe for efficiency
                # Adjust batch_size based on memory constraints and text length
                batch_size = 1000
                doc_count = 0
                for doc in self.nlp.pipe(texts, batch_size=batch_size):
                    doc_count += 1
                    for ent in doc.ents:
                        entities_by_type[ent.label_] += 1
                        # Store text and label for finding top entities later
                        # Normalize whitespace and case for better aggregation
                        entity_text = ' '.join(ent.text.split()).lower()
                        if entity_text: # Avoid adding empty strings
                            all_entities.append(entity_text)

                    # Optional: Provide progress feedback for large columns
                    if doc_count % (batch_size * 10) == 0: # Every 10 batches
                         logger.debug(f"   ...processed {doc_count} entries in '{col_name}'")

                logger.debug(f"Finished processing {doc_count} entries in '{col_name}'.")

                # Find top N most frequent specific entities
                top_n = 20 # Number of top entities to show
                top_entities_counter = Counter(all_entities)
                top_entities_list = top_entities_counter.most_common(top_n)

                ner_report[col_name] = {
                    'entities_by_type': dict(entities_by_type), # Convert Counter to dict
                    'top_entities': top_entities_list
                }
                logger.debug(f"NER results for '{col_name}': Types={len(entities_by_type)}, TopEntities={len(top_entities_list)}")

            except Exception as e:
                logger.error(f"An error occurred during NER analysis for column '{col_name}': {e}", exc_info=True)
                ner_report[col_name] = {"error": f"Analysis failed: {e}"}

        logger.info("NER analysis complete for selected columns.")
        return ner_report