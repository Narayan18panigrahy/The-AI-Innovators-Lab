# NextGen DataOps Assistant

**NextGen DataOps** is an interactive web application designed to assist with data exploration, profiling, cleaning, analysis, and visualization. It leverages Large Language Models (LLMs) for natural language understanding and employs an agent-based architecture to manage different tasks like automated data profiling, cleaning suggestions, feature engineering, chat with your data, and create Visualization.

## Key Features

*   **Interactive UI:** Built with React for a modern, responsive frontend and Flask for a robust backend API.
*   **File Upload:** Supports loading data from CSV and Excel files.
*   **Automated Data Profiling:** Generates a comprehensive report including:
    *   Overview (rows, columns, duplicates, memory usage)
    *   Data Types
    *   Missing Values (count and percentage)
    *   Descriptive Statistics (numeric and categorical)
    *   Cardinality (unique values)
    *   Correlation Matrix (for numeric columns)
    *   Skewness & Kurtosis (for numeric columns)
    *   Outlier Detection using DBSCAN
*   **Named Entity Recognition (NER):** Analyzes selected text columns to identify and count named entities (like PERSON, ORG, GPE) using spaCy.
*   **Interactive Data Cleaning:** Suggests potential cleaning steps (handling missing values, duplicates) based on the profile report and allows users to apply selected actions.
*   **Interactive Feature Engineering:** Suggests potential new features (datetime extraction, polynomial features, interaction terms) and allows users to create selected features.
*   **AI-Powered Summary:** Generates a textual summary of the dataset's characteristics and quality using an LLM based on the profile report.
*   **Chat with your data:** Translates user questions asked in natural language into executable PostgreSQL `SELECT` queries using an LLM.
*   **Natural Language Visualization:** Interprets natural language requests for plots, determines plot parameters (type, axes, color), and generates visualizations using Seaborn/Matplotlib.
*   **Multi-LLM Provider Support:** Uses the `openai` library configured dynamically to support various LLM providers with OpenAI-compatible APIs (e.g., Azure OpenAI, Nvidia NIM). Users configure their chosen provider and credentials via the UI.
*   **Database Integration:** Loads uploaded data into a PostgreSQL database for efficient querying.
*   **Downloadable Reports & Plots:** Allows downloading the generated profile report as a PDF, query results as CSV, and generated plots as PNG images.
*   **Agent-Based Architecture:** Modular backend design where distinct agents handle specific tasks.

## Folder Structure

```plaintext
nextgen-dataops/
├── backend/                # Flask backend application
│   ├── agents/             # Contains all specialized agent classes
│   │   └── llm/            # Agents specifically interacting with LLMs
│   ├── instance/           # Instance folder for Flask (e.g., session files)
│   ├── venv/               # Python virtual environment (if created here)
│   ├── .env                # Optional: Environment variables for backend
│   ├── app.py              # Main Flask application entry point
│   ├── constants.py        # Application-wide constants
│   └── requirements.txt    # Python package dependencies for backend
│
├── frontend/               # React frontend application
│   ├── public/             # Static assets for frontend
│   ├── src/                # React source code
│   │   ├── assets/         # CSS, images
│   │   ├── components/     # Reusable UI components
│   │   ├── services/       # API interaction logic
│   │   └── ...
│   ├── .env                # Optional: Environment variables for frontend
│   ├── package.json        # Node.js dependencies and scripts
│   └── ...
│
├── .gitignore              # Git ignore configuration
└── README.md               # This file
```

## Setup Instructions

### Prerequisites

