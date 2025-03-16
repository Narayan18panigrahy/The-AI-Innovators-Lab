// App.js
import React, { useState, useEffect, useCallback } from 'react';
import Container from 'react-bootstrap/Container';
// import Row from 'react-bootstrap/Row'; // No longer directly used in App.js
// import Col from 'react-bootstrap/Col';   // No longer directly used in App.js
import Alert from 'react-bootstrap/Alert';
import Spinner from 'react-bootstrap/Spinner';
import Navbar from 'react-bootstrap/Navbar';
import Card from 'react-bootstrap/Card';
import Button from 'react-bootstrap/Button';
import Offcanvas from 'react-bootstrap/Offcanvas';
import Accordion from 'react-bootstrap/Accordion'; // Import Accordion
// import Collapse from 'react-bootstrap/Collapse'; // Replaced by Accordion for these sections
import 'bootstrap/dist/css/bootstrap.min.css';
import './assets/styles.css';
import {
    FiCpu, FiDatabase, FiUploadCloud, FiSettings, FiBarChart2,
    FiMessageSquare, FiAlertTriangle, FiMenu, FiX, // FiMenu, FiX might be for future mobile toggle if Offcanvas responsive is overridden
    FiCheckCircle, FiXCircle, FiChevronDown, FiChevronUp, // FiChevronDown/Up might not be needed if Accordion handles its own icons
} from 'react-icons/fi';
import { FaChevronLeft, FaChevronRight } from 'react-icons/fa';

import LlmConfigSection from './sections/LlmConfigSection';
import FileUploadSection from './sections/FileUploadSection';
import ProfileDisplaySection from './sections/ProfieDisplaySection';
import OptionalAnalysisTabs from './sections/OptionalAnalysisTabs';
import QueryVizSection from './sections/QueryVizSection';
import DataFramePreview from './components/DataFramePreview';
import apiService from './services/apiService';

