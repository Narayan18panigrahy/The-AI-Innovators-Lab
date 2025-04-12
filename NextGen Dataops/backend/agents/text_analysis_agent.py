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