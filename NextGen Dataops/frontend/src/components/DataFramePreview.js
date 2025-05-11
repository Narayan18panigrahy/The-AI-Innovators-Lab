// filepath: c:\Users\narpanig\OneDrive - Capgemini\Desktop\NextGen DataOps\frontend\src\components\DataFramePreview.js
import React from 'react';
import { Card, Table, Button, Spinner, Alert } from 'react-bootstrap';
import { FiDownload, FiGrid, FiAlertTriangle } from 'react-icons/fi';

const DataFramePreview = ({ dataPreviewJson, onDownloadExcel, isLoadingDownload, dataframeName }) => {
    if (!dataPreviewJson) {
        return null; // Don't render if no preview data
    }

    let columns = [];
    let data = [];
    let parseError = null;

    try {
        const parsed = JSON.parse(dataPreviewJson);
        columns = parsed.columns || [];
        data = parsed.data || [];
    } catch (e) {
        console.error("Error parsing data preview JSON:", e);
        parseError = "Error displaying data preview. The data might be in an unexpected format.";
    }

    const excelFileName = `${(dataframeName || 'dataset').split('.')[0]}_modified.xlsx`;

    return (
        <Card className="mt-4 shadow-sm">
            <Card.Header className="d-flex justify-content-between align-items-center bg-light border-bottom">
                <span className="h6 mb-0"><FiGrid className="me-2"/>Data Preview (First {data.length} Rows)</span>
                <Button
                    variant="success"
                    size="sm"
                    onClick={() => onDownloadExcel(excelFileName)}
                    disabled={isLoadingDownload || parseError}
                >
                    {isLoadingDownload ? (
                        <><Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" /> Downloading...</>
                    ) : (
                        <><FiDownload className="me-1" /> Download Full Data (Excel)</>
                    )}
                </Button>
            </Card.Header>
            <Card.Body style={{ maxHeight: '400px', overflowY: 'auto', overflowX: 'auto' }}>
                {parseError ? (
                    <Alert variant="danger"><FiAlertTriangle className="me-2"/>{parseError}</Alert>
                ) : columns.length === 0 || data.length === 0 ? (
                    <p className="text-muted text-center py-3">No data to display in preview.</p>
                ) : (
                    <Table striped bordered hover responsive size="sm" className="small data-preview-table">
                        <thead>
                            <tr>
                                {columns.map((col, index) => (
                                    <th key={index} title={col}>{col}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {data.map((row, rowIndex) => (
                                <tr key={rowIndex}>
                                    {row.map((cell, cellIndex) => (
                                        <td key={cellIndex}>
                                            {cell === null ? <i className="text-muted">null</i> : 
                                             (typeof cell === 'boolean' ? cell.toString() : 
                                             (typeof cell === 'object' ? JSON.stringify(cell) : String(cell)))}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </Table>
                )}
            </Card.Body>
        </Card>
    );
};

export default DataFramePreview;