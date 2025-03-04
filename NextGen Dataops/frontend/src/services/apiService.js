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