// frontend/src/sections/QueryVizSection.js

import React, { useState } from 'react';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Form from 'react-bootstrap/Form';
import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Alert from 'react-bootstrap/Alert';
import Spinner from 'react-bootstrap/Spinner';
import Table from 'react-bootstrap/Table'; // For displaying raw data snippet
import ReactMarkdown from 'react-markdown'; // Import ReactMarkdown

// Import API service
import apiService from '../services/apiService';

// --- Helper Table Component (Should be defined or imported) ---
// Assuming SimpleResultTable exists as defined previously
function SimpleResultTable({ data, columns }) {
    if (!data || !Array.isArray(data) || data.length === 0) { // Added Array check
         return <p className="text-muted small mt-2">No tabular data to display.</p>;
    }
    // Check if first item is object to determine headers safely
    const firstItemIsObject = typeof data[0] === 'object' && data[0] !== null;
    const headers = columns
         ? columns.map(col => col.header)
         : (firstItemIsObject ? Object.keys(data[0]) : ['Value']); // Fallback header for non-object array

    const accessors = columns
         ? columns.map(col => col.accessor)
         : headers; // Use headers as accessors if no column config provided

     // If data is not objects, we only have one column to display
     if (!firstItemIsObject && headers.length === 1 && accessors.length === 1) {
        const singleAccessor = accessors[0]; // Not really used here, but for structure
     }

    return (
        <Table striped bordered hover responsive size="sm" className="small result-table">
            <thead>
                <tr>{headers.map((h, i) => <th key={i}>{h}</th>)}</tr>
            </thead>
            <tbody>
                {data.map((row, rIdx) => (
                    <tr key={rIdx}>
                        {firstItemIsObject ? (
                            accessors.map((acc, cIdx) => <td key={cIdx}>{String(row[acc] ?? '')}</td>)
                        ) : (
                            // Render the item directly if it's not an object (e.g., array of strings/numbers)
                            <td key={0}>{String(row ?? '')}</td>
                        )}
                    </tr>
                ))}
            </tbody>
        </Table>
    );
}


// --- Main QueryVizSection Component ---

// Props:
// - isLlmConfigured (boolean)
// - dataframeName (string | null)
// - setLoading (function): Set global loading state
// - setError (function): Set global error state

