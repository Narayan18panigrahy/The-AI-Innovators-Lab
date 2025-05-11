// frontend/src/sections/ProfileDisplaySection.js

import React from 'react';
import Accordion from 'react-bootstrap/Accordion';
import Card from 'react-bootstrap/Card';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Table from 'react-bootstrap/Table';
import Button from 'react-bootstrap/Button';
import apiService from '../services/apiService';

// --- Helper Components (Keep MetricDisplay and SimpleTable) ---
function MetricDisplay({ label, value }) {
    const displayValue = (typeof value === 'number' && !isNaN(value))
                         ? value.toLocaleString()
                         : (value ?? 'N/A');
    return ( <Col><Card body className="text-center p-2 mb-2"><h6 className="card-subtitle mb-1 text-muted small">{label}</h6><p className="card-text h5 mb-0">{displayValue}</p></Card></Col> );
}

function SimpleTable({ data, columns, title }) {
    if (!data || data.length === 0) {
        return <p className="text-muted small mt-2">{title ? `${title}: ` : ''}No data available.</p>;
    }
    const dataArray = Array.isArray(data) ? data : [];
    const headers = columns ? columns.map(col => col.header) : (dataArray.length > 0 ? Object.keys(dataArray[0]) : []);
    const accessors = columns ? columns.map(col => col.accessor) : headers;
    const isObjectRow = dataArray.length > 0 && typeof dataArray[0] === 'object' && dataArray[0] !== null;

    return (
        <>
            {title && <h6 className="mt-2 mb-1">{title}</h6>}
            <Table striped bordered hover responsive size="sm" className="small">
                <thead>
                    <tr>{headers.map((header, index) => <th key={index}>{header}</th>)}</tr>
                </thead>
                <tbody>
                    {dataArray.map((row, rowIndex) => (
                        <tr key={rowIndex}>
                            {isObjectRow ? accessors.map((accessor, colIndex) => (
                                <td key={colIndex}>{row[accessor] !== null && row[accessor] !== undefined ? String(row[accessor]) : ''}</td>
                            )) : (
                                <td key={0}>{String(row ?? '')}</td>
                            )}
                        </tr>
                    ))}
                </tbody>
            </Table>
        </>
    );
}