*   Python 3.9 or higher
*   `pip` (Python package installer)
*   Node.js and `npm` (or `yarn`) for the frontend
*   PostgreSQL Database Server (running locally or accessible)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url> # Replace with your repo URL
    cd nextgen-dataops
    ```

2.  **Backend Setup:**
    *   Navigate to the `backend` directory:
        ```bash
        cd backend
        ```
    *   Create and activate a virtual environment (Recommended):
        ```bash
        # On macOS/Linux
        python3 -m venv venv
        source venv/bin/activate

        # On Windows
        python -m venv venv
        .\venv\Scripts\activate
        ```
    *   Install Python dependencies:
        ```bash
        pip install -r requirements.txt
        ```
    *   Download spaCy model (Required for Text Analysis / NER):
        ```bash
        python -m spacy download en_core_web_sm
        ```
    *   **Configure Database Connection:** Create a `.env` file in the `backend` directory and add your PostgreSQL connection string:
        ```env
        # Example .env content
        DATABASE_URL=postgresql://user:password@host:port/database_name
        FLASK_SECRET_KEY=your_strong_random_secret_key # Important for sessions
        # Optional: LOG_LEVEL=DEBUG
        ```
        Ensure the specified database exists in your PostgreSQL server.

3.  **Frontend Setup:**
    *   Navigate to the `frontend` directory:
        ```bash
        cd ../frontend # Assuming you are in the backend directory
        # Or: cd path/to/nextgen-dataops/frontend
        ```
    *   Install Node.js dependencies:
        ```bash
        npm install
        # or: yarn install
        ```

## Configuration (LLM API Keys)

The application requires API credentials for the LLM provider you intend to use. These are configured **via the application UI**:

1.  Expand the "Configure LLM Provider" section in the sidebar.
2.  Select your desired LLM provider (e.g., `azure`, `nvidia`).
3.  Enter the required API credentials (API Key, Endpoint/Base URL, API Version for Azure) and the specific Model/Deployment Name you want to use.
4.  Click "Save LLM Configuration".

The configuration is stored securely in the server-side session for the duration of your interaction.

## Running the Application

1.  **Start the Backend (Flask Server):**
    *   Make sure you are in the `backend` directory with the virtual environment activated.
    *   Run the Flask app:
        ```bash
        flask run
        # Or for development mode: flask --app app --debug run
        ```
    *   The backend API will typically start on `http://127.0.0.1:5000`.

2.  **Start the Frontend (React App):**
    *   Open a *new* terminal window.
    *   Navigate to the `frontend` directory.
    *   Run the React development server:
        ```bash
        npm start
        # or: yarn start
        ```
    *   This will usually open the application automatically in your default web browser at `http://localhost:3000`.

## Usage Guide

1.  **Configure LLM:** Expand the "Configure LLM Provider" section in the sidebar, select your provider, enter credentials and model name, and click "Save LLM Configuration".
2.  **Load Data:** Use the file uploader in the sidebar to upload a CSV or Excel file. The data will be loaded into the PostgreSQL database.
3.  **View Profile:** Once loaded, the Data Profiling Report will be automatically generated and displayed. Explore the different sections (Overview, Data Types, Missing Values, etc.). Download the PDF report if needed.
4.  **Optional Analysis & Modification:**
    *   **Text Analysis:** Select text columns and run NER.
    *   **Data Cleaning:** Generate suggestions, select actions, and click "Apply Selected Cleaning Steps". The data in the database will be updated.
    *   **Feature Engineering:** Generate suggestions, select features, and click "Create Selected Features". The data in the database will be updated.
    *   **AI Summary:** Generate an LLM-based summary of the data profile.
5.  **Query Data:**
    *   Go to the "Query and Visualize Data" section.
    *   Enter a question in natural language in the "Ask Questions" box and click "Generate & Run Query".
    *   The generated SQL (if applicable), a natural language answer, and a raw data snippet will appear.
    *   Download full results as CSV if needed.
6.  **Visualize Data:**
    *   Enter a description of the plot you want in the "Create Visualizations" box and click "Generate Plot Parameters".
    *   Review the parameters generated by the LLM.
    *   Click "Generate Plot".
    *   The generated plot will appear below, along with a button to download it as a PNG.

## Contributors

*   Narayan Panigrahy
*   Rohit Ranjan

![Screenshot (2)](https://github.com/user-attachments/assets/0b171e9b-49ab-44ef-a590-39329b025602)