function App() {
    const [appState, setAppState] = useState({
        session_id: null,
        dataframeName: null,
        llmConfig: null,
        llmConfigured: false,
        profileReport: null,
        workingDataAvailable: false,
        pg_table_name: null,
        nerReport: null,
        aiSummary: null,
        dataPreview: null,
    });
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    // const [showLlmConfig, setShowLlmConfig] = useState(true); // Replaced by Accordion activeKey
    const [activeAccordionKey, setActiveAccordionKey] = useState('0'); // Default to LLM config open
    const [showSidebar, setShowSidebar] = useState(true);
    const [isDownloadingExcel, setIsDownloadingExcel] = useState(false);
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

    const fetchAndSetProfileReport = useCallback(async (isInitialLoad = false) => {
        if (!appState.pg_table_name && !isInitialLoad) return;
        setIsLoading(true); setError(null);
        try {
            const response = await apiService.refreshProfileReport();
            if (response.data && response.data.profile_report) {
                setAppState(prev => ({ ...prev, profileReport: response.data.profile_report, workingDataAvailable: true }));
            } else {
                setAppState(prev => ({ ...prev, profileReport: null }));
            }
        } catch (err) {
            const errorMsg = err.response?.data?.error || err.message || "Failed to refresh profile report.";
            setError(errorMsg); setAppState(prev => ({ ...prev, profileReport: null }));
        } finally { setIsLoading(false); }
    }, [appState.pg_table_name]);

    const handleDataModified = useCallback(async (modificationType, modificationResponseData) => {
        setIsLoading(true);
        setAppState(prev => ({
            ...prev, profileReport: null, nerReport: null, aiSummary: null,
            dataPreview: modificationResponseData?.data_preview || null,
        }));
        await fetchAndSetProfileReport();
    }, [fetchAndSetProfileReport]);

    const handleDataLoaded = useCallback((uploadResponseData) => {
        setError(null);
        const profileData = uploadResponseData?.profile_report || null;
        const dataAvailable = profileData !== null;
        setAppState(prevState => ({
            ...prevState,
            dataframeName: uploadResponseData?.dataframe_name || null,
            profileReport: profileData,
            workingDataAvailable: dataAvailable,
            pg_table_name: uploadResponseData?.db_table || prevState.pg_table_name,
            nerReport: null, aiSummary: null, dataPreview: null,
        }));
        // Optionally, switch accordion to data if LLM is configured, or keep LLM open
        if (appState.llmConfigured) {
            // setActiveAccordionKey('1'); // Or null to close all if not alwaysOpen
        } else {
            setActiveAccordionKey('0');
        }
    }, [appState.llmConfigured]);


    useEffect(() => {
        const fetchSessionData = async () => {
            setIsLoading(true);
            try {
                const response = await apiService.getSessionState();
                const data = response.data;
                setAppState(prev => ({
                    ...prev, session_id: data.session_id, dataframeName: data.dataframe_name,
                    llmConfig: data.llm_config, llmConfigured: data.llm_configured,
                    profileReport: data.profile_report || null, workingDataAvailable: data.working_df_available,
                    pg_table_name: data.pg_table_name,
                    nerReport: data.working_df_available && data.ner_report ? data.ner_report : null,
                    aiSummary: data.working_df_available && data.llm_summary ? data.llm_summary : null,
                    dataPreview: null,
                }));
                if (!data.llm_configured) {
                    setActiveAccordionKey('0');
                } else if (!data.working_df_available) {
                    setActiveAccordionKey('1');
                } else {
                    setActiveAccordionKey(null); // Or '0' or keep current logic
                }
            } catch (err) {
                setError("Failed to connect to backend or retrieve session status.");
                setAppState(prevState => ({
                    ...prevState, workingDataAvailable: false, profileReport: null, llmConfigured: false,
                    pg_table_name: null, dataPreview: null,
                }));
            } finally { setIsLoading(false); }
        };
        fetchSessionData();
    }, []);

    useEffect(() => {
        if (appState.pg_table_name && !appState.profileReport && appState.workingDataAvailable) {
            fetchAndSetProfileReport(true);
        }
    }, [appState.pg_table_name, appState.profileReport, appState.workingDataAvailable, fetchAndSetProfileReport]);

    const handleLlmConfigured = useCallback((newConfig) => {
        setAppState(prev => ({...prev, llmConfig: newConfig, llmConfigured: true }));
        setError(null);
        // Optionally close LLM config accordion or open next one
        // setActiveAccordionKey('1'); // Open file upload next
        // Or if using alwaysOpen, user can manage it.
    }, []);

    const handleSetNerReport = useCallback((report) => setAppState(prev => ({ ...prev, nerReport: report })), []);
    const handleSetAiSummary = useCallback((summary) => setAppState(prev => ({ ...prev, aiSummary: summary })), []);

    const handleDownloadExcel = async (filename) => {
        setIsDownloadingExcel(true); setError(null);
        try { await apiService.downloadDataExcel(filename); }
        catch (err) {
            const errorMsg = err.response?.data?.error || err.message || "Failed to download Excel file.";
            setError(errorMsg);
        } finally { setIsDownloadingExcel(false); }
    };

    const toggleInternalSidebarCollapse = () => setIsSidebarCollapsed(!isSidebarCollapsed);

    const llmStatusIcon = appState.llmConfigured ? <FiCheckCircle className="text-success ms-1 align-middle" /> : <FiXCircle className="text-warning ms-1 align-middle" />;
    const llmStatusText = appState.llmConfigured ? ` ${appState.llmConfig?.provider || ''}/${appState.llmConfig?.model_name || ''}` : ' Not Configured';

    return (
        <div className="app-container" data-bs-theme="dark">
            <Navbar bg="dark" variant="dark" expand="lg" sticky="top" className="app-header px-3">
                 <Navbar.Brand href="#home" className="d-flex align-items-center me-auto app-brand">
                     <FiCpu className="me-2 brand-icon" />
                     <span>NextGen DataOps</span>
                 </Navbar.Brand>
                 <Navbar.Text className="d-none d-lg-block small llm-status-navbar" title={appState.llmConfigured ? llmStatusText.trim() : 'Not Configured'}>
                     LLM: {llmStatusIcon}