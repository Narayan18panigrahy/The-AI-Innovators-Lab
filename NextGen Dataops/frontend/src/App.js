                        ) : (
                         !isLoading &&
                         <Container fluid className="d-flex align-items-center justify-content-center" style={{minHeight: 'calc(100vh - var(--header-height) - 4rem)'}}>
                            <Alert variant="primary" className="text-center welcome-box shadow-lg">
                                <Alert.Heading><FiCpu size="2em" className="mb-2 welcome-icon"/><br/>Welcome to NextGen DataOps!</Alert.Heading>
                                <p>
                                    Unlock the power of your data.
                                    Please configure your LLM settings and upload a dataset using the sidebar to begin.
                                </p>
                                <hr/>
                                <p className="mb-0">
                                    Let's transform data into actionable intelligence.
                                </p>
                            </Alert>
                         </Container>
                        )}
                    </div>
                 </main>
            </div>
        </div>
    );
}

export default App;