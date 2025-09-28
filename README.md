# TalentScout AI Recruitment Assistant

## 1. Project Overview

TalentScout is an advanced, conversational AI agent designed to automate and enhance the initial technical screening of job candidates. Built with Python and Streamlit, it provides a seamless, interactive experience for candidates while delivering insightful, summarized data to recruiters.

The application functions as a multi-page Streamlit app:
- **Candidate Screener:** A candidate-facing interface that gathers information, conducts an AI-driven technical interview, and analyzes responses.
- **Recruiter Dashboard:** A secure, password-protected dashboard for recruiters to review candidate submissions, performance summaries, and sentiment analysis.

## 2. Installation Instructions

To set up and run this project locally, please follow these steps:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/DivyanshiRaghuwanshi/TalentScout-AI-Recruitment-Assistant.git
    cd TalentScout-AI-Recruitment-Assistant
    ```

2.  **Create and Activate a Virtual Environment:**
    Using a virtual environment is crucial to prevent dependency conflicts.
    ```bash
    # Create the environment
    python -m venv .venv

    # Activate on Windows (PowerShell)
    .\\.venv\\Scripts\\Activate.ps1
    ```

3.  **Install Dependencies:**
    With your virtual environment active, install all required packages from the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up Environment Variables:**
    Create a file named `.env` in the project's root directory. Add your Google API key to this file:
    ```
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"
    ```

5.  **Run the Application:**
    Launch the Streamlit app from your terminal.
    ```bash
    streamlit run 1_Candidate_Screener.py
    ```
    The application will open in your default web browser.

## 3. Usage Guide

- **For Candidates:** Access the main URL to begin the screening. Fill out the initial form and upload an optional resume. Answer the technical questions presented by the AI assistant, "Scout."
- **For Recruiters:** Navigate to the "Recruiter Dashboard" page from the sidebar. Log in using the password. View all candidate submissions in the main table. Select a candidate from the dropdown to view their detailed summary, including the AI's performance analysis and a breakdown of their answers and sentiment.

## 4. Technical Details

#### Libraries and Tech Stack
- **Backend:** Python
- **Frontend:** Streamlit
- **LLM:** Google Gemini (`gemini-pro-latest` for generation, `models/embedding-001` for embeddings)
- **Resume & Vectorization:** LangChain, FAISS (for in-memory vector search), PyMuPDF (for PDF text extraction)
- **Data Validation:** Pydantic (for form validation)
- **Authentication:** `bcrypt` for secure password hashing and verification.
- **Environment Management:** `python-dotenv` for secrets management.

#### Architectural Decisions
- **Multi-Page App:** The application is structured as a multi-page Streamlit app to enforce a clear separation of concerns between the candidate-facing and recruiter-facing functionalities.
- **Agent-Based Logic:** The core AI logic is encapsulated within a `TechnicalAssessorAgent` class. This makes the code modular and easy to maintain, as all AI-related tasks (question generation, analysis, summarization) are handled by this agent.
- **State Management:** Streamlit's `session_state` is used extensively to manage the conversation flow, store user data, and track the interview stage.
- **Security:** The recruiter dashboard is protected by a password system. Passwords are not stored in plain text; instead, `bcrypt` is used to store a secure hash in a git-ignored file (`.password.hash`), ensuring credentials are not exposed.

## 5. Prompt Design

The effectiveness of the AI hinges on carefully crafted prompts.

- **Persona-Driven Prompts:** The AI is given the persona of "Scout," a sharp, experienced senior engineer. This ensures the tone of the conversation is professional and appropriate for a technical screening.
- **Context-Aware Question Generation:**
    - **With Resume:** If a resume is provided, the prompt instructs the AI to synthesize the candidate's declared tech stack with specific projects mentioned in the resume. This leads to deeply personalized and insightful questions.
    - **Without Resume:** If no resume is available, a fallback prompt is used to generate strong, open-ended questions based solely on the declared tech stack.
- **Specialized Task Prompts:** Separate, highly-focused prompts are used for specialized tasks like generating an "easier question," a "follow-up question," or analyzing the sentiment of an answer. This ensures the AI produces a predictable and accurate output for each specific task.

## 6. Challenges & Solutions

- **Challenge:** Initial `ModuleNotFoundError` for `google.generativeai` and dependency conflicts with globally installed packages like `tensorflow-intel`.
- **Solution:** The issue was resolved by creating a dedicated virtual environment (`.venv`) for the project. This isolated the project's dependencies from the global Python installation, ensuring a clean and stable environment. The `requirements.txt` file was also updated.

- **Challenge:** Ensuring the Recruiter Dashboard was secure and not publicly accessible.
- **Solution:** A robust authentication system was built using the `bcrypt` library. A dedicated `auth.py` module handles password hashing, setting, and checking, ensuring that recruiter-sensitive data is protected.

## 7. Bonus Enhancements

- **Modern UI/UX:** A custom `style.css` file provides a more attractive and professional user interface with custom fonts, gradients, and interactive hover effects.
- **Sentiment Analysis:** The AI analyzes the text of a candidate's answers to gauge their confidence level, providing recruiters with deeper insight.