// --- Main Profile Display Component ---
function ProfileDisplaySection({ report, dataframeName }) {

    if (!report) {
        return <p>Profile report is not yet available.</p>;
    }

    // --- Extract data from report prop ---
    // Use const for variables defined in this scope
    const basicInfo = report.basic_info || {};
    const missingValuesData = report.missing_values || {}; // Renamed variable here for clarity
    const dataTypes = report.data_types || {};
    const stats = report.descriptive_stats || {};
    const cardinality = report.cardinality || {};
    const outlierInfo = report.outlier_detection || {};
    const correlationMatrix = report.correlation_matrix;

    // --- Prepare Data for Tables using JavaScript ---
    const dataTypesArray = Object.entries(dataTypes).map(([col, type]) => ({ Column: col, DataType: type }));

    // *** FIX: Use the correct variable name 'missingValuesData' here ***
    const missingValuesArray = Object.entries(missingValuesData)
        .map(([col, data]) => ({
            Column: col,
            'Missing Count': data?.count ?? 'N/A',
            'Missing (%)': data?.percentage ?? 'N/A',
        }))
        .filter(item => (item['Missing Count'] > 0))
        .sort((a, b) => (b['Missing (%)'] ?? 0) - (a['Missing (%)'] ?? 0));

    // --- Process Statistics Data ---
    const numericStats = stats.numeric;
    const catStats = stats.categorical;

    const formatStatsForTable = (statsObj) => {
        // ... (keep the formatStatsForTable helper function exactly as before) ...
         if (!statsObj || typeof statsObj !== 'object' || Object.keys(statsObj).length === 0) {
            return { data: [], columns: [] };
        }
        const statistics = Object.keys(statsObj);
        const columns = statistics.length > 0 ? Object.keys(statsObj[statistics[0]]) : [];
        const tableColumns = [
            { header: 'Statistic', accessor: 'Statistic' },
            ...columns.map(col => ({ header: col, accessor: col }))
        ];
        const tableData = statistics.map(stat => {
            const row = { Statistic: stat };
            columns.forEach(col => {
                 const value = statsObj[stat]?.[col];
                 row[col] = (typeof value === 'number') ? Number(value.toFixed(3)) : (value ?? 'N/A');
            });
            return row;
        });
        return { data: tableData, columns: tableColumns };
    };

    const { data: numericStatsArray, columns: numericStatsCols } = formatStatsForTable(numericStats);
    const { data: catStatsArray, columns: catStatsCols } = formatStatsForTable(catStats);

    const cardinalityArray = Object.entries(cardinality)
        .map(([col, count]) => ({ Column: col, 'Unique Values': count }))
        .sort((a, b) => (b['Unique Values'] ?? 0) - (a['Unique Values'] ?? 0));

    // --- Event Handlers ---
    const handleDownloadPdf = () => {
        const downloadUrl = apiService.getProfilePdfUrl();
        console.log("Triggering PDF download from:", downloadUrl);
        window.location.href = downloadUrl;
    };

    // --- Render Logic (Keep exactly as before) ---
    return (
        <div className="profile-display-section">
            {/* Header and Download Button */}
            <Row className="mb-3 align-items-center">
                 {/* ... (header content) ... */}
                 <Col xs="auto">
                     <Button variant="outline-primary" size="sm" onClick={handleDownloadPdf}>
                        Download PDF Report
                    </Button>
                </Col>
            </Row>

            {/* Overview Metrics */}
            <Row xs={1} sm={2} md={4} className="mb-3">
                <MetricDisplay label="Rows" value={basicInfo.rows} />
                {/* ... (other metrics) ... */}
                <MetricDisplay label="Memory Usage" value={basicInfo.memory_usage} />
            </Row>

            <Accordion defaultActiveKey={['0']} alwaysOpen>
                {/* Data Types & Missing Values */}
                <Accordion.Item eventKey="0">
                    <Accordion.Header>Data Types & Missing Values</Accordion.Header>
                    <Accordion.Body>
                        <Row>
                            <Col md={5}>
                                <SimpleTable title="Data Types" data={dataTypesArray} columns={[{ header: 'Column', accessor: 'Column' }, { header: 'Data Type', accessor: 'DataType' }]}/>
                            </Col>
                            <Col md={7}>
                                {missingValuesArray.length > 0 ? (
                                     <SimpleTable title="Columns with Missing Values" data={missingValuesArray} columns={[{ header: 'Column', accessor: 'Column' }, { header: 'Missing Count', accessor: 'Missing Count' }, { header: 'Missing (%)', accessor: 'Missing (%)' }]}/>
                                ) : ( <p className="mt-2">No missing values found.</p> )}
                                {/* TODO: Add Missing Value Bar Chart */}
                            </Col>
                        </Row>
                    </Accordion.Body>
                </Accordion.Item>

                {/* Descriptive Statistics */}
                <Accordion.Item eventKey="1">
                   {/* ... (Stats Table rendering exactly as before, using numericStatsArray etc.) ... */}
                   <Accordion.Header>Descriptive Statistics</Accordion.Header>
                   <Accordion.Body>
                       {numericStatsArray.length > 0 ? ( <SimpleTable title="Numeric Columns" data={numericStatsArray} columns={numericStatsCols} /> ) : ( <p>No numeric statistics available.</p>)}
                       <hr/>
                       {catStatsArray.length > 0 ? ( <SimpleTable title="Categorical/Object Columns" data={catStatsArray} columns={catStatsCols} /> ) : ( <p>No categorical/object statistics available.</p>)}
                    </Accordion.Body>
                </Accordion.Item>

                {/* Cardinality */}
                <Accordion.Item eventKey="2">
                   {/* ... (Cardinality Table rendering exactly as before) ... */}
                   <Accordion.Header>Value Cardinality (Unique Counts)</Accordion.Header>
                   <Accordion.Body>
                        <SimpleTable data={cardinalityArray} columns={[{ header: 'Column', accessor: 'Column' }, { header: 'Unique Values', accessor: 'Unique Values' }]}/>
                   </Accordion.Body>
                </Accordion.Item>

                 {/* Numerical Analysis Details */}
                 <Accordion.Item eventKey="3">
                   {/* ... (Numerical Analysis rendering exactly as before) ... */}
                    <Accordion.Header>Numerical Analysis Details</Accordion.Header>
                    <Accordion.Body>
                        {/* ... (Correlation placeholder) ... */}
                        {/* ... (Skew/Kurt placeholder) ... */}
                        {/* ... (Outlier display) ... */}
                        <h6>Correlation Matrix</h6>
                        {correlationMatrix ? ( /* ... */ <pre>{JSON.stringify(correlationMatrix, null, 2)}</pre> ) : (<p>Not available.</p>)}
                         <hr/>
                         <h6>Skewness & Kurtosis</h6><p className="text-muted small">(Tables coming soon)</p>
                         <hr/>
                         <h6>Outlier Detection (DBSCAN)</h6>
                        {outlierInfo && !outlierInfo.error ? ( <Row xs={1} sm={3}><MetricDisplay label="Potential Outliers" value={outlierInfo.outlier_count} /> <MetricDisplay label="Outlier (%)" value={outlierInfo.outlier_percentage ? `${outlierInfo.outlier_percentage}%` : 'N/A'} /> <MetricDisplay label="Rows Analyzed" value={outlierInfo.rows_analyzed} /></Row> ): ( <p className="text-muted small">{outlierInfo.error || "Outlier info not available."}</p> )}
                         {outlierInfo?.rows_dropped_nan > 0 && <p className="text-muted small mt-1">Note: {outlierInfo.rows_dropped_nan.toLocaleString()} rows with NaN excluded.</p>}
                         {outlierInfo?.parameters && <p className="text-muted small mt-1">Params: eps={outlierInfo.parameters.eps}, min_samples={outlierInfo.parameters.min_samples}</p>}
                    </Accordion.Body>
                </Accordion.Item>
            </Accordion>
        </div>
    );
}

export default ProfileDisplaySection;