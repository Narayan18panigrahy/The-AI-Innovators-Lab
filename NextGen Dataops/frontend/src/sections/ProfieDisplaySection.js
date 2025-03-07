
                {/* Cardinality */}
                <Accordion.Item eventKey="2">
                   {/* ... (Cardinality Table rendering exactly as before) ... */}
                   <Accordion.Header>Value Cardinality (Unique Counts)</Accordion.Header>
                   <Accordion.Body>
                        <SimpleTable data={cardinalityArray} columns={[{ header: 'Column', accessor: 'Column' }, { header: 'Unique Values', accessor: 'Unique Values' }]}/>
                   </Accordion.Body>
                </Accordion.Item>

                 {/* Numerical Analysis Details */}
                 <Accordion.Item eventKey="3">
                   {/* ... (Numerical Analysis rendering exactly as before) ... */}
                    <Accordion.Header>Numerical Analysis Details</Accordion.Header>
                    <Accordion.Body>
                        {/* ... (Correlation placeholder) ... */}
                        {/* ... (Skew/Kurt placeholder) ... */}
                        {/* ... (Outlier display) ... */}
                        <h6>Correlation Matrix</h6>
                        {correlationMatrix ? ( /* ... */ <pre>{JSON.stringify(correlationMatrix, null, 2)}</pre> ) : (<p>Not available.</p>)}
                         <hr/>
                         <h6>Skewness & Kurtosis</h6><p className="text-muted small">(Tables coming soon)</p>
                         <hr/>
                         <h6>Outlier Detection (DBSCAN)</h6>
                        {outlierInfo && !outlierInfo.error ? ( <Row xs={1} sm={3}><MetricDisplay label="Potential Outliers" value={outlierInfo.outlier_count} /> <MetricDisplay label="Outlier (%)" value={outlierInfo.outlier_percentage ? `${outlierInfo.outlier_percentage}%` : 'N/A'} /> <MetricDisplay label="Rows Analyzed" value={outlierInfo.rows_analyzed} /></Row> ): ( <p className="text-muted small">{outlierInfo.error || "Outlier info not available."}</p> )}
                         {outlierInfo?.rows_dropped_nan > 0 && <p className="text-muted small mt-1">Note: {outlierInfo.rows_dropped_nan.toLocaleString()} rows with NaN excluded.</p>}
                         {outlierInfo?.parameters && <p className="text-muted small mt-1">Params: eps={outlierInfo.parameters.eps}, min_samples={outlierInfo.parameters.min_samples}</p>}
                    </Accordion.Body>
                </Accordion.Item>
            </Accordion>
        </div>
    );
}

export default ProfileDisplaySection;