import streamlit as st
import os
import json
import pandas as pd
from auth import check_password as auth_check_password, set_password as auth_set_password

# --- Configuration ---
SUMMARIES_DIR = "summaries"

def login_screen():
    """Shows the login screen and returns True if login is successful."""
    st.header("Recruiter Login")
    password = st.text_input("Enter password", type="password")
    if not password:
        st.stop()
    
    if auth_check_password(password):
        st.session_state['logged_in'] = True
        return True
    else:
        st.error("Password incorrect.")
        st.stop()

def load_summaries():
    """Loads all candidate summaries from the summaries directory."""
    if not os.path.exists(SUMMARIES_DIR):
        return []

    all_summaries = []
    for filename in os.listdir(SUMMARIES_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(SUMMARIES_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Add filename for selection purposes
                    data['filename'] = filename
                    all_summaries.append(data)
            except (json.JSONDecodeError, IOError) as e:
                st.warning(f"Could not read or parse {filename}: {e}")
    
    # Sort by timestamp, newest first
    all_summaries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return all_summaries

def change_password_screen():
    st.header("Account Management")
    with st.expander("Change Password"):
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            submitted = st.form_submit_button("Change Password")

            if submitted:
                if not auth_check_password(current_password):
                    st.error("Current password is incorrect.")
                elif new_password != confirm_password:
                    st.error("New passwords do not match.")
                elif len(new_password) < 8:
                    st.error("New password must be at least 8 characters long.")
                else:
                    auth_set_password(new_password)
                    st.success("Password changed successfully!")

def load_css(file_name):
    """Loads a local CSS file into the Streamlit app."""
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Recruiter Dashboard", page_icon="📊")
    load_css("style.css") # Load custom CSS
    st.title("Recruiter Dashboard 📊")

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_screen()
    
    # --- Main Dashboard UI ---
    st.header("Candidate Summaries")
    summaries = load_summaries()

    if not summaries:
        st.info("No candidate summaries found yet. As candidates complete the screening, their results will appear here.")
    else:
        # Create a DataFrame for a clean, sortable table view
        overview_data = []
        for summary in summaries:
            details = summary.get('candidate_details', {})
            overview_data.append({
                "Timestamp": summary.get('timestamp', 'N/A'),
                "Name": details.get('full_name', 'N/A'),
                "Position": details.get('desired_position', 'N/A'),
                "Experience (Yrs)": details.get('experience', 'N/A'),
                "Tech Stack": details.get('tech_stack', 'N/A'),
                "File": summary.get('filename') # Keep a reference to the file
            })
        
        df = pd.DataFrame(overview_data)
        st.dataframe(df.drop(columns=['File']))

        st.header("View Full Summary")
        candidate_options = {f"{s.get('timestamp')} - {s.get('candidate_details', {}).get('full_name', 'N/A')}": s for s in summaries}
        selected_candidate_display = st.selectbox(
            "Select a candidate to view their detailed summary:",
            options=candidate_options.keys()
        )

        if selected_candidate_display:
            selected_summary = candidate_options[selected_candidate_display]
            st.subheader(f"Detailed Summary for {selected_summary.get('candidate_details', {}).get('full_name', 'N/A')}")
            
            st.markdown("#### AI-Generated Performance Summary")
            ai_summary = selected_summary.get('ai_summary', 'Not available.')
            summary_html = ai_summary.replace("\n", "<br>")
            # Use the custom card style
            st.markdown(f'<div class="summary-card">{summary_html}</div>', unsafe_allow_html=True)

            st.markdown("#### Technical Q&A Breakdown")
            responses = selected_summary.get("technical_responses", {})
            if not responses:
                st.write("No technical responses were recorded.")
            else:
                for question, response_data in responses.items():
                    with st.expander(f"Question: {question[:80]}..."):
                        # Handle both old (string) and new (dict) formats for backward compatibility
                        if isinstance(response_data, dict):
                            sentiment = response_data.get('sentiment', 'N/A')
                            answer = response_data.get('answer', 'No answer provided.')
                            
                            # Display sentiment with a corresponding emoji
                            if sentiment == "Confident":
                                st.markdown(f"**Sentiment:** {sentiment} ✅")
                            elif sentiment == "Hesitant":
                                st.markdown(f"**Sentiment:** {sentiment} ⚠️")
                            else:
                                st.markdown(f"**Sentiment:** {sentiment} 😐")
                                
                            st.markdown(f"**Answer:**\n\n> {answer.replace('n', '  n')}")
                        else:
                            # Fallback for old data format
                            st.markdown(f"**Answer:**\n\n> {response_data.replace('n', '  n')}")

            with st.expander("View Full Raw Data"):
                st.json(selected_summary)

    # --- Password Management UI ---
    change_password_screen()

if __name__ == "__main__":
    main()
