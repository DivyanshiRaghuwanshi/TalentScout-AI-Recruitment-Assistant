import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- Model Initialization ---
try:
    # This reuses the same model initialization logic from the interview graph
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Google API key not found. Please ensure it is set in the .env file.")
    
    model = ChatGoogleGenerativeAI(model="gemini-pro-latest", google_api_key=api_key, convert_system_message_to_human=True)

except Exception as e:
    print(f"Error initializing model for shortlisting agent: {e}")
    model = None

def load_candidate_summaries(summaries_dir="summaries"):
    """
    Scans the summaries directory, loads all candidate JSON files,
    and returns a list of their contents.
    """
    all_summaries = []
    if not os.path.exists(summaries_dir):
        return []

    for filename in os.listdir(summaries_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(summaries_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_summaries.append(data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Could not read or parse file {filename}: {e}")
    
    return all_summaries

def run_shortlisting_agent(job_description: str):
    """
    Orchestrates the shortlisting process by loading candidate data
    and invoking the AI hiring manager agent.
    """
    if not model:
        return "Error: The AI model is not available. Please check the API key."

    candidate_data = load_candidate_summaries()
    if not candidate_data:
        return "No candidate summaries found to analyze."

    # Convert the list of summaries into a single string for the prompt
    candidate_profiles_str = json.dumps(candidate_data, indent=2)

    # Define the prompt for our AI Hiring Manager
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
You are an expert Senior Hiring Manager with 20 years of experience in the tech industry. You have a sharp eye for talent and a deep understanding of technical roles.

Your task is to analyze a list of candidate profiles who have completed an initial AI screening. Based on the provided job description and their screening results, you must produce a final shortlist.

**Your Decision-Making Criteria:**
1.  **Technical Proficiency:** Scrutinize their answers to technical questions and the AI's sentiment analysis. Are their answers deep and practical, or superficial?
2.  **Relevance to Job:** How well does their experience, as described in the AI summary, align with the requirements of the job description?
3.  **Communication & Confidence:** Use the AI's sentiment analysis ('Confident', 'Neutral', 'Hesitant') as a key signal. A confident and correct answer is a strong positive indicator.

**Output Format:**
Your output must be a concise, professional report in Markdown format. Follow this structure exactly:

### Final Shortlisting Report

**Job Role:** {job_description}

---

### **Shortlisted Candidates**

*   **[Candidate Name]:** [Provide a 1-2 sentence justification for why they are a strong fit. Mention a specific strength.]
*   **[Candidate Name]:** [Justification...]

*(If no candidates are shortlisted, state: "No candidates met the bar for this role at this time.")*

---

### **Candidates Not Progressing**

*   **[Candidate Name]:** [Provide a 1-2 sentence, constructive reason for the decision. Mention a specific area of weakness or mismatch.]
*   **[Candidate Name]:** [Justification...]

---
        """),
        ("human", """
Here is the job description we are hiring for:
---
{job_description}
---

And here are the JSON summaries of the candidates who completed the screening:
---
{candidate_profiles}
---

Please generate the final shortlisting report.
        """)
    ])

    # Create and invoke the chain
    chain = prompt | model | StrOutputParser()
    
    try:
        report = chain.invoke({
            "job_description": job_description,
            "candidate_profiles": candidate_profiles_str
        })
        return report
    except Exception as e:
        return f"An error occurred while generating the report: {e}"

if __name__ == '__main__':
    # This allows for testing the agent directly
    print("Running shortlisting agent in test mode...")
    # A sample job description for testing
    sample_jd = "Senior Python Developer with experience in cloud services (AWS/GCP) and building scalable APIs. Strong knowledge of database design and system architecture is required."
    final_report = run_shortlisting_agent(job_description=sample_jd)
    print("\n--- GENERATED REPORT ---")
    print(final_report)
