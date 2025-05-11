// frontend/src/sections/FileUploadSection.js

import React, { useState, useRef } from 'react';
import Form from 'react-bootstrap/Form';
import Button from 'react-bootstrap/Button';
import ProgressBar from 'react-bootstrap/ProgressBar';
import Alert from 'react-bootstrap/Alert';

// Import API service
import apiService from '../services/apiService';

// Component Props:
// - onUploadSuccess (function): Callback function in App.js when upload & initial processing is done. Passes backend response data.
// - setLoading (function): Callback to set global loading state in App.js (for overlay)
// - setError (function): Callback to set global error state in App.js

// Define allowed file types based roughly on backend constants
const ALLOWED_MIME_TYPES = [
    "text/csv",
    "application/vnd.ms-excel", // .xls
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" // .xlsx
];
const ALLOWED_EXTENSIONS_STRING = ".csv, .xlsx, .xls";

function FileUploadSection({ onUploadSuccess, setLoading, setError }) {
    // --- Component State ---
    const [selectedFile, setSelectedFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [localError, setLocalError] = useState(''); // Error specific to upload validation/process
    const fileInputRef = useRef(null); // Ref to reset the file input

    // --- Event Handlers ---
    const handleFileChange = (event) => {
        setLocalError(''); // Clear previous errors
        setError(null); // Clear global errors
        const file = event.target.files ? event.target.files[0] : null;

        if (file) {
            // Basic validation (can add size check here too if needed)
            if (!ALLOWED_MIME_TYPES.includes(file.type) && !ALLOWED_EXTENSIONS_STRING.includes(file.name.slice(file.name.lastIndexOf('.')))) {
                 setLocalError(`Invalid file type. Please upload ${ALLOWED_EXTENSIONS_STRING}`);
                 setSelectedFile(null);
                 // Reset the file input visually
                 if(fileInputRef.current) {
                     fileInputRef.current.value = "";
                 }
                 return;
            }
            setSelectedFile(file);
            console.log("File selected:", file.name, file.size, file.type);
        } else {
            setSelectedFile(null);
        }
    };

    const handleUpload = async () => {
        if (!selectedFile) {
            setLocalError("Please select a file first.");
            return;
        }

        setIsUploading(true);
        setUploadProgress(0);
        setLocalError('');
        setError(null); // Clear global error
        setLoading(true); // Set global loading overlay active

        try {
            const response = await apiService.uploadFile(selectedFile, (progressEvent) => {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                setUploadProgress(percentCompleted);
            });

            console.log("Upload successful:", response.data);
            onUploadSuccess(response.data); // Notify parent component with backend response (incl. profile)

        } catch (err) {
            console.error("Upload Error:", err);
            const errorMsg = err.response?.data?.error || err.message || "File upload failed.";
            setError(`Upload failed: ${errorMsg}`); // Set global error
            setLocalError("Upload failed. Please try again."); // Set local error
        } finally {
            setIsUploading(false);
            setLoading(false); // Stop global loading overlay
            setSelectedFile(null); // Clear selection after attempt
             // Reset the file input visually
            if(fileInputRef.current) {
                fileInputRef.current.value = "";
            }
        }
    };

    // --- Render Logic ---
    return (
        <div className="file-upload-section">
            <h3 className="h5">Load Data</h3>
            <Form>
                <Form.Group controlId="formFile" className="mb-3">
                    <Form.Label size="sm">Select CSV or Excel File</Form.Label>
                    <Form.Control
                        type="file"
                        size="sm"
                        ref={fileInputRef} // Assign ref
                        onChange={handleFileChange}
                        accept={ALLOWED_EXTENSIONS_STRING} // Hint for browser file picker
                        disabled={isUploading}
                    />
                </Form.Group>

                {/* Display selected file name */}
                {selectedFile && !isUploading && (
                    <p className="text-muted small mb-2">Selected: {selectedFile.name}</p>
                )}

                {/* Local Error Display */}
                {localError && <Alert variant="danger" size="sm" className="py-1 px-2 mb-2">{localError}</Alert>}

                {/* Upload Progress Bar */}
                {isUploading && (
                    <ProgressBar
                        animated
                        now={uploadProgress}
                        label={`${uploadProgress}%`}
                        className="mb-2"
                        style={{ height: '15px' }} // Custom height
                        variant="info"
                    />
                )}

                {/* Upload Button */}
                <Button
                    variant="success"
                    size="sm"
                    onClick={handleUpload}
                    disabled={!selectedFile || isUploading} // Disable if no file or uploading
                >
                    {isUploading ? 'Uploading...' : 'Upload & Profile'}
                </Button>
            </Form>
        </div>
    );
}

export default FileUploadSection;