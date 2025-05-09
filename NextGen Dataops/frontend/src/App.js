                     <span className='d-inline-block text-truncate align-middle' style={{maxWidth: '200px'}}>
                         {llmStatusText}
                     </span>
                 </Navbar.Text>
            </Navbar>

            {isLoading && (
                <div className="loading-overlay">
                    <Spinner animation="border" variant="primary" style={{ width: '4rem', height: '4rem' }} />
                    <p className="mt-3 loading-text">Processing...</p>
                </div>
            )}

            <div className="d-flex app-body">
                 <Offcanvas
                     show={showSidebar}
                     onHide={() => setShowSidebar(false)}
                     responsive="md"
                     className={`app-sidebar-offcanvas bg-transparent border-end ${isSidebarCollapsed && showSidebar ? 'sidebar-shrunk' : ''}`}
                     id="app-sidebar"
                     placement="start"
                 >
                     <Offcanvas.Header closeButton className="border-bottom d-md-none">
                         <Offcanvas.Title className="h6"><FiSettings className="me-2"/>Controls</Offcanvas.Title>
                     </Offcanvas.Header>
                     <Offcanvas.Body className="d-flex flex-column p-0 sidebar-custom-body">
                        {showSidebar && (
                            <Button
                                variant="outline-primary"
                                onClick={toggleInternalSidebarCollapse}
                                className="m-2 align-self-start border sidebar-collapse-toggle flex-shrink-0"
                                title={isSidebarCollapsed ? "Expand Sidebar Sections" : "Collapse Sidebar Sections"}
                                size="sm"
                            >
                                {isSidebarCollapsed ? <FaChevronRight /> : <FaChevronLeft />}
                            </Button>
                        )}

                        <div className={`flex-grow-1 sidebar-content-area ${isSidebarCollapsed ? 'content-collapsed' : ''}`}>
                            {isSidebarCollapsed && showSidebar ? (
                                <div className="d-flex flex-column align-items-center mt-3 pt-2">
                                    <div title="LLM Configuration" className="sidebar-icon-item" onClick={() => { setIsSidebarCollapsed(false); setActiveAccordionKey('0'); }}>
                                        <FiCpu />
                                    </div>
                                    <div title="Load Data" className="sidebar-icon-item" onClick={() => { setIsSidebarCollapsed(false); setActiveAccordionKey('1');}}>
                                        <FiUploadCloud />
                                    </div>
                                    {appState.dataframeName && (
                                        <div title={`File: ${appState.dataframeName}`} className="sidebar-icon-item" onClick={() => setIsSidebarCollapsed(false)}>
                                            <FiDatabase />
                                        </div>
                                    )}
                                </div>
                            ) : (
                                showSidebar && (
                                    <>
                                        <Accordion activeKey={activeAccordionKey} onSelect={(k) => setActiveAccordionKey(k)} flush className="sidebar-accordion">
                                            <Accordion.Item eventKey="0" className="sidebar-accordion-item">
                                                <Accordion.Header className="sidebar-accordion-header">
                                                    <FiCpu className="me-2 accordion-icon"/>LLM Configuration
                                                    {appState.llmConfigured ?
                                                      <FiCheckCircle className="text-success ms-auto accordion-status-icon" title="Configured"/> :
                                                      <FiXCircle className="text-warning ms-auto accordion-status-icon" title="Not Configured"/>
                                                    }
                                                </Accordion.Header>
                                                <Accordion.Body className="sidebar-accordion-body">
                                                    {/* Content has its own padding via .sidebar-section-content */}
                                                    <div className="sidebar-section-content">
                                                        <LlmConfigSection
                                                            initialConfig={appState.llmConfig}
                                                            isConfigured={appState.llmConfigured}
                                                            onConfigSave={handleLlmConfigured}
                                                            setLoading={setIsLoading}
                                                            setError={setError}
                                                        />
                                                    </div>
                                                </Accordion.Body>
                                            </Accordion.Item>

                                            <Accordion.Item eventKey="1" className="sidebar-accordion-item">
                                                <Accordion.Header className="sidebar-accordion-header">
                                                    <FiUploadCloud className="me-2 accordion-icon"/>Load & Manage Data
                                                    {appState.dataframeName && <FiCheckCircle className="text-success ms-auto accordion-status-icon" title="Data Loaded"/>}
                                                </Accordion.Header>
                                                <Accordion.Body className="sidebar-accordion-body">
                                                    <div className="sidebar-section-content">
                                                        <FileUploadSection
                                                            onUploadSuccess={handleDataLoaded}
                                                            setLoading={setIsLoading}
                                                            setError={setError}
                                                        />
                                                    </div>
                                                </Accordion.Body>
                                            </Accordion.Item>
                                        </Accordion>

                                         {appState.dataframeName && (
                                            <Alert variant="info" className="mt-auto small p-2 text-center current-file-alert flex-shrink-0">
                                                Active Dataset: <strong className="text-break">{appState.dataframeName}</strong>
                                            </Alert>
                                         )}
                                    </>
                                )
                            )}
                        </div>
                     </Offcanvas.Body>
                 </Offcanvas>

                 <main className="app-main-content flex-grow-1">
                    <div className="p-3 p-lg-4 main-content-inner">
                        {error && <Alert variant="danger" onClose={() => setError(null)} dismissible className="global-error-alert shadow-lg"><FiAlertTriangle className="me-2"/> {error}</Alert>}

                        {isLoading && !appState.profileReport && appState.workingDataAvailable && (
                             <div className="text-center p-5 placeholder-loading">
                                <Spinner animation="grow" variant="primary" style={{width: '3rem', height: '3rem'}}/>
                                <p className="mt-3 text-muted">Generating Data Profile...</p>
                             </div>
                        )}

                        {appState.workingDataAvailable ? (
                        <>
                            {appState.profileReport ? (
                                <Card className="mb-4 shadow-lg analysis-card">
                                    <Card.Header className="card-header-ai">
                                        <FiDatabase className="me-2 header-icon"/>Data Profile Overview
                                    </Card.Header>
                                    <Card.Body><ProfileDisplaySection report={appState.profileReport} dataframeName={appState.dataframeName} /></Card.Body>
                                </Card>
                            ) : (
                                !isLoading && <div className="text-center p-5 placeholder-loading">
                                    <Spinner animation="grow" variant="primary" style={{width: '3rem', height: '3rem'}}/>
                                    <p className="mt-3 text-muted">Loading Profile Report...</p>
                                </div>
                            )}

                            {appState.dataPreview && (
                                <DataFramePreview
                                    dataPreviewJson={appState.dataPreview}
                                    onDownloadExcel={handleDownloadExcel}
                                    isLoadingDownload={isDownloadingExcel}
                                    dataframeName={appState.dataframeName}
                                />
                            )}

                            {appState.profileReport && (
                                 <Card className="mb-4 shadow-lg analysis-card">
                                     <Card.Header className="card-header-ai">
                                        <FiBarChart2 className="me-2 header-icon"/>Analysis & Transformation Hub
                                     </Card.Header>
                                     <Card.Body>
                                        <OptionalAnalysisTabs
                                            profileReport={appState.profileReport} nerReport={appState.nerReport} aiSummary={appState.aiSummary}
                                            isLlmConfigured={appState.llmConfigured} setNerReport={handleSetNerReport} setAiSummary={handleSetAiSummary}
                                            onDataModified={handleDataModified} setLoading={setIsLoading} setError={setError}
                                        />
                                     </Card.Body>
                                 </Card>
                            )}
                            <Card className="mb-4 shadow-lg analysis-card">
                                 <Card.Header className="card-header-ai">
                                    <FiMessageSquare className="me-2 header-icon"/>Query & Visualize Insights
                                </Card.Header>
                                 <Card.Body>
                                    <QueryVizSection
                                        isLlmConfigured={appState.llmConfigured} dataframeName={appState.dataframeName}
                                        setLoading={setIsLoading} setError={setError}
                                    />
                                 </Card.Body>
                            </Card>
                        </>