// frontend/src/sections/LlmConfigSection.js

import React, { useState, useEffect } from 'react';
import Form from 'react-bootstrap/Form';
import Button from 'react-bootstrap/Button';
import Alert from 'react-bootstrap/Alert';
import Spinner from 'react-bootstrap/Spinner'; // For loading state on save

// Import API service
import apiService from '../services/apiService';

// Define supported providers and their required fields (mirror constants.py)
const SUPPORTED_PROVIDERS_CONFIG = {
    "azure": {
        "api_key": "Azure API Key",
        "api_base": "Azure API Base URL (Endpoint)",
        "api_version": "Azure API Version"
    },
    "nvidia": {
        "nvidia_api_key": "Nvidia API Key",
        "api_base": "Nvidia Base URL (Optional)" // Allow optional base for Nvidia
    }
};

// Helper function to get required credential keys for a provider
const getRequiredCredentials = (provider) => {
    return SUPPORTED_PROVIDERS_CONFIG[provider] ? Object.keys(SUPPORTED_PROVIDERS_CONFIG[provider]) : [];
};

// Component Props:
// - initialConfig (object | null): Current config loaded from backend session
// - isConfigured (boolean): Whether config is currently set on backend
// - onConfigSave (function): Callback function to notify App.js of successful save
// - setLoading (function): Callback to set global loading state in App.js
// - setError (function): Callback to set global error state in App.js

function LlmConfigSection({ initialConfig, isConfigured, onConfigSave, setLoading, setError }) {
    // --- Component State ---
    const [provider, setProvider] = useState('');
    const [modelName, setModelName] = useState('');
    const [credentials, setCredentials] = useState({});
    const [localError, setLocalError] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    // --- Effects ---
    // Initialize state when initialConfig prop changes
    useEffect(() => {
        const config = initialConfig || {};
        const initialProvider = config.provider || Object.keys(SUPPORTED_PROVIDERS_CONFIG)[0];

        setProvider(initialProvider);
        setModelName(config.model_name || '');

        const requiredKeys = getRequiredCredentials(initialProvider);
        const initialCreds = {};
        requiredKeys.forEach(key => {
            initialCreds[key] = config.credentials?.[key] || '';
        });
        if (initialProvider === 'nvidia' && config.credentials?.api_base) {
            initialCreds['api_base'] = config.credentials.api_base;
        }
        setCredentials(initialCreds);

    }, [initialConfig]);

    // --- Event Handlers ---
    const handleProviderChange = (event) => {
        const newProvider = event.target.value;
        setProvider(newProvider);
        const requiredKeys = getRequiredCredentials(newProvider);
        const newCreds = {};
        requiredKeys.forEach(key => { newCreds[key] = ''; });
        setCredentials(newCreds);
        setModelName('');
        setLocalError('');
    };

    const handleCredentialChange = (event) => {
        const { name, value } = event.target;
        setCredentials(prevCreds => ({ ...prevCreds, [name]: value }));
        setLocalError('');
    };

    const handleModelNameChange = (event) => {
        setModelName(event.target.value);
        setLocalError('');
    };

    const handleSave = async (event) => {
        event.preventDefault();
        setLocalError('');
        setError(null);
        setIsSaving(true);
        setLoading(true);

        let isValid = true;
        if (!modelName.trim()) {
            setLocalError("Model Name cannot be empty.");
            isValid = false;
        }
        const requiredKeys = getRequiredCredentials(provider);
        const currentCreds = { ...credentials };

        for (const key of requiredKeys) {
            if (!(provider === 'nvidia' && key === 'api_base') && !currentCreds[key]?.trim()) {
                setLocalError(`${SUPPORTED_PROVIDERS_CONFIG[provider][key]} cannot be empty.`);
                isValid = false;
                break;
            }
        }
        if (provider === 'nvidia' && !currentCreds.api_base?.trim()) {
            delete currentCreds.api_base;
        }

        if (!isValid) {
            setIsSaving(false);
            setLoading(false);
            return;
        }

        const configData = {
            provider: provider,
            model_name: modelName.trim(),
            credentials: currentCreds
        };

        try {
            const response = await apiService.saveLlmConfig(configData);
            console.log("LLM Config Save Response:", response.data);
            onConfigSave(configData);
        } catch (err) {
            console.error("LLM Config Save Error:", err);
            const errorMsg = err.response?.data?.error || err.message || "Failed to save LLM configuration.";
            setError(errorMsg);
            setLocalError("Save failed. See console or global error.");
        } finally {
            setIsSaving(false);
            setLoading(false);
        }
    };

    // --- Dynamic Help Text ---
     const getModelNameHelp = () => {
        // *** FIXED: Manual capitalization ***
        const providerName = (typeof provider === 'string' && provider.length > 0)
                             ? provider.charAt(0).toUpperCase() + provider.slice(1) // Manual capitalization
                             : 'Selected Provider'; // Fallback text

        let help = `Enter model name for ${providerName}. Examples:\n`;
        // Use the actual 'provider' state variable for comparison
        if (provider === "azure") {
             help += "- Your Azure Deployment Name (e.g., my-gpt4-deployment)";
        } else if (provider === "nvidia") {
             help += "- Nvidia Model ID (e.g., nvidia/llama3-70b-instruct)";
        }
        return help;
    }

    // --- Render Logic ---
    return (
        <div className="llm-config-section mb-3">
            <h3 className="h5">LLM Settings</h3>
            {isConfigured && <Alert variant="success" size="sm" className="py-1 px-2 mb-2">Configured</Alert>}

            <Form onSubmit={handleSave}>
                {/* Provider Selection */}
                <Form.Group className="mb-2" controlId="llmProviderSelect">
                    <Form.Label size="sm">Provider</Form.Label>
                    <Form.Select size="sm" value={provider} onChange={handleProviderChange}>
                        {Object.keys(SUPPORTED_PROVIDERS_CONFIG).map(p => (