function QueryVizSection({ isLlmConfigured, dataframeName, setLoading, setError }) {
    // --- State for NL Query -> SQL -> NL Answer ---
    const [nlQuery, setNlQuery] = useState('');
    const [generatedSql, setGeneratedSql] = useState(''); // Store the generated SQL
    const [nlAnswer, setNlAnswer] = useState(''); // Store the final NL answer
    const [rawData, setRawData] = useState(null); // Store raw data snippet (e.g., array of objects)
    const [rawDataType, setRawDataType] = useState(''); // Store type of raw data
    const [llmSkipped, setLlmSkipped] = useState(false); // Flag if NL Answer LLM call was skipped
    const [isGeneratingSql, setIsGeneratingSql] = useState(false);
    const [isExecutingSql, setIsExecutingSql] = useState(false); // Covers SQL exec + NL Answer gen
    const [queryError, setQueryError] = useState('');
    const [showRawData, setShowRawData] = useState(false); // Toggle for raw data display

    // --- State for NL Viz ---
    const [vizRequest, setVizRequest] = useState('');
    const [plotParams, setPlotParams] = useState(null); // Store generated params
    const [plotDataUrl, setPlotDataUrl] = useState(''); // Store base64 data URL
    const [plotFilename, setPlotFilename] = useState('plot.png'); // Store suggested filename
    const [isGeneratingParams, setIsGeneratingParams] = useState(false);
    const [isGeneratingPlot, setIsGeneratingPlot] = useState(false);
    const [vizError, setVizError] = useState('');

    // --- Handlers for Querying ---
    const handleGenerateAndRunQuery = async () => {
        if (!nlQuery.trim()) { setQueryError("Please enter a question."); return; }
        if (!isLlmConfigured) { setQueryError("LLM must be configured."); return; }

        setQueryError(''); setError(null); setGeneratedSql(''); setNlAnswer('');
        setRawData(null); setRawDataType(''); setShowRawData(false); setLlmSkipped(false);
        setIsGeneratingSql(true); setIsExecutingSql(false); setLoading(true);

        try {
            // 1. Generate SQL Query
            const sqlResponse = await apiService.generateSqlQuery(nlQuery);
            const sql = sqlResponse.data.query;
            setGeneratedSql(sql);
            setIsGeneratingSql(false); // Done generating SQL

            // 2. Execute SQL Query and Get NL Answer
            setIsExecutingSql(true); // Now executing and getting answer
            try {
                const execResponse = await apiService.executeQueryAndGetAnswer(sql);
                // Update state with results from the backend
                setNlAnswer(execResponse.data.nl_answer || "Backend did not return an answer.");
                setRawData(execResponse.data.raw_data);
                setRawDataType(execResponse.data.raw_data_type || "Unknown");
                setLlmSkipped(execResponse.data.llm_skipped || false);
            } catch (execErr) {
                 console.error("SQL Execution/Answer Error:", execErr);
                 const execErrorMsg = execErr.response?.data?.error || execErr.message || "Query execution or answer generation failed.";
                 setQueryError(`Execution Failed: ${execErrorMsg}`);
                 // Decide if this should be a global error too
                 // setError(`Execution Failed: ${execErrorMsg}`);
            } finally {
                setIsExecutingSql(false); // Finished execution/answer attempt
            }

        } catch (genErr) {
            console.error("SQL Generation Error:", genErr);
            const genErrorMsg = genErr.response?.data?.error || genErr.message || "SQL generation failed.";
            setQueryError(`Generation Failed: ${genErrorMsg}`);
            // setError(genErrorMsg); // Show generation error globally?
            setIsGeneratingSql(false); // Ensure generating state stops
        } finally {
            setLoading(false); // Stop global loading only after all steps finish or fail
        }
    };

     const handleDownloadQueryResult = () => {
         // Trigger download via backend endpoint URL which handles re-executing SQL
         const downloadUrl = apiService.getQueryResultCsvUrl();
         console.log("Triggering Query Result CSV download from:", downloadUrl);
         window.open(downloadUrl, '_blank'); // Open URL in new tab to trigger download
     };

    // --- Handlers for Visualization ---
    const handleGeneratePlot = async () => {
        if (!vizRequest.trim()) { setVizError("Please describe the plot."); return; }
        if (!isLlmConfigured) { setVizError("LLM must be configured."); return; }

        setVizError(''); setError(null); setPlotParams(null); setPlotDataUrl('');
        setIsGeneratingParams(true); setIsGeneratingPlot(false); setLoading(true);

        try {
            // 1. Generate Plot Parameters
            const paramsResponse = await apiService.generateVizParams(vizRequest);
            const params = paramsResponse.data.params;
            setPlotParams(params);
            setIsGeneratingParams(false); // Done generating params

            // 2. Generate Plot Image Data
            setIsGeneratingPlot(true); // Now generating plot
            try {
                const plotResponse = await apiService.generatePlot(params);
                setPlotDataUrl(plotResponse.data.plot_data_url);
                setPlotFilename(plotResponse.data.filename || 'plot.png');
            } catch (plotErr) {
                 console.error("Plot Generation Error:", plotErr);
                 const plotErrorMsg = plotErr.response?.data?.error || plotErr.message || "Plot generation failed.";
                 setVizError(`Plot Generation Failed: ${plotErrorMsg}`);
                 // setError(plotErrorMsg); // Show plot error globally?
            } finally {
                setIsGeneratingPlot(false); // Finished plot generation attempt