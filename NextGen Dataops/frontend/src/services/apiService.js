// frontend/src/services/apiService.js

import axios from 'axios';

// --- Configuration ---

// Read the API base URL from environment variables with a fallback
const API_BASE_URL = process.env.REACT_APP_API_URL || // For Create React App
                     (typeof import.meta.env !== 'undefined' ? import.meta.env.VITE_API_URL : null) || // For Vite
                     'http://localhost:5000/api'; // Default fallback

console.log("Using API Base URL:", API_BASE_URL); // Log for debugging

// Create an Axios instance with default settings
const apiClient = axios.create({
  baseURL: API_BASE_URL, // All requests will be relative to this
  timeout: 600000,        // Increased timeout (60 seconds) for potentially long operations
  withCredentials: true, // Send session cookies
  headers: {
    'Content-Type': 'application/json', // Default content type for POST/PUT
  },
});

// --- Optional: Interceptors for logging ---
apiClient.interceptors.request.use(request => {
   console.log('Starting API Request:', request.method?.toUpperCase(), request.url, request.data || request.params);
   return request;
});

apiClient.interceptors.response.use(response => {
   console.log('API Response:', response.status, response.data);
   return response;
}, error => {
   // Log detailed error information
   console.error(
       'API Error:',
       error.response?.status, // Status code
       error.response?.data || error.message, // Backend error message or network error
       error.config?.url // URL that failed
    );
   // Don't swallow the error, let calling code handle it
   return Promise.reject(error);
});


// --- API Service Functions ---

const apiService = {
  /**
   * Checks the current session status with the backend.
   */
  checkSession: () => {
    return apiClient.get('/session');
  },

  /**
   * Saves the LLM configuration.
   * @param {object} configData - { provider, model_name, credentials }
   */
  saveLlmConfig: (configData) => {
    return apiClient.post('/config_llm', configData);
  },

  /**
   * Uploads a data file.
   * @param {File} file - The file object to upload.
   * @param {function} [onUploadProgress] - Optional callback for upload progress.
   */
  uploadFile: (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file); // Key matches Flask's request.files['file']

    return apiClient.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data', // Override default JSON for file uploads
      },
      onUploadProgress: onUploadProgress,
    });
  },

  /**
   * Generates an SQL query from a natural language question.
   * @param {string} query - The natural language query.
   */
  generateSqlQuery: (query) => {
    return apiClient.post('/generate_query', { query }); // Updated endpoint
  },

  /**
   * Executes an SQL query and gets a natural language answer.
   * @param {string} sql_query - The SQL query string to execute.
   */
  executeQueryAndGetAnswer: (sql_query) => {
    return apiClient.post('/execute_query', { sql_query }); // Updated endpoint
  },

  /**
   * Gets cleaning suggestions based on the current data/profile.
   */
  suggestCleaning: () => {
    return apiClient.get('/suggest_cleaning');
  },

  /**
   * Applies selected cleaning actions.
   * @param {Array<object>} actions - List of cleaning action objects.
   */
  applyCleaning: (actions) => {
    return apiClient.post('/apply_cleaning', { actions }); // Ensure this returns the full response
  },

  /**
   * Gets feature engineering suggestions based on the current data.
   */
  suggestFeatures: () => {
    return apiClient.get('/suggest_features');
  },

  /**
   * Applies selected feature engineering actions.
   * @param {Array<object>} features - List of feature creation objects.
   */
  applyFeatures: (features) => {
    return apiClient.post('/apply_features', { features }); // Ensure this returns the full response
  },

  /**
   * Analyzes text columns for Named Entities.
   * @param {Array<string>} columns - List of column names to analyze.
   */
  analyzeNer: (columns) => {
    return apiClient.post('/ner_analyze', { columns });
  },

  /**
   * Generates an AI summary based on the current data profile.
   */
  generateSummary: () => {
    return apiClient.post('/generate_summary', {}); // Empty body might be okay if context is from session
  },

  /**
   * Generates visualization parameters from natural language.
   * @param {string} request - The natural language visualization request.
   */
  generateVizParams: (request) => {
    return apiClient.post('/generate_viz_params', { request });
  },

  /**
   * Generates the actual plot image data URL based on parameters.
   * @param {object} params - Plot parameters dictionary.
   */
  generatePlot: (params) => {
    return apiClient.post('/generate_plot', { params }); // Expects data URL back
  },

  /**
   * Returns the URL endpoint to trigger profile PDF download.
   * Frontend needs to handle navigating to this URL.
   */
  getProfilePdfUrl: () => {
    return `${API_BASE_URL}/download/profile_pdf`;
  },

  /**
   * Returns the URL endpoint to trigger query result CSV download.
   * Backend handles re-running the last successful query.
   * Frontend needs to handle navigating to this URL.
   */
  getQueryResultCsvUrl: () => {
    return `${API_BASE_URL}/download/query_result_csv`;
  },

  /**
   * Refreshes the profile report.
   */
  refreshProfileReport: () => {
    return apiClient.post('/profile/refresh');
  },

  /**
   * Downloads data as an Excel file.
   * @param {string} [filename='data_modified.xlsx'] - The name of the file to save.
   */
  downloadDataExcel: async (filename = 'data_modified.xlsx') => {
    try {
      const response = await apiClient.get('/download_data/excel', {
        responseType: 'blob', // Crucial for file downloads
      });
      // Create a link element, click it to trigger download, then remove it
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading Excel file:', error);
      throw error; // Re-throw to be handled by the calling component
    }
  },

  // If you implement plot downloads differently (e.g., saving plot image on backend
  // and needing to fetch it by a key):
  // getPlotImageUrl: (plotKey) => {
  //   return `${API_BASE_URL}/download/plot/${plotKey}`; // Example
  // },

};

export default apiService;