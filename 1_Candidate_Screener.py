import streamlit as st
import os
import json
from datetime import datetime
from validators import validate_form
from resume_processor import process_resume
from interview_graph import interview_app, InterviewState, generate_summary_node, generate_easier_question_node

# --- UI & Helper Functions ---

def display_chat_history():
    """Displays the chat messages stored in session state."""
    if "messages" in st.session_state.interview_state:
        for message in st.session_state.interview_state["messages"]:
            role = message["role"]
            avatar = "🧑‍💻" if role == "user" else "🤖"
            with st.chat_message(role, avatar=avatar):
                st.markdown(message["content"])

def save_and_download_summary(summary_data):
    """Saves the summary to a file and provides a download button."""
    summaries_dir = "summaries"
    if not os.path.exists(summaries_dir):
        os.makedirs(summaries_dir)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate_name = summary_data.get("candidate_details", {}).get("full_name", "candidate").replace(" ", "_")
    file_name = f"{timestamp_str}_{candidate_name}.json"
    file_path = os.path.join(summaries_dir, file_name)

    json_string = json.dumps(summary_data, indent=4)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_string)
    except IOError as e:
        st.error(f"Failed to save summary file: {e}")

    st.download_button(
        label="Download Screening Summary (JSON)",
        data=json_string,
        file_name=f"talent_scout_summary_{candidate_name}.json",
        mime="application/json",
    )

def load_css(file_name):
    """Loads a local CSS file into the Streamlit app."""
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- Main Application Logic ---

def initialize_app():
    """Sets up the Streamlit page and initial markdown."""
    st.set_page_config(page_title="TalentScout AI", page_icon="🤖")
    st.title("💼 Welcome to TalentScout AI 🤖")
    st.markdown("""
    Hello! I'm **Scout**, your AI assistant for the first stage of our interview process. My goal is to get to know you a bit better.
    
    **Here’s how our session will work:**
    1.  **Your Details:** First, you'll fill out the form below. You can also upload your resume to help me ask more relevant questions.
    2.  **Technical Questions:** Based on your tech stack, I will ask you a few technical questions one by one.
    3.  **Follow-ups:** I may ask brief follow-up questions to dive deeper.

    **A quick note on the questions:**
    *   You will have an **"Easier Question"** button available for each main technical question.
    *   Feel free to use it if a question is too tough. Your use of this option will be noted in the final summary.

    Let's get started!
    """)

def initialize_session_state():
    """Initializes or resets the session state for a new interview."""
    if 'interview_state' not in st.session_state:
        st.session_state.interview_state = InterviewState(
            candidate_details={},
            tech_stack=[],
            resume_retriever=None,
            technical_questions=[],
            technical_answers={},
            tech_question_index=0,
            current_question_key=None,
            is_awaiting_follow_up_answer=False,
            user_input="",
            messages=[],
            final_summary=""
        )
    if 'stage' not in st.session_state:
        st.session_state.stage = "gathering_info"

def main():
    load_css("style.css")
    initialize_app()
    initialize_session_state()

    # --- Stage 1: Information Gathering Form ---
    if st.session_state.stage == "gathering_info":
        with st.form("candidate_form"):
            st.write("Please provide your details:")
            uploaded_resume = st.file_uploader("Upload your Resume (Optional, PDF only)", type="pdf")
            details = {
                "full_name": st.text_input("Full Name"),
                "email": st.text_input("Email Address"),
                "phone_number": st.text_input("Phone Number"),
                "experience": st.number_input("Years of Professional Experience", min_value=0, step=1),
                "desired_position": st.text_input("Desired Position"),
                "current_location": st.text_input("Current Location"),
                "tech_stack": st.text_input("Primary Tech Stack (comma-separated)"),
            }
            submitted = st.form_submit_button("Submit Details")

            if submitted:
                is_valid, errors = validate_form(details)
                if is_valid:
                    # Update the interview state
                    current_state = st.session_state.interview_state
                    current_state["candidate_details"] = details
                    current_state["tech_stack"] = [tech.strip() for tech in details.get("tech_stack", "").split(',')]
                    
                    if uploaded_resume:
                        with st.spinner("Analyzing resume..."):
                            current_state["resume_retriever"] = process_resume(uploaded_resume)

                    # --- Invoke the graph to generate questions ---
                    with st.spinner("Generating technical questions..."):
                        # We start the graph from the beginning
                        updated_state = interview_app.invoke(current_state, {"recursion_limit": 5})
                    
                    # Store the new state and move to the next stage
                    st.session_state.interview_state = updated_state
                    st.session_state.interview_state["messages"].append(
                        {"role": "assistant", "content": "Thank you for providing your details. Now, based on your tech stack, I have a few technical questions for you."}
                    )
                    # The first question is asked via the graph's flow, but we need to display it
                    first_question = updated_state["technical_questions"][0]
                    st.session_state.interview_state["messages"].append(
                        {"role": "assistant", "content": first_question}
                    )
                    st.session_state.interview_state["current_question_key"] = first_question
                    st.session_state.stage = "in_interview"
                    st.rerun()
                else:
                    for error in errors:
                        st.error(error)

    # --- Stage 2: The Main Interview Loop ---
    elif st.session_state.stage == "in_interview":
        display_chat_history()
        
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("Easier Question"):
                with st.spinner("Generating an easier question..."):
                    # Invoke the specific node for generating an easier question
                    easier_question_state = generate_easier_question_node(st.session_state.interview_state)
                    st.session_state.interview_state.update(easier_question_state)
                    st.rerun()

        with col1:
            if prompt := st.chat_input("Your answer..."):
                current_state = st.session_state.interview_state
                current_state["user_input"] = prompt
                current_state["messages"].append({"role": "user", "content": prompt})

                # Display user message
                with st.chat_message("user", avatar="🧑‍💻"):
                    st.markdown(prompt)
                
                with st.spinner("Analyzing your answer..."):
                    # Invoke the graph to process the answer
                    updated_state = interview_app.invoke(
                        current_state,
                        {"recursion_limit": 5}
                    )
                
                st.session_state.interview_state = updated_state

                # Check if the interview is over by seeing if a summary was generated
                if updated_state.get("final_summary"):
                    st.session_state.stage = "concluding"
                    st.session_state.interview_state["messages"].append(
                        {"role": "assistant", "content": "Thank you for your answers. That's all the questions I have for now. The hiring team will review your responses and get in touch with you regarding the next steps."}
                    )
                # If not over, and if we are not waiting for a follow-up, ask the next question
                elif not updated_state["is_awaiting_follow_up_answer"]:
                    next_question_index = updated_state["tech_question_index"]
                    if next_question_index < len(updated_state["technical_questions"]):
                        next_question = updated_state["technical_questions"][next_question_index]
                        st.session_state.interview_state["messages"].append({"role": "assistant", "content": next_question})
                        st.session_state.interview_state["current_question_key"] = next_question

                st.rerun()

    # --- Stage 3: Conclusion and Summary ---
    elif st.session_state.stage == "concluding":
        # We might need to run the summary node one last time if the graph ended
        if not st.session_state.interview_state.get("final_summary"):
             with st.spinner("Generating final summary..."):
                summary_state = generate_summary_node(st.session_state.interview_state)
                st.session_state.interview_state.update(summary_state)

        display_chat_history()
        st.info("You have completed the initial screening. Thank you for your time!")
        
        final_state = st.session_state.interview_state
        summary_html = final_state["final_summary"].replace("\n", "<br>")
        st.markdown(f'<div class="summary-card"><h3>AI Performance Summary</h3><p>{summary_html}</p></div>', unsafe_allow_html=True)

        # Prepare data for saving
        summary_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "candidate_details": final_state["candidate_details"],
            "ai_summary": final_state["final_summary"],
            "technical_responses": final_state["technical_answers"]
        }
        save_and_download_summary(summary_data)
        # Prevent further interaction after completion
        st.stop()

if __name__ == "__main__":
    main()