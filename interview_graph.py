import os
import re
import json
from typing import TypedDict, List, Dict, Any
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langgraph.graph import StateGraph, END

# --- Model Initialization ---
# Load environment variables
load_dotenv()

try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Google API key not found. Please ensure it is set in the .env file.")
    
    # We wrap the model with LangChain for better integration
    model = ChatGoogleGenerativeAI(model="gemini-pro-latest", google_api_key=api_key, convert_system_message_to_human=True)

except Exception as e:
    # This will be caught by the Streamlit app, but it's good practice to handle it here
    print(f"Error initializing model: {e}")
    model = None

# --- Graph State Definition ---

class InterviewState(TypedDict):
    """
    Represents the state of our interview graph.
    This state is passed between nodes and updated as the interview progresses.
    """
    candidate_details: Dict[str, Any]
    tech_stack: List[str]
    resume_retriever: Any  # This will be a FAISS retriever instance
    
    technical_questions: List[str]
    technical_answers: Dict[str, Dict[str, str]]
    
    # Tracking the conversation flow
    tech_question_index: int
    current_question_key: str
    is_awaiting_follow_up_answer: bool
    
    # User input and chat history
    user_input: str
    messages: List[Dict[str, str]]
   
    final_summary: str

# --- Helper Functions & Chains ---

def get_resume_context(tech_stack: List[str], retriever: Any) -> str:
    """Extracts relevant context from the resume for a given tech stack."""
    context = ""
    if not retriever:
        return context
        
    for tech in tech_stack:
        try:
            docs = retriever.get_relevant_documents(tech)
            if docs:
                context += f"Context from resume related to {tech}:\n"
                for doc in docs:
                    context += f"- {doc.page_content}\n"
        except Exception:
            # Ignore errors if a tech isn't found in the resume
            pass
    return context

def fallback_questions():
    return [
        "Could you describe a challenging project you've worked on with your listed technologies?",
        "How do you stay updated with the latest trends in your tech stack?"
    ]

# --- Node Definitions ---

def generate_questions_node(state: InterviewState):
    """
    Generates the initial set of technical questions based on the tech stack and resume.
    """
    tech_stack = state["tech_stack"]
    retriever = state["resume_retriever"]
    
    resume_context = get_resume_context(tech_stack, retriever)
    
    if resume_context:
        # If we have resume context, use the more detailed prompt
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """
You are "Scout", an AI hiring assistant for a top-tier tech company. Your persona is that of a sharp, experienced senior engineer.
Your goal is to generate 3-5 deeply insightful technical questions that synthesize the candidate's declared tech stack with the specific projects and experiences mentioned in their resume.
Follow these rules:
1.  **Prioritize Resume Context:** Base your questions on the resume context provided. Refer to specific details if possible (e.g., "In your resume, you mentioned a project using Django...").
2.  **Probe Deeper:** Ask "how," "why," or "describe" questions that probe for understanding of core principles, trade-offs, and practical application.
3.  **Scenario-Based:** Include at least one scenario-based question relevant to their experience.
4.  **No Generic Questions:** Avoid simple definitions or questions that could be answered without the resume context.
Format the output *only* as a numbered list. Do not include any other text, introduction, or conclusion.
            """),
            ("human", "The candidate's self-declared tech stack is: {tech_stack}.\n\nHere is the context from their resume:\n---\n{resume_context}\n---")
        ])
        chain = prompt_template | model | StrOutputParser()
        try:
            response = chain.invoke({"tech_stack": ", ".join(tech_stack), "resume_context": resume_context})
            questions = re.findall(r'\d+\.\s*(.*)', response)
            if not questions:
                questions = fallback_questions()
        except Exception:
            questions = fallback_questions()
    else:
        # Fallback to the generic prompt if no resume context is available
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """
You are "Scout", an AI hiring assistant for a top-tier tech company. Your persona is that of a sharp, experienced senior engineer.
A candidate is applying for a software engineering role and has listed their tech stack.
Your goal is to generate 3-5 deeply insightful technical questions to accurately gauge their skills. Follow these rules:
1.  For each technology listed, generate at least one relevant question.
2.  Focus on open-ended questions that start with "How," "Why," or "Describe." Avoid simple definitions.
3.  Include at least one scenario-based question (e.g., "Imagine you have a slow database query... How would you debug it?").
4.  The questions should probe for understanding of core principles, trade-offs, and practical application, not just textbook knowledge.
Format the output *only* as a numbered list. Do not include any other text, introduction, or conclusion.
            """),
            ("human", "The candidate's tech stack is: {tech_stack}.")
        ])
        chain = prompt_template | model | StrOutputParser()
        try:
            response = chain.invoke({"tech_stack": ", ".join(tech_stack)})
            questions = re.findall(r'\d+\.\s*(.*)', response)
            if not questions:
                questions = fallback_questions()
        except Exception:
            questions = fallback_questions()

    return {"technical_questions": [q.strip() for q in questions]}


