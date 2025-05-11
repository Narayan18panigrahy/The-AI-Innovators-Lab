// frontend/src/index.js (or main.jsx)

import React from 'react';
import ReactDOM from 'react-dom/client'; // Use client rendering API

// --- Global Styles ---
// Import Bootstrap CSS first if using its components/classes globally
// Make sure you installed it: npm install bootstrap
import 'bootstrap/dist/css/bootstrap.min.css';
// Import your custom global styles (can override Bootstrap)
import './assets/styles.css'; // Create this file for your custom styles

// --- Main App Component ---
import App from './App';

// --- Optional: Web Vitals for performance measurement ---
// import reportWebVitals from './reportWebVitals';

// Find the root DOM element defined in public/index.html
const rootElement = document.getElementById('root');

// Ensure the root element exists before trying to render
if (rootElement) {
  // Create a React root for concurrent rendering
  const root = ReactDOM.createRoot(rootElement);

  // Render the main App component wrapped in StrictMode
  root.render(
    <React.StrictMode> {/* Helps identify potential problems */}
      <App />
    </React.StrictMode>
  );
} else {
  console.error("Failed to find the root element with ID 'root'. React app could not be mounted.");
}


// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
// reportWebVitals(); // Uncomment if needed