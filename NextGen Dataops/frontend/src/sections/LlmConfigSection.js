                            <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                        ))}
                    </Form.Select>
                </Form.Group>

                {/* Dynamically Render Credential Inputs */}
                {provider && SUPPORTED_PROVIDERS_CONFIG[provider] &&
                    Object.entries(SUPPORTED_PROVIDERS_CONFIG[provider]).map(([key, label]) => (
                        <Form.Group className="mb-2" controlId={`credential_${key}`} key={key}>
                            <Form.Label size="sm">{label}</Form.Label>
                            <Form.Control
                                size="sm"
                                type="password"
                                name={key}
                                value={credentials[key] || ''}
                                onChange={handleCredentialChange}
                                required={!(provider === 'nvidia' && key === 'api_base')}
                                autoComplete="new-password"
                            />
                        </Form.Group>
                    ))
                }

                {/* Model Name Input */}
                <Form.Group className="mb-2" controlId="llmModelName">
                    <Form.Label size="sm">Model Name</Form.Label>
                    <Form.Control
                        size="sm"
                        type="text"
                        value={modelName}
                        onChange={handleModelNameChange}
                        required
                        placeholder={provider === 'azure' ? 'Your Deployment Name' : 'e.g., nvidia/model-id'}
                    />
                    {/* Render help text */}
                    <Form.Text className="text-muted">{getModelNameHelp()}</Form.Text>
                </Form.Group>

                {/* Local Error Display */}
                {localError && <Alert variant="danger" size="sm" className="py-1 px-2 mb-2">{localError}</Alert>}

                {/* Save Button */}
                <Button variant="primary" type="submit" size="sm" disabled={isSaving}>
                    {isSaving ? <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" /> : 'Save Config'}
                </Button>
            </Form>
        </div>
    );
}

export default LlmConfigSection;