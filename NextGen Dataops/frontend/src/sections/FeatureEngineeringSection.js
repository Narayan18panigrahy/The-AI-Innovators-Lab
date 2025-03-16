// frontend/src/sections/FeatureEngineeringSection.js

import React, { useState, useCallback } from 'react';
import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import Alert from 'react-bootstrap/Alert';
import Spinner from 'react-bootstrap/Spinner';
import ListGroup from 'react-bootstrap/ListGroup';

// Import API service
import apiService from '../services/apiService';

// Props:
// - onDataModified (function): Callback to notify App.js that working_df has changed
// - setLoading (function): Set global loading state
// - setError (function): Set global error state
// Note: Doesn't strictly need profileReport, suggestions based on current df columns

function FeatureEngineeringSection({ onDataModified, setLoading, setError }) {
    // --- Component State ---
    const [suggestions, setSuggestions] = useState([]);
    const [selectedFeatures, setSelectedFeatures] = useState({}); // Store selections: { index: true/false }
    const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
    const [isApplying, setIsApplying] = useState(false);
    const [localError, setLocalError] = useState('');
    const [applyLogs, setApplyLogs] = useState([]); // Store logs from backend apply response

    // --- Fetch Suggestions ---
    // useCallback to memoize the function
    const fetchSuggestions = useCallback(async () => {
        setIsLoadingSuggestions(true);
        setLocalError('');
        setError(null); // Clear global error
        setApplyLogs([]); // Clear previous logs
        setSuggestions([]); // Clear previous suggestions
        setSelectedFeatures({}); // Clear selections

        try {
            const response = await apiService.suggestFeatures();
            setSuggestions(response.data.suggestions || []);
            if (!response.data.suggestions || response.data.suggestions.length === 0) {
                 setLocalError("No specific feature suggestions were generated for the current columns.");
            }
        } catch (err) {
            console.error("Fetch Feature Suggestions Error:", err);
            const errorMsg = err.response?.data?.error || err.message || "Failed to fetch feature suggestions.";
            setError(errorMsg); // Set global error
            setLocalError("Could not retrieve feature suggestions.");
        } finally {
            setIsLoadingSuggestions(false);
        }
    }, [setError]); // Dependency: setError (stable)

    // --- Event Handlers ---
    const handleCheckboxChange = (index) => {
        setSelectedFeatures(prev => ({
            ...prev,
            [index]: !prev[index] // Toggle selection state
        }));
    };

    const handleApplySelected = async () => {
        setLocalError('');
        setError(null);
        setApplyLogs([]);

        const featuresToCreate = suggestions.filter((_, index) => selectedFeatures[index]);

        if (featuresToCreate.length === 0) {
            setLocalError("No features selected to create.");
            return;
        }

        setIsApplying(true);
        setLoading(true);

        try {
            const response = await apiService.applyFeatures(featuresToCreate); // Get the full response
            setApplyLogs(response.data.logs || []);
            onDataModified("feature engineering", response.data); // Pass the full response.data
            // Clear suggestions and selections after applying
            setSuggestions([]);
            setSelectedFeatures({});
            console.log("Features applied successfully");

        } catch (err) {
            console.error("Apply Features Error:", err);
            const errorMsg = err.response?.data?.error || err.message || "Failed to apply feature engineering actions.";
            setError(errorMsg);
            setLocalError("Failed to apply selected features.");
            onDataModified("feature_engineering_error", null); // Indicate error, no preview data
        } finally {
            setIsApplying(false);
            setLoading(false);
        }
    };

    // --- Render Logic ---
    return (
        <div className="feature-engineering-section">
            <Card>
                <Card.Header>Feature Engineering</Card.Header>
                <Card.Body>
                    <div className="mb-3">
                        <Button
                            variant="outline-info"
                            onClick={fetchSuggestions}
                            disabled={isLoadingSuggestions || isApplying}
                            size="sm"
                        >
                            {isLoadingSuggestions ? <Spinner animation="border" size="sm" /> : 'Suggest New Features'}
                        </Button>
                    </div>

                    {/* Display Local Errors */}
                    {localError && !isLoadingSuggestions && <Alert variant="warning" size="sm">{localError}</Alert>}

                    {/* Display Suggestions */}
                    {suggestions.length > 0 && (
                        <Form>
                            <p>Select new features to create:</p>
                            <ListGroup className="mb-3" style={{maxHeight: '300px', overflowY: 'auto'}}>
                                {suggestions.map((suggestion, index) => (
                                    <ListGroup.Item key={index} className="py-1 px-2">
                                        <Form.Check
                                            type="checkbox"
                                            id={`fe-check-${index}`}
                                            checked={!!selectedFeatures[index]}
                                            onChange={() => handleCheckboxChange(index)}
                                            label={
                                                <span className="small">
                                                    <strong>{suggestion.name}</strong> ({suggestion.type}): {suggestion.description}
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
                                disabled={isApplying || Object.values(selectedFeatures).every(v => !v)}
                                size="sm"
                            >
                                {isApplying ? (
                                    <>
                                        <Spinner as="span" animation="border" size="sm" /> Applying...
                                    </>
                                ) : (
                                    'Create Selected Features'
                                )}
                            </Button>
                        </Form>
                    )}

                     {/* Display Logs from Apply Action */}
                     {applyLogs.length > 0 && (
                        <div className="mt-3">
                            <h6>Application Logs:</h6>
                            <ListGroup variant="flush" style={{fontSize: '0.8rem'}}>
                                {applyLogs.map((log, index) => (
                                     <ListGroup.Item key={index} className="py-1 px-0">{log}</ListGroup.Item>
                                ))}
                            </ListGroup>
                        </div>
                     )}
