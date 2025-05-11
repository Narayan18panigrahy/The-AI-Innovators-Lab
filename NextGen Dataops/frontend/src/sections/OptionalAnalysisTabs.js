// frontend/src/sections/OptionalAnalysisTabs.js

import React, { useState } from 'react';
import Tabs from 'react-bootstrap/Tabs';
import Tab from 'react-bootstrap/Tab';

// Import placeholder section components (Create these files later)
import NerAnalysisSection from './NerAnalysisSection';
import CleaningSection from './CleaningSection';
import FeatureEngineeringSection from './FeatureEngineeringSection';
import SummarySection from './SummarySection';

// Props:
// - profileReport (object | null): Passed down for context if needed by child sections
// - nerReport (object | null): Current NER report state from App.js
// - aiSummary (string | null): Current AI summary state from App.js
// - isLlmConfigured (boolean): Passed down for enabling/disabling LLM features
// - setNerReport (function): Callback to update NER report state in App.js
// - setAiSummary (function): Callback to update AI summary state in App.js
// - onDataModified (function): Callback to notify App.js when data is changed by Cleaning/FE
// - setLoading (function): Callback to set global loading state
// - setError (function): Callback to set global error state

function OptionalAnalysisTabs({
    profileReport,
    nerReport,
    aiSummary,
    isLlmConfigured,
    setNerReport,
    setAiSummary,
    onDataModified,
    setLoading,
    setError
}) {
    const [activeTab, setActiveTab] = useState('ner'); // Default active tab key

    return (
        <div className="optional-analysis-tabs">
            <h2 className="h4 mb-3">Optional Analysis & Transformation</h2>
            <Tabs
                id="optional-analysis-controlled-tabs"
                activeKey={activeTab}
                onSelect={(k) => setActiveTab(k)}
                className="mb-3"
                justify // Justify tabs to fill width
            >
                {/* --- NER Tab --- */}
                <Tab eventKey="ner" title="Text Analysis (NER)">
                    {/* Pass necessary props down to the NER section component */}
                    <NerAnalysisSection
                        profileReport={profileReport} // May not be needed directly by NER section
                        nerReport={nerReport}
                        setNerReport={setNerReport}
                        setLoading={setLoading}
                        setError={setError}
                    />
                </Tab>

                {/* --- Cleaning Tab --- */}
                <Tab eventKey="cleaning" title="Data Cleaning">
                     {/* Pass necessary props down to the Cleaning section component */}
                     <CleaningSection
                        profileReport={profileReport} // Cleaning suggestions based on profile
                        onDataModified={onDataModified} // Notify App.js after applying
                        setLoading={setLoading}
                        setError={setError}
                     />
                </Tab>

                {/* --- Feature Engineering Tab --- */}
                <Tab eventKey="feature_engineering" title="Feature Engineering">
                     {/* Pass necessary props down to the FE section component */}
                     <FeatureEngineeringSection
                        onDataModified={onDataModified} // Notify App.js after applying
                        setLoading={setLoading}
                        setError={setError}
                     />
                </Tab>

                {/* --- AI Summary Tab --- */}
                <Tab eventKey="summary" title="AI Summary">
                     {/* Pass necessary props down to the Summary section component */}
                     <SummarySection
                        profileReport={profileReport} // Needed for context
                        nerReport={nerReport} // Optional context
                        aiSummary={aiSummary}
                        setAiSummary={setAiSummary}
                        isLlmConfigured={isLlmConfigured} // Enable/disable button
                        setLoading={setLoading}
                        setError={setError}
                     />
                </Tab>
            </Tabs>
        </div>
    );
}

export default OptionalAnalysisTabs;