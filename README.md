# Consent Secretary Agent 🤖

Welcome to the Consent Secretary Agent, an AI-powered email assistant designed to bring intelligence and efficiency to your inbox. This application securely summarizes your unread emails, determines their intent, and helps you draft smart replies, all while ensuring user consent is at the forefront of every action.

## ✨ Features

-   **AI-Powered Summaries**: Automatically fetches and summarizes your unread emails from the last 24 hours.
-   **Intent Classification**: Categorizes emails into actionable intents like "Scheduling," "Information Request," or "FYI."
-   **Smart Reply Generation**: Uses a powerful language model to generate context-aware, professional email replies.
-   **User-in-the-Loop Workflow**: All generated replies are presented as suggestions, requiring your approval before being sent. You can edit, approve, or reject any suggestion.
-   **Consent-Driven Architecture**: Built on the Hushh Micro-Consent Protocol (HushhMCP), ensuring that every action is performed with explicit, verifiable user consent.
-   **Document-Aware Context**: Can use the content of attached documents to generate more accurate and relevant replies.

## 🛠️ Tech Stack

-   **Backend**: Python, FastAPI, SQLAlchemy, LangChain, Google AI, Groq API
-   **Frontend**: React, React Bootstrap, Axios
-   **Authentication & APIs**: Google OAuth 2.0, Gmail API, Google Calendar API
-   **Consent**: Hushh Micro-Consent Protocol (HushhMCP)

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your local machine:

-   [Git](https://git-scm.com/)
-   [Python 3.10+](https://www.python.org/)
-   [Node.js and npm](https://nodejs.org/en/)

## 🚀 Getting Started

Follow these instructions to get the project up and running on your local machine for development and testing purposes.

### 1. Clone the Repository

First, clone the project repository to your local machine.

```bash
git clone [https://github.com/your-username/your-repository-name.git](https://github.com/your-username/your-repository-name.git)
cd your-repository-name
```

### 2. Backend Setup

The backend is powered by FastAPI and handles all the core logic.

#### **A. Set Up Python Virtual Environment**

It's highly recommended to use a virtual environment to manage dependencies.

```bash
# Navigate to the Backend directory
cd hush_frontend/Backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```

#### **B. Install Dependencies**

Install all the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

#### **C. Configure Environment Variables (Critical Step)**

This project requires several API keys and secret keys to function.

1.  Navigate back to the **root directory** of the project (the one containing `hush_frontend/` and `hushh_mcp/`).
2.  Rename the example environment file from `.env.example` to `.env`.
3.  Open the `.env` file and fill in the values as described below:

```
SECRET_KEY=your_unique_32_character_long_random_key_goes_here
VAULT_ENCRYPTION_KEY=your_unique_64_character_encryption_key_goes_here
GOOGLE_API_KEY="your_google_api_key"
SERPAPI_API_KEY="your_serpapi_api_key"
GROQ_API_KEY="your_groq_api_key"
GOOGLE_CLIENT_ID="your_google_oauth_client_id"
```

-   **`SECRET_KEY` & `VAULT_ENCRYPTION_KEY`**: These are required by HushhMCP. You must generate them yourself. Run the following command in your terminal to generate a secure, random key and paste it into the file.
    ```bash
    # Run this command twice to generate two different keys
    python -c "import secrets; print(secrets.token_hex(32))"
    ```
-   **`GOOGLE_API_KEY`**: Obtain this from the Google Cloud Console for your project.
-   **`SERPAPI_API_KEY`**: Get this from your [SerpAPI Dashboard](https://serpapi.com/dashboard).
-   **`GROQ_API_KEY`**: Get this from your [Groq Console](https://console.groq.com/keys).
-   **`GOOGLE_CLIENT_ID`**: You will get this in the next step. Copy the `client_id` from your `credentials.json` file here.

#### **D. Configure Google OAuth Credentials (Critical Step)**

To access Gmail and Google Calendar, you need to generate two separate OAuth credential files.

1.  **Go to the [Google Cloud Console](https://console.cloud.google.com/).**
2.  Create a new project or select an existing one.
3.  In the navigation menu, go to **APIs & Services > Library**.

**For Gmail API (`credentials.json`):**
- Search for and enable the **Gmail API**.
- Go to **APIs & Services > Credentials**.
- Click **+ CREATE CREDENTIALS** > **OAuth client ID**.
- Select **Web application** as the application type.
- Under **Authorized redirect URIs**, add `http://localhost:8080`.
- Click **Create**. Download the JSON file and rename it to `credentials.json`.
- Place this `credentials.json` file inside the `hush_frontend/Backend/` directory.

**For Google Calendar API (`calendar_credentials.json`):**
- Search for and enable the **Google Calendar API**.
- Follow the exact same steps as above to create another **OAuth client ID**.
- Download the new JSON file and rename it to `calendar_credentials.json`.
- Place this `calendar_credentials.json` file inside the `hush_frontend/Backend/` directory.

> **Note**: You are correct that `token.json` will be generated automatically the first time a user signs in and grants consent. You do not need to create this file yourself.

#### **E. Run the Backend Server**

Navigate back to the `Backend` directory and start the FastAPI server.

```bash
# Make sure you are in the hush_frontend/Backend/ directory
uvicorn app:app --reload --port 8000
```

The backend API will now be running on `http://localhost:8000`.

### 3. Frontend Setup

The frontend is a React application.

#### **A. Install Dependencies**

Open a **new terminal window** and navigate to the frontend directory.

```bash
# From the project root directory
cd hush_frontend
npm install
```

#### **B. Start the Frontend Server**

```bash
npm start
```

The React application will open automatically in your browser at `http://localhost:3000`.

## ✅ Usage

1.  Open your browser to `http://localhost:3000`.
2.  You will be prompted to sign up or sign in with your Google account or email/password.
3.  The first time you sign in, a Google consent screen will appear, asking you to grant the permissions your application needs (to read emails and manage calendar events).
4.  Once authorized, you can navigate through the application to summarize your inbox and generate smart replies.
