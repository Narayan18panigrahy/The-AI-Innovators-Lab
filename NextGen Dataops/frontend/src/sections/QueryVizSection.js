            }

        } catch (paramErr) {
             console.error("Parameter Generation Error:", paramErr);
             const paramErrorMsg = paramErr.response?.data?.error || paramErr.message || "Parameter generation failed.";
             setVizError(`Parameter Generation Failed: ${paramErrorMsg}`);
             // setError(paramErrorMsg);
             setIsGeneratingParams(false); // Ensure param loading stops
        } finally {
            setLoading(false); // Stop global loading
        }
    };

    // --- Render Logic ---
    return (
        <div className="query-viz-section">
            {/* Title and LLM Config Warning */}
            <h2 className="h4 mb-3">Query & Visualize Data</h2>
            {!isLlmConfigured && (
                <Alert variant="warning" size="sm">LLM must be configured to use natural language features.</Alert>
            )}

            <Row>
                {/* --- Query Column --- */}
                <Col md={6} className="mb-3 mb-md-0 d-flex flex-column"> {/* Use flex column */}
                    <Card className="flex-grow-1"> {/* Allow card to grow */}
                        <Card.Header>Ask Questions (Chat with your Data)</Card.Header>
                        <Card.Body className="d-flex flex-column"> {/* Flex column for body */}
                            {/* Input Form */}
                            <Form.Group className="mb-2" controlId="nlQueryInput">
                                <Form.Label visuallyHidden>Enter your question</Form.Label>
                                <Form.Control
                                    as="textarea"
                                    rows={3}
                                    placeholder="e.g., What is the total profit per region?"
                                    value={nlQuery}
                                    onChange={(e) => setNlQuery(e.target.value)}
                                    disabled={!isLlmConfigured || isGeneratingSql || isExecutingSql}
                                />
                            </Form.Group>

                            {queryError && <Alert variant="danger" size="sm" className="py-1 px-2 mb-2">{queryError}</Alert>}

                            <Button
                                variant="primary"
                                onClick={handleGenerateAndRunQuery}
                                disabled={!isLlmConfigured || !nlQuery.trim() || isGeneratingSql || isExecutingSql}
                                size="sm"
                                className="mb-3"
                            >
                                {isGeneratingSql ? <><Spinner size="sm"/> Generating SQL...</> :
                                 isExecutingSql ? <><Spinner size="sm"/> Getting Answer...</> :
                                 'Get Answer'}
                            </Button>

                            {/* Generated SQL Display */}
                            {generatedSql && (
                                <details className="mb-3 small text-muted">
                                    <summary style={{cursor: 'pointer'}}>Show Generated SQL</summary>
                                    <Form.Control
                                        as="textarea" rows={3} readOnly value={generatedSql}
                                        className="code-display mt-1" style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
                                     />
                                </details>
                            )}

                            {/* Answer & Raw Data Display Area - allow this to grow */}
                            <div className="query-result-display flex-grow-1" style={{overflowY: 'auto', minHeight: '150px'}}>
                                {(nlAnswer || isExecutingSql) && ( // Show if we have an answer or are waiting for one
                                    <>
                                        <hr/>
                                        <h6 className="mb-2">Answer:</h6>
                                        {isExecutingSql && !isGeneratingSql ? ( // Show spinner only during execution phase
                                            <div className="text-center"><Spinner animation="border" size="sm" variant="secondary"/></div>
                                        ) : nlAnswer ? (
                                            <Card body className="bg-light">
                                                <div className="markdown-content">
                                                    <ReactMarkdown
                                                        children={nlAnswer}
                                                    />
                                                </div>
                                            </Card>
                                        ) : queryError ? null : /* Avoid showing if error already displayed */
                                            ( <Alert variant='secondary' size="sm">Processing request...</Alert> )
                                        }

                                        {/* Display Raw Data Snippet */}
                                        {(rawData && !isExecutingSql) && (
                                            <div className="mt-3">
                                                {llmSkipped && <Alert variant='info' size='sm' className='py-1 px-2 mb-2'>Natural language summary skipped as data result was too large.</Alert>}
                                                <Button variant="outline-secondary" size="sm" onClick={() => setShowRawData(!showRawData)}>
                                                    {showRawData ? 'Hide Raw Data Snippet' : 'Show Raw Data Snippet'}
                                                </Button>
                                                {showRawData && (
                                                    <div className='mt-2 data-snippet-container' style={{maxHeight: '300px', overflowY: 'auto'}}>
                                                        <small className='text-muted d-block mb-1'>{rawDataType}</small>
                                                        {Array.isArray(rawData) ? (
                                                            <SimpleResultTable data={rawData} />
                                                         ) : (
                                                             <pre className="bg-light p-2 rounded small">{JSON.stringify(rawData, null, 2)}</pre>
                                                         )}
                                                         <Button variant="link" size="sm" onClick={handleDownloadQueryResult} className="p-0 mt-1 d-block">
                                                             Download Full Raw Result (CSV)
                                                         </Button>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </>
                                )}
                             </div> {/* End flex-grow-1 result area */}
                        </Card.Body>
                    </Card>
                </Col>

                {/* --- Visualize Column --- */}
                <Col md={6} className="d-flex flex-column"> {/* Use flex column */}
                    <Card className="flex-grow-1"> {/* Allow card to grow */}
                        <Card.Header>Create Visualizations</Card.Header>
                        <Card.Body className="d-flex flex-column"> {/* Flex column for body */}
                            <Form.Group className="mb-2" controlId="vizRequestInput">
                                <Form.Label visuallyHidden>Describe the plot</Form.Label>
                                <Form.Control
                                    as="textarea" rows={3}
                                    placeholder="e.g., Scatter plot of sales vs marketing spend."
                                    value={vizRequest}
                                    onChange={(e) => setVizRequest(e.target.value)}
                                    disabled={!isLlmConfigured || isGeneratingParams || isGeneratingPlot}
                                />
                            </Form.Group>

                            {vizError && <Alert variant="danger" size="sm">{vizError}</Alert>}

                            <Button
                                variant="primary"
                                onClick={handleGeneratePlot}
                                disabled={!isLlmConfigured || !vizRequest.trim() || isGeneratingParams || isGeneratingPlot}
                                size="sm"
                                className="mb-3"
                             >
                                {isGeneratingParams ? <><Spinner size="sm"/> Analyzing Request...</> :
                                 isGeneratingPlot ? <><Spinner size="sm"/> Generating Plot...</> :
                                 'Generate Plot'}
                             </Button>

                             {/* Plot Display Area - allow this to grow */}
                             <div className="plot-display mt-3 flex-grow-1 text-center">
                                 {(isGeneratingParams || isGeneratingPlot) && !plotDataUrl && <Spinner animation="border" variant="primary" />}

                                 {plotDataUrl && !vizError && (
                                     <>
                                         {/* <h6>Generated Plot:</h6> */}
                                         <img src={plotDataUrl} alt="Generated Plot" className="img-fluid border rounded mb-2" style={{maxWidth: '100%', maxHeight: '450px'}}/>
                                         <a href={plotDataUrl} download={plotFilename} className="btn btn-outline-secondary btn-sm">
                                             Download Plot (PNG)
                                         </a>
                                     </>
                                 )}
                             </div>
                             {/* Display plot params for debugging (keep details tag logic) */}
                             {plotParams && ( <details className="mt-2 small text-muted"><summary style={{cursor: 'pointer'}}>Generated Plot Parameters</summary><pre style={{fontSize:'0.7rem'}}>{JSON.stringify(plotParams, null, 2)}</pre></details> )}
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        </div>
    );
}

export default QueryVizSection;