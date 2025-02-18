            {/* Display NER Results */}
            {nerReport && typeof nerReport === 'object' && Object.keys(nerReport).length > 0 && (
                <div className="mt-2">
                    <h5 className="mb-3">Analysis Results:</h5>
                    {/* Use Accordion to make results per column collapsible */}
                    <Accordion>
                        {Object.entries(nerReport).map(([colName, colData], index) => (
                             <Accordion.Item eventKey={String(index)} key={colName}>
                                 <Accordion.Header>Column: '{colName}'</Accordion.Header>
                                 <Accordion.Body>
                                     {renderColumnNerResults(colName, colData)}
                                 </Accordion.Body>
                             </Accordion.Item>
                        ))}
                    </Accordion>
                </div>
            )}
        </div>
    );
}

export default NerAnalysisSection;