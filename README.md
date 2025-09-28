# TalentScout AI 🤖

## Project Overview

TalentScout AI is an advanced, agentic AI recruitment assistant designed to automate the initial screening of job candidates. Built with Streamlit and powered by Google's Gemini models, this tool provides a seamless, interactive experience for candidates and a powerful, centralized dashboard for recruiters.

The application features a two-agent architecture:
- **Candidate Screener Agent:** Interacts with the candidate, gathers essential information via a dynamic form, and conducts a technical interview.
- **Technical Assessor Agent:** A specialized agent that dynamically generates insightful technical questions based on the candidate's declared tech stack and the content of their uploaded resume. It also provides an AI-generated summary of the candidate's performance.

## Key Features
- **Multi-Page Interface:** Separate, dedicated interfaces for candidates and recruiters.
- **Dynamic Question Generation:** Moves beyond static question banks by using the Gemini LLM to create relevant questions on the fly.
- **Resume Analysis:** Ingests PDF resumes, creating a vector-based memory to ask hyper-personalized questions based on the candidate's actual experience.
- **Interactive Interview Flow:** Allows candidates to request an "easier question" and provides AI-generated follow-up questions to probe deeper into their knowledge.
- **Secure Recruiter Dashboard:** A password-protected dashboard for recruiters to view, sort, and analyze all candidate submissions. Features include an AI-generated performance summary for each candidate.
- **Secure Password Management:** Uses `bcrypt` for securely hashing and storing the recruiter password, with a built-in interface for changing it.

## Installation Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd TalentScout-AgenticAIProject
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    # For Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up Environment Variables:**
    - Create a file named `.env` in the root of the project.
    - Add your Google Gemini API key to this file:
      ```
      GOOGLE_API_KEY="your_api_key_here"
      ```

5.  **Run the Application:**
    ```bash
    streamlit run 1_Candidate_Screener.py
    ```
    The application will open in your web browser.

## Usage Guide

### For Candidates
- Navigate to the **Candidate Screener** page.
- Fill in your personal and professional details in the form.
- Optionally, upload your PDF resume for a more personalized interview.
- Answer the technical questions one by one. You can use the "Easier Question" button if needed.

### For Recruiters
- Navigate to the **Recruiter Dashboard** page from the sidebar.
- The first time you access the dashboard, the default password is `password123`.
- Once logged in, you will see a table of all completed candidate screenings.
- You can select a candidate from the dropdown to view their full summary, including their answers and the AI-generated performance analysis.
- To change your password, use the "Change Password" form at the bottom of the dashboard.

## Technical Details

- **Framework:** Streamlit
- **Core Libraries:**
    - `google-generativeai`: For interacting with the Gemini Pro LLM.
    - `langchain`, `langchain-community`, `faiss-cpu`: For text splitting, embeddings, and vector store creation during resume analysis.
    - `pydantic`: For robust data validation of the candidate submission form.
    - `bcrypt`: For secure password hashing.
    - `PyMuPDF`: For extracting text from PDF resumes.
- **LLM Models:**
    - **Generation:** `gemini-pro-latest`
    - **Embeddings:** `models/embedding-001`
- **Architecture:**
    - **Multi-Page App:** The project is structured as a multi-page Streamlit app, with the main screener in the root and additional pages (like the dashboard) in the `pages/` directory.
    - **Modular Logic:** Code is organized into logical modules: `validators.py` for data validation, `resume_processor.py` for handling PDF and vectorization, and `auth.py` for password management.

## Prompt Design

The effectiveness of this agent relies heavily on prompt engineering.
- **Technical Question Generation:** The agent uses a detailed prompt that instructs the AI to act as a senior engineer. It has two modes:
    1.  **Without Resume:** Generates insightful, open-ended questions based on the declared tech stack.
    2.  **With Resume:** A more advanced prompt instructs the AI to synthesize the resume content with the tech stack, asking questions that directly reference the candidate's listed projects and experience.
- **Follow-up & Easier Questions:** Specific prompts were designed to either probe deeper into a given answer or to generate a more fundamental question on the same topic, creating an adaptive interview flow.
- **AI Summary:** At the end of the interview, a final prompt instructs the model to act as a senior hiring manager and produce a concise, professional summary of the candidate's strengths and weaknesses based on the entire technical Q&A.

## Challenges & Solutions

- **Challenge:** Initial `404 Model Not Found` errors with the Gemini API.
  - **Solution:** A utility script (`check_models.py`) was created to query the API directly and identify a valid, available model name (`gemini-pro-latest`), resolving the issue.

- **Challenge:** `ImportError` for `email-validator` after adding Pydantic for validation.
  - **Solution:** Research revealed that email validation requires an extra dependency. This was fixed by changing `pydantic` to `pydantic[email]` in `requirements.txt`.

- **Challenge:** Persistent `ImportError` during a major UI refactor from a sequential chat to a single form.
  - **Solution:** The root cause was a failure to keep `app.py` and `validators.py` in sync. The solution was to adopt a more careful, user-confirmed process to replace the entire file content, ensuring consistency.

- **Challenge:** Storing the recruiter password securely.
  - **Solution:** The initial hardcoded password was replaced with a secure system using the `bcrypt` library. A new `auth.py` module was created to handle hashing, checking, and updating the password, which is stored as a hash in a `.password.hash` file (which is git-ignored).
