// frontend/src/sections/SummarySection.js

import React, { useState } from 'react';
import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Alert from 'react-bootstrap/Alert';
import Spinner from 'react-bootstrap/Spinner';
import ReactMarkdown from 'react-markdown'; // Import ReactMarkdown

// Import API service
import apiService from '../services/apiService';

// Props:
// - profileReport (object | null): Needed for context check
// - nerReport (object | null): Optional context (passed to backend but not directly used here)
// - aiSummary (string | null): Current summary state from App.js
// - setAiSummary (function): Callback to update summary state in App.js
// - isLlmConfigured (boolean): To enable/disable generation button
// - setLoading (function): Callback to set global loading state
// - setError (function): Callback to set global error state

function SummarySection({
    profileReport,
    nerReport, // Passed down but backend uses session version if needed
    aiSummary,
    setAiSummary,
    isLlmConfigured,
    setLoading,
    setError
}) {
    const [isGenerating, setIsGenerating] = useState(false);
    const [localError, setLocalError] = useState('');

    const handleGenerateSummary = async () => {
        // Basic checks before calling API
        if (!isLlmConfigured) {
            setLocalError("LLM must be configured before generating a summary.");
            return;
        }
        if (!profileReport) {
             setLocalError("Profile report must be generated first to provide context.");
             return;
        }

        setIsGenerating(true);
        setLocalError('');
        setError(null); // Clear global error
        setLoading(true); // Use global loading indicator

        try {
            // No request body needed, API uses session data for context
            const response = await apiService.generateSummary();
            setAiSummary(response.data.summary); // Update state in App.js via callback

        } catch (err) {
            console.error("AI Summary Generation Error:", err);
            const errorMsg = err.response?.data?.error || err.message || "Failed to generate AI summary.";
            setError(errorMsg); // Set global error
            setLocalError("Summary generation failed."); // Show local indication
            setAiSummary(null); // Clear any previous summary on error
        } finally {
            setIsGenerating(false);
            setLoading(false);
        }
    };

    return (
        <div className="summary-section">
            <Card>
                <Card.Header>AI Generated Data Summary</Card.Header>
                <Card.Body>
                    {/* Button to trigger generation */}
                    {!aiSummary && ( // Show button only if no summary exists
                         <div className="mb-3 text-center">
                             <Button
                                 variant="info"
                                 onClick={handleGenerateSummary}
                                 disabled={isGenerating || !isLlmConfigured || !profileReport}
                             >
                                 {isGenerating ? (
                                     <>
                                         <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                                         {' '}Generating...
                                     </>
                                 ) : (
                                     'Generate Summary'
                                 )}
                             </Button>
                             {!isLlmConfigured && <p className="text-warning small mt-2">LLM must be configured.</p>}
                             {!profileReport && isLlmConfigured && <p className="text-warning small mt-2">Profile report needed first.</p>}
                         </div>
                    )}

                    {/* Display local error */}
                    {localError && <Alert variant="danger">{localError}</Alert>}

                    {/* Display the summary */}
                    {aiSummary && (
                        <div>
                            {/* Wrap ReactMarkdown in a div and apply className there */}
                            <div className="markdown-content"> 
                                <ReactMarkdown
                                    children={aiSummary}
                                />
                            </div>
                             <Button variant="secondary" size="sm" onClick={handleGenerateSummary} disabled={isGenerating} className="mt-3">
                                {isGenerating ? 'Regenerating...' : 'Regenerate Summary'}
                            </Button>
                        </div>
                    )}
                </Card.Body>
            </Card>
        </div>
    );
}

export default SummarySection;