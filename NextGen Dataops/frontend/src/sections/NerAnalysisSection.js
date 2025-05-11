// frontend/src/sections/NerAnalysisSection.js

import React, { useState, useEffect, useMemo } from 'react';
import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import Alert from 'react-bootstrap/Alert';
import Spinner from 'react-bootstrap/Spinner';
import Accordion from 'react-bootstrap/Accordion';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Table from 'react-bootstrap/Table';

// Import API service
import apiService from '../services/apiService';

// Simple Table component (or import from a shared components file)
function SimpleTable({ data, columns, title }) {
    if (!data || data.length === 0) return <p className="text-muted small mt-2">{title ? `${title}: ` : ''}No data.</p>;
    const headers = columns ? columns.map(col => col.header) : Object.keys(data[0] || {});
    const accessors = columns ? columns.map(col => col.accessor) : headers;
    return (
        <>
            {title && <h6 className="mt-2 mb-1 small text-muted">{title}</h6>}
            <Table striped bordered hover responsive size="sm" className="small ner-table">
                <thead>
                    <tr>{headers.map((h, i) => <th key={i}>{h}</th>)}</tr>
                </thead>
                <tbody>
                    {data.map((row, rIdx) => (
                        <tr key={rIdx}>{accessors.map((acc, cIdx) => <td key={cIdx}>{String(row[acc] ?? '')}</td>)}</tr>
                    ))}
                </tbody>
            </Table>
        </>
    );
}

// Props:
// - profileReport (object | null): Used to determine available text columns
// - nerReport (object | null): Current NER report state from App.js { col: { entities_by_type: {}, top_entities: [] }, ...}
// - setNerReport (function): Callback to update NER report state in App.js
// - setLoading (function): Set global loading state
// - setError (function): Set global error state

function NerAnalysisSection({ profileReport, nerReport, setNerReport, setLoading, setError }) {
    // --- Component State ---
    const [selectedColumns, setSelectedColumns] = useState([]); // Array of column names selected by user
    const [isLoading, setIsLoading] = useState(false); // Local loading for NER analysis
    const [localError, setLocalError] = useState('');

    // --- Determine Available Text Columns ---
    // Use useMemo to calculate only when profileReport changes
    const availableTextCols = useMemo(() => {
        if (profileReport && profileReport.data_types) {
            return Object.entries(profileReport.data_types)
                .filter(([col, dtype]) => ['object', 'string'].includes(String(dtype).toLowerCase()))
                .map(([col]) => col);
        }
        return [];
    }, [profileReport]);

    // Clear selection if available columns change (e.g., new file load)
    useEffect(() => {
        setSelectedColumns([]);
    }, [availableTextCols]);


    // --- Event Handlers ---
    const handleColumnSelectionChange = (event) => {
        const selectedOptions = Array.from(event.target.selectedOptions, option => option.value);
        setSelectedColumns(selectedOptions);
        setLocalError('');
    };

    const handleRunNer = async () => {
        if (selectedColumns.length === 0) {
            setLocalError("Please select at least one text column to analyze.");
            return;
        }

        setIsLoading(true);
        setLocalError('');
        setError(null);
        setLoading(true);

        try {
            const response = await apiService.analyzeNer(selectedColumns);
            setNerReport(response.data); // Update state in App.js

        } catch (err) {
            console.error("NER Analysis Error:", err);
            const errorMsg = err.response?.data?.error || err.message || "Failed to perform NER analysis.";
            setError(errorMsg);
            setLocalError("NER analysis failed.");
            setNerReport(null); // Clear previous report on error
        } finally {
            setIsLoading(false);
            setLoading(false);
        }
    };

    // --- Render Logic ---
    // Helper to render results for a single column
    const renderColumnNerResults = (columnName, data) => {
         if (!data || data.error) {
             return <p className="text-danger small mt-2">Analysis failed for '{columnName}': {data?.error || 'Unknown error'}</p>;
         }
         const types = data.entities_by_type || {};
         const top = data.top_entities || [];
         const typesArray = Object.entries(types).map(([type, count]) => ({ Type: type, Count: count })).sort((a,b)=>b.Count - a.Count);
         const topArray = top.map(([entity, count]) => ({ Entity: entity, Count: count }));

         if (typesArray.length === 0 && topArray.length === 0) {
             return <p className="text-muted small mt-2">No entities found in this column.</p>;
         }

         return (
             <Row key={columnName} className="mb-3">
                 <Col md={5} className="mb-2 mb-md-0">
                     <SimpleTable data={typesArray} columns={[{header: 'Entity Type', accessor: 'Type'}, {header: 'Count', accessor: 'Count'}]} title="Counts by Type"/>
                 </Col>
                 <Col md={7}>
                     <SimpleTable data={topArray} columns={[{header: 'Top Entities', accessor: 'Entity'}, {header: 'Count', accessor: 'Count'}]} title={`Top ${top.length} Entities`}/>
                 </Col>
             </Row>
         );
    }

    return (
        <div className="ner-analysis-section">
             {/* Keep Card structure if desired, or remove if just content needed in tab */}
            {/* <Card> <Card.Body> ... </Card.Body> </Card> */}
            <Form>
                <Form.Group className="mb-3" controlId="nerColumnSelect">
                    <Form.Label>Select Text Columns for Analysis</Form.Label>
                    {availableTextCols.length === 0 ? (
                        <Alert variant="secondary" size="sm">No text (object/string) columns found in the profile report, or profile not loaded.</Alert>
                    ) : (
                        <Form.Select
                            multiple
                            htmlSize={Math.min(5, availableTextCols.length + 1)}
                            value={selectedColumns}
                            onChange={handleColumnSelectionChange}
                            disabled={isLoading || availableTextCols.length === 0}
                            aria-describedby="nerColumnHelp"
                        >
                            {availableTextCols.map(col => (
                                <option key={col} value={col}>{col}</option>
                            ))}
                        </Form.Select>
                    )}
                    <Form.Text id="nerColumnHelp" muted>
                        Hold Ctrl (or Cmd) to select multiple. Analysis performed on current data state.
                    </Form.Text>
                </Form.Group>

                {localError && <Alert variant="danger" size="sm">{localError}</Alert>}

                <Button
                    variant="primary"
                    onClick={handleRunNer}
                    disabled={isLoading || selectedColumns.length === 0}
                    size="sm"
                    className="mb-3"
                >
                    {isLoading ? <><Spinner size="sm" /> Analyzing...</> : 'Run NER Analysis'}
                </Button>
            </Form>

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