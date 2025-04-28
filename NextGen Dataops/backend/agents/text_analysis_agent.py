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