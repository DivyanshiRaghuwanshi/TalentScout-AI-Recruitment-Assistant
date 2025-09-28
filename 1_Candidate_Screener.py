import streamlit as st
import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from validators import validate_form, CandidateDetails
from resume_processor import process_resume

# Load environment variables
load_dotenv()

# --- Agent Definitions ---

class TechnicalAssessorAgent:
    """
    A specialized agent that generates technical questions using a Large Language Model.
    """
    def __init__(self, model):
        self.model = model

    def generate_questions(self, tech_stack, resume_retriever=None):
        """
        Generates a set of technical questions for the given tech stack using an LLM,
        optionally using resume context.
        """
        prompt = ""
        # --- Prompt Engineering: Select prompt based on resume availability ---
        if resume_retriever:
            context = ""
            for tech in tech_stack:
                try:
                    # Get relevant context from the resume for each technology
                    docs = resume_retriever.get_relevant_documents(tech)
                    if docs:
                        context += f"Context from resume related to {tech}:\n"
                        for doc in docs:
                            context += f"- {doc.page_content}\n"
                except Exception as e:
                    st.warning(f"Could not get resume context for {tech}: {e}")
            
            if context:
                # If we found relevant context, use the advanced prompt
                prompt = f"""
                You are "Scout", an AI hiring assistant for a top-tier tech company. Your persona is that of a sharp, experienced senior engineer.
                A candidate's self-declared tech stack is: {', '.join(tech_stack)}.
                You have been provided with the following context extracted from their resume:
                ---
                {context}
                ---
                Your goal is to generate 3-5 deeply insightful technical questions that synthesize the candidate's declared tech stack with the specific projects and experiences mentioned in their resume.
                Follow these rules:
                1.  **Prioritize Resume Context:** Base your questions on the resume context provided. Refer to specific details if possible (e.g., "In your resume, you mentioned a project using Django...").
                2.  **Probe Deeper:** Ask "how," "why," or "describe" questions that probe for understanding of core principles, trade-offs, and practical application.
                3.  **Scenario-Based:** Include at least one scenario-based question relevant to their experience.
                4.  **No Generic Questions:** Avoid simple definitions or questions that could be answered without the resume context.
                Format the output *only* as a numbered list. Do not include any other text, introduction, or conclusion.
                """
        
        # Fallback to the original prompt if no resume context was found or no resume was provided
        if not prompt:
            prompt = f"""
            You are "Scout", an AI hiring assistant for a top-tier tech company. Your persona is that of a sharp, experienced senior engineer.
            A candidate is applying for a software engineering role and has listed their tech stack as: {', '.join(tech_stack)}.
            Your goal is to generate 3-5 deeply insightful technical questions to accurately gauge their skills. Follow these rules:
            1.  For each technology listed, generate at least one relevant question.
            2.  Focus on open-ended questions that start with "How," "Why," or "Describe." Avoid simple definitions.
            3.  Include at least one scenario-based question (e.g., "Imagine you have a slow database query... How would you debug it?").
            4.  The questions should probe for understanding of core principles, trade-offs, and practical application, not just textbook knowledge.
            Format the output *only* as a numbered list. Do not include any other text, introduction, or conclusion.
            """

        try:
            response = self.model.generate_content(prompt)
            text_response = response.text
            questions = re.findall(r'\d+\.\s*(.*)', text_response)
            if not questions:
                return self.fallback_questions()
            return [q.strip() for q in questions]
        except Exception as e:
            st.error(f"An error occurred while generating questions: {e}")
            return self.fallback_questions()

    def generate_easier_question(self, original_question, tech_stack):
        """Generates an easier version of a given technical question."""
        try:
            prompt = f"""
            You are "Scout", an AI hiring assistant.
            A candidate found the following question too difficult: "{original_question}"

            The candidate's tech stack is: {', '.join(tech_stack)}.

            Your task is to generate a single, more fundamental, and easier question on the *same topic* as the original question.
            For example, if the original question was about advanced database indexing strategies, a good easier question would be about the basic purpose of database indexes.

            Format the output as just the question text. Do not include any other text, introduction, or numbering.
            """
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            st.error(f"An error occurred while generating an easier question: {e}")
            return "Could you please describe a core concept related to your tech stack?"

    def generate_follow_up_question(self, original_question, user_answer):
        """Generates a follow-up question based on the user's answer."""
        try:
            prompt = f"""
            You are "Scout", an AI hiring assistant. Your persona is that of a sharp, experienced senior engineer.

            The original question was: "{original_question}"
            The candidate's answer was: "{user_answer}"

            Your task is to generate a single, insightful follow-up question that probes deeper into their answer.
            - If the answer is good, ask something that builds on it.
            - If the answer is weak or vague, ask for clarification or a more specific example.
            - Keep the question concise.

            Format the output as just the question text. Do not include any other text, introduction, or numbering.
            """
            response = self.model.generate_content(prompt)
            # Add a prefix to distinguish it as a follow-up
            return f"Follow-up: {response.text.strip()}"
        except Exception as e:
            st.error(f"An error occurred while generating a follow-up question: {e}")
            return None # Return None if it fails

    def summarize_performance(self, technical_answers):
        """Analyzes the technical answers and generates a summary."""
        if not technical_answers:
            return "No technical answers were provided."

        try:
            # Format the Q&A for the prompt
            qa_text = ""
            for q, a in technical_answers.items():
                qa_text += f"Question: {q}\nAnswer: {a}\n\n"

            prompt = f"""
            You are a senior engineering manager reviewing a candidate's technical screening.
            Based on the following questions and answers, provide a concise, professional summary of the candidate's performance.

            Your summary should include:
            1.  **Overall Impression:** A brief, one-sentence summary.
            2.  **Strengths:** 1-2 bullet points highlighting areas where the candidate demonstrated strong knowledge.
            3.  **Areas for Improvement:** 1-2 bullet points identifying topics where the candidate seemed weak or could be probed further.

            Keep the tone objective and constructive.

            ---
            CANDIDATE'S Q&A:
            {qa_text}
            ---

            SUMMARY:
            """
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            st.error(f"An error occurred while generating the summary: {e}")
            return "Could not generate AI summary due to an error."

    def fallback_questions(self):
        return [
            "Could you describe a challenging project you've worked on with your listed technologies?",
            "How do you stay updated with the latest trends in your tech stack?"
        ]

# --- Streamlit UI & State Management ---

def initialize_app():
    """Sets up the Streamlit page and initializes the AI model."""
    st.set_page_config(page_title="TalentScout AI", page_icon="🤖")
    st.title("Welcome to TalentScout AI 🤖")
    st.markdown("""
Hello! I'm **Scout**, your AI assistant for the first stage of our interview process. My goal is to get to know you a bit better.

**Here’s how our session will work:**
1.  **Your Details:** First, you'll fill out the form below with your information. You can also upload your resume to help me ask more relevant questions.
2.  **Technical Questions:** Based on your tech stack (and resume, if provided), I will ask you a few technical questions one by one.
3.  **Follow-ups:** After you answer a main question, I may ask a brief follow-up question to dive a little deeper.

**A quick note on the questions:**
*   You will have an **"Easier Question"** button available for each main technical question.
*   Feel free to use it if a question is too tough. Please be aware that your use of this option will be noted in the final summary for our hiring team.

Let's get started!
""")

    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            st.error("Google API key not found. Please create a .env file with GOOGLE_API_KEY='YOUR_API_KEY'.")
            st.stop()
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro-latest')
        return model
    except Exception as e:
        st.error(f"Failed to configure the AI model: {e}")
        st.stop()

def initialize_session_state(model):
    """Initializes Streamlit's session state variables."""
    if 'conversation_stage' not in st.session_state:
        st.session_state.conversation_stage = "gathering_info"
    if 'candidate_details' not in st.session_state:
        st.session_state.candidate_details = {}
    if 'technical_questions' not in st.session_state:
        st.session_state.technical_questions = []
    if 'technical_answers' not in st.session_state:
        st.session_state.technical_answers = {}
    if 'tech_question_index' not in st.session_state:
        st.session_state.tech_question_index = 0
    if 'is_awaiting_follow_up_answer' not in st.session_state:
        st.session_state.is_awaiting_follow_up_answer = False
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'resume_retriever' not in st.session_state:
        st.session_state.resume_retriever = None
    if 'assessor' not in st.session_state:
        st.session_state.assessor = TechnicalAssessorAgent(model)

def display_chat_history():
    """Displays the chat messages stored in session state."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def generate_summary_data():
    """Creates a dictionary of the candidate's data, answers, and AI analysis."""
    with st.spinner("Generating AI performance summary..."):
        ai_summary = st.session_state.assessor.summarize_performance(
            st.session_state.technical_answers
        )

    summary_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "candidate_details": st.session_state.candidate_details,
        "ai_summary": ai_summary,
        "technical_responses": st.session_state.technical_answers
    }
    return summary_data

def save_and_download_summary(summary_data):
    """Saves the summary to a file and provides a download button."""
    # Ensure the summaries directory exists
    summaries_dir = "summaries"
    if not os.path.exists(summaries_dir):
        os.makedirs(summaries_dir)

    # Create a unique filename
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate_name = summary_data.get("candidate_details", {}).get("full_name", "candidate").replace(" ", "_")
    file_name = f"{timestamp_str}_{candidate_name}.json"
    file_path = os.path.join(summaries_dir, file_name)

    # Convert dict to JSON string for saving and downloading
    json_string = json.dumps(summary_data, indent=4)

    # Save the file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_string)
    except IOError as e:
        st.error(f"Failed to save summary file: {e}")

    # Provide download button
    st.download_button(
        label="Download Screening Summary (JSON)",
        data=json_string,
        file_name=f"talent_scout_summary_{candidate_name}.json",
        mime="application/json",
    )

def main():
    model = initialize_app()
    initialize_session_state(model)

    # --- Stage 1: Information Gathering Form ---
    if st.session_state.conversation_stage == "gathering_info":
        with st.form("candidate_form"):
            st.write("Please provide your details:")
            
            uploaded_resume = st.file_uploader("Upload your Resume (Optional, PDF only)", type="pdf")

            details = {
                "full_name": st.text_input("Full Name"),
                "email": st.text_input("Email Address"),
                "phone_number": st.text_input("Phone Number (e.g., +1234567890)"),
                "experience": st.number_input("Years of Professional Experience", min_value=0, step=1),
                "desired_position": st.text_input("Desired Position"),
                "current_location": st.text_input("Current Location"),
                "tech_stack": st.text_input("Primary Tech Stack (comma-separated, e.g., Python, Django, React)"),
            }
            submitted = st.form_submit_button("Submit Details")

            if submitted:
                is_valid, errors = validate_form(details)
                if is_valid:
                    st.session_state.candidate_details = details
                    
                    # Process the resume if it was uploaded
                    if uploaded_resume:
                        with st.spinner("Analyzing resume..."):
                            st.session_state.resume_retriever = process_resume(uploaded_resume)
                            if not st.session_state.resume_retriever:
                                st.error("Could not process the uploaded resume. Please ensure it's a valid PDF. Continuing without resume analysis.")

                    st.session_state.conversation_stage = "generating_tech_questions"
                    st.success("Details submitted successfully! Generating technical questions...")
                    st.rerun()
                else:
                    for error in errors:
                        st.error(error)

    # --- Stage 2: Generating and Asking Technical Questions ---
    elif st.session_state.conversation_stage == "generating_tech_questions":
        with st.spinner("Analyzing tech stack and generating questions..."):
            tech_stack_list = [tech.strip() for tech in st.session_state.candidate_details.get("tech_stack", "").split(',')]
            
            # Pass the resume retriever to the agent
            questions = st.session_state.assessor.generate_questions(
                tech_stack_list, 
                st.session_state.resume_retriever
            )
            
            st.session_state.technical_questions = questions
            st.session_state.conversation_stage = "in_tech_questions"
            
            # Add initial messages to chat
            st.session_state.messages.append({"role": "assistant", "content": "Thank you for providing your details. Now, based on your tech stack, I have a few technical questions for you."})
            st.session_state.messages.append({"role": "assistant", "content": questions[0]})
            st.rerun()

    # --- Stage 3 & 4: In-progress and Concluding ---
    else:
        display_chat_history()

        if st.session_state.conversation_stage == "concluding":
            st.info("You have completed the initial screening. Thank you for your time!")
            
            summary_data = generate_summary_data()
            save_and_download_summary(summary_data)

        else: # In technical questions
            # Create columns for the input and the button
            col1, col2 = st.columns([4, 1])

            with col2:
                if st.button("Easier Question"):
                    with st.spinner("Generating an easier question..."):
                        current_question = st.session_state.technical_questions[st.session_state.tech_question_index]
                        tech_stack_list = [tech.strip() for tech in st.session_state.candidate_details.get("tech_stack", "").split(',')]
                        
                        new_question = st.session_state.assessor.generate_easier_question(current_question, tech_stack_list)
                        
                        # Replace the old question with the new one
                        st.session_state.technical_questions[st.session_state.tech_question_index] = new_question
                        st.session_state.messages[-1] = {"role": "assistant", "content": new_question} # Update the last message
                        st.rerun()

            with col1:
                if prompt := st.chat_input("Your answer..."):
                    st.session_state.messages.append({"role": "user", "content": prompt})

                    # --- New Conversational Logic ---
                    
                    # Case 1: User is answering a follow-up question
                    if st.session_state.is_awaiting_follow_up_answer:
                        # Append the follow-up answer to the previous main answer
                        last_question = st.session_state.technical_questions[st.session_state.tech_question_index]
                        st.session_state.technical_answers[last_question] += f"\nFollow-up Answer: {prompt}"
                        
                        st.session_state.is_awaiting_follow_up_answer = False
                        st.session_state.tech_question_index += 1 # Now, move to the next main question
                    
                    # Case 2: User is answering a main technical question
                    else:
                        current_question = st.session_state.technical_questions[st.session_state.tech_question_index]
                        st.session_state.technical_answers[current_question] = prompt
                        
                        # Generate a follow-up and check if it's valid
                        with st.spinner("Analyzing your answer..."):
                            follow_up = st.session_state.assessor.generate_follow_up_question(current_question, prompt)
                        
                        if follow_up:
                            st.session_state.messages.append({"role": "assistant", "content": follow_up})
                            st.session_state.is_awaiting_follow_up_answer = True # Set flag to wait for the next answer
                        else:
                            # If no follow-up, just move to the next question
                            st.session_state.tech_question_index += 1

                    # --- Ask the next main question if appropriate ---
                    if not st.session_state.is_awaiting_follow_up_answer:
                        if st.session_state.tech_question_index < len(st.session_state.technical_questions):
                            next_question = st.session_state.technical_questions[st.session_state.tech_question_index]
                            st.session_state.messages.append({"role": "assistant", "content": next_question})
                        else:
                            # Or conclude the interview
                            st.session_state.conversation_stage = "concluding"
                            conclusion_message = "Thank you for your answers. That's all the questions I have for now. The hiring team will review your responses and get in touch with you regarding the next steps."
                            st.session_state.messages.append({"role": "assistant", "content": conclusion_message})
                    
                    st.rerun()

if __name__ == "__main__":
    main()