def analyze_answer_node(state: InterviewState):
    """
    Analyzes the user's answer and decides on the next step (follow-up or next question).
    """
    current_question = state["current_question_key"]
    user_answer = state["user_input"]

    # Initialize variables
    messages = state["messages"]
    current_answers = state.get("technical_answers", {})
    next_question_index = state["tech_question_index"]

    # Case 1: This is an answer to a follow-up question.
    if state["is_awaiting_follow_up_answer"]:
        # Append the follow-up answer and move to the next main question.
        current_answers[current_question]['answer'] += f"\n\n*Follow-up Answer:*\n{user_answer}"
        is_awaiting_follow_up = False
        next_question_index += 1
    
    # Case 2: This is an answer to a main technical question.
    else:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are "Scout", an AI hiring assistant. Your persona is that of a sharp, experienced senior engineer.

Your task is to perform two actions based on the candidate's answer:
1.  **Analyze Sentiment:** Classify the candidate's answer as one of: "Confident", "Neutral", or "Hesitant".
2.  **Generate Follow-up:** Create a single, insightful follow-up question to probe deeper. If the answer is weak, ask for clarification. If it's good, build on it. If no follow-up is necessary, return `null`.

Provide the output *only* as a valid JSON object with two keys: "sentiment" and "follow_up_question".

Example for a good answer:
{{
    "sentiment": "Confident",
    "follow_up_question": "That's a good overview. Can you describe a time you had to optimize a query like that in a real-world project?"
}}

Example for when no follow-up is needed:
{{
    "sentiment": "Neutral",
    "follow_up_question": null
}}
            """),
            ("human", "The original question was: \"{original_question}\"\nThe candidate's answer was: \"{user_answer}\"")
        ])
        
        chain = prompt | model | JsonOutputParser()
        
        try:
            analysis = chain.invoke({
                "original_question": current_question,
                "user_answer": user_answer
            })
            sentiment = analysis.get("sentiment", "N/A")
            follow_up = analysis.get("follow_up_question")
        except Exception:
            sentiment = "N/A"
            follow_up = None

        # Store the main answer and sentiment
        current_answers[current_question] = {
            "answer": user_answer,
            "sentiment": sentiment
        }

        # If a follow-up is generated, ask it and wait.
        if follow_up:
            messages += [{"role": "assistant", "content": follow_up}]
            is_awaiting_follow_up = True
            # The question index does NOT advance here.
        # If no follow-up, advance to the next question.
        else:
            is_awaiting_follow_up = False
            next_question_index += 1

    return {
        "technical_answers": current_answers,
        "is_awaiting_follow_up_answer": is_awaiting_follow_up,
        "tech_question_index": next_question_index,
        "messages": messages,
    }

def generate_summary_node(state: InterviewState):
    """
    Generates a final summary of the candidate's performance.
    """
    answers = state["technical_answers"]
    if not answers:
        return {"final_summary": "No technical answers were provided."}

    qa_text = ""
    for q, a_info in answers.items():
        answer = a_info.get('answer', 'No answer provided.')
        sentiment = a_info.get('sentiment', 'N/A')
        qa_text += f"Question: {q}\nSentiment: {sentiment}\nAnswer: {answer}\n\n"

    prompt = ChatPromptTemplate.from_messages([
        ("system", """
You are a senior engineering manager reviewing a candidate's technical screening.
Based on the following questions and answers, provide a concise, professional summary of the candidate's performance.

Your summary should include:
1.  **Overall Impression:** A brief, one-sentence summary.
2.  **Strengths:** 1-2 bullet points highlighting areas where the candidate demonstrated strong knowledge, considering their sentiment.
3.  **Areas for Improvement:** 1-2 bullet points identifying topics where the candidate seemed weak or could be probed further, considering their sentiment.

Keep the tone objective and constructive.
        """),
        ("human", "CANDIDATE'S Q&A:\n---\n{qa_text}\n---\n\nSUMMARY:")
    ])
    
    chain = prompt | model | StrOutputParser()
    
    try:
        summary = chain.invoke({"qa_text": qa_text})
        return {"final_summary": summary}
    except Exception as e:
        print(f"Error generating summary: {e}")
        return {"final_summary": f"Could not generate AI summary due to an error: {e}"}

def generate_easier_question_node(state: InterviewState):
    """
    Generates an easier version of the current question.
    """
    current_question = state["technical_questions"][state["tech_question_index"]]
    tech_stack = state["tech_stack"]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """
You are "Scout", an AI hiring assistant.
A candidate found the following question too difficult: "{original_question}"

The candidate's tech stack is: {tech_stack}.

Your task is to generate a single, more fundamental, and easier question on the *same topic* as the original question.
For example, if the original question was about advanced database indexing strategies, a good easier question would be about the basic purpose of database indexes.

Format the output as just the question text. Do not include any other text, introduction, or numbering.
        """),
        ("human", "Original question: {original_question}\nTech stack: {tech_stack}")
    ])
    
    chain = prompt | model | StrOutputParser()
    
    try:
        new_question = chain.invoke({
            "original_question": current_question,
            "tech_stack": ", ".join(tech_stack)
        })
    except Exception:
        new_question = "Could you please describe a core concept related to your tech stack?"

    # Update the questions list and the latest message
    questions = state["technical_questions"]
    messages = state["messages"]
    
    questions[state["tech_question_index"]] = new_question
    messages[-1] = {"role": "assistant", "content": new_question}
    
    return {"technical_questions": questions, "messages": messages}

# --- Conditional Edge Logic ---

def should_continue(state: InterviewState) -> str:
    """
    Determines the next step in the interview process.
    """
    # If we are now waiting for a follow-up answer, the graph should pause.
    if state["is_awaiting_follow_up_answer"]:
        return END

    # If we have asked all questions, generate the summary.
    if state["tech_question_index"] >= len(state["technical_questions"]):
        return "generate_summary"
    
    # Otherwise, the UI will ask the next question.
    return "ask_next_question"

# --- Graph Definition ---

def create_graph():
    """
    Creates and compiles the LangGraph for the interview process.
    """
    workflow = StateGraph(InterviewState)

    # Add nodes to the graph
    workflow.add_node("generate_questions", generate_questions_node)
    workflow.add_node("analyze_answer", analyze_answer_node)
    workflow.add_node("generate_summary", generate_summary_node)
    workflow.add_node("generate_easier_question", generate_easier_question_node)

    # Define the entry point of the graph
    workflow.set_entry_point("generate_questions")

    # Define the edges that control the flow
    workflow.add_edge("generate_questions", "analyze_answer")
    workflow.add_edge("generate_easier_question", "analyze_answer")
    
    # This edge is special: it's conditional. After analyzing an answer,
    # we decide whether to continue, summarize, or wait.
    workflow.add_conditional_edges(
        "analyze_answer",
        should_continue,
        {
            "ask_next_question": END, # The UI will ask the next question
            "generate_summary": "generate_summary",
            END: END # This is the crucial pause for follow-ups
        }
    )

    return workflow.compile()

# --- Compile the graph ---
interview_app = create_graph()
