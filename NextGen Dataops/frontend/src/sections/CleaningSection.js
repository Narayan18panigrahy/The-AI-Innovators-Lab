// frontend/src/sections/CleaningSection.js

import React, { useState, useEffect, useCallback } from 'react';
import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import Alert from 'react-bootstrap/Alert';
import Spinner from 'react-bootstrap/Spinner';
import ListGroup from 'react-bootstrap/ListGroup';
import apiService from '../services/apiService';

function CleaningSection({ profileReport, onDataModified, setLoading, setError }) {
    const [suggestions, setSuggestions] = useState([]);
    const [selectedActions, setSelectedActions] = useState({});
    const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
    const [isApplying, setIsApplying] = useState(false);
    const [localError, setLocalError] = useState('');
    const [applyLogs, setApplyLogs] = useState([]);

    const fetchSuggestions = useCallback(async () => {
        if (!profileReport) {
            setSuggestions([]);
            // Optionally set a local message indicating profile needed
            setLocalError("Generate profile report first to get suggestions.");
            return;
        }
        setIsLoadingSuggestions(true);
        setLocalError('');
        setError(null);
        setApplyLogs([]);
        setSuggestions([]);
        setSelectedActions({});

        try {
            const response = await apiService.suggestCleaning(); // Calls GET /api/suggest_cleaning
            setSuggestions(response.data.suggestions || []);
            if (!response.data.suggestions || response.data.suggestions.length === 0) {
                 setLocalError("No specific cleaning suggestions were generated based on the current profile.");
            }
        } catch (err) {
            console.error("Fetch Cleaning Suggestions Error:", err);
            const errorMsg = err.response?.data?.error || err.message || "Failed to fetch cleaning suggestions.";
            setError(errorMsg);
            setLocalError("Could not retrieve cleaning suggestions.");
        } finally {
            setIsLoadingSuggestions(false);
        }
    }, [profileReport, setError]); // Re-fetch if profile changes (though profile is static now)

    const handleCheckboxChange = (index) => {
        setSelectedActions(prev => ({ ...prev, [index]: !prev[index] }));
    };

    const handleApplySelected = async () => {
        setLocalError('');
        setError(null);
        setApplyLogs([]);

        const actionsToApply = suggestions.filter((_, index) => selectedActions[index]);

        if (actionsToApply.length === 0) {
            setLocalError("No cleaning actions selected to apply.");
            return;
        }

        setLoading(true); // Global loading for App.js
        setIsApplying(true);

        try {
            const response = await apiService.applyCleaning(actionsToApply); // Get the full response
            setApplyLogs(response.data.logs || []);
            onDataModified("cleaning", response.data); // Pass the full response.data
            // Clear suggestions and selections after applying
            setSuggestions([]);
            setSelectedActions({});
            console.log("Cleaning actions applied successfully");
        } catch (err) {
            console.error("Apply Cleaning Error:", err);
            const errorMsg = err.response?.data?.error || err.message || "Failed to apply cleaning actions.";
            setError(errorMsg); // Set global error
            setLocalError("Failed to apply selected actions.");
            onDataModified("cleaning_error", null); // Indicate error, no preview data
        } finally {
            setIsApplying(false);
            setLoading(false); // Global loading for App.js
        }
    };

    const canSuggest = !!profileReport;

    return (
        <div className="cleaning-section">
            <Card>
                <Card.Header>Data Cleaning</Card.Header>
                <Card.Body>
                    <div className="mb-3">
                        <Button
                            variant="outline-info"
                            onClick={fetchSuggestions}
                            disabled={!canSuggest || isLoadingSuggestions || isApplying}
                            size="sm"
                        >
                            {isLoadingSuggestions ? <Spinner animation="border" size="sm" /> : 'Suggest Cleaning Steps'}
                        </Button>
                        {/* Display requirement message more clearly */}
                        {!canSuggest && <span className="text-muted small ms-2">Profile report required.</span>}
                    </div>

                    {localError && !isLoadingSuggestions && <Alert variant="warning" size="sm">{localError}</Alert>}

                    {suggestions.length > 0 && (
                        <Form onSubmit={(e) => e.preventDefault()}> {/* Prevent accidental form submission */}
                            <p>Select cleaning actions to apply:</p>
                            <ListGroup className="mb-3 suggestions-list" style={{maxHeight: '300px', overflowY: 'auto'}}>
                                {suggestions.map((suggestion, index) => (
                                    <ListGroup.Item key={index} className="py-1 px-2">
                                        <Form.Check
                                            type="checkbox"
                                            id={`clean-check-${index}`}
                                            checked={!!selectedActions[index]}
                                            onChange={() => handleCheckboxChange(index)}
                                            label={
                                                <span className="small">
                                                    <strong>{suggestion.column}:</strong> ({suggestion.issue}) {'->'} {suggestion.suggestion}
                                                </span>
                                            }
                                            disabled={isApplying}
                                        />
                                    </ListGroup.Item>
                                ))}
                            </ListGroup>

                            <Button
                                variant="success"
                                onClick={handleApplySelected}
                                disabled={isApplying || Object.values(selectedActions).every(v => !v)}
                                size="sm"
                            >
                                {isApplying ? <><Spinner size="sm"/> Applying...</> : 'Apply Selected Steps'}
                            </Button>
                        </Form>
                    )}

                     {applyLogs.length > 0 && (
                        <div className="mt-3">
                            <h6>Application Logs:</h6>
                            <ListGroup variant="flush" className="logs-list" style={{fontSize: '0.8rem'}}>
                                {applyLogs.map((log, index) => (
                                     <ListGroup.Item key={index} className="py-1 px-0 border-0">{log}</ListGroup.Item>
                                ))}
                            </ListGroup>
                        </div>
                     )}
                </Card.Body>
            </Card>
        </div>
    );
}

export default CleaningSection;