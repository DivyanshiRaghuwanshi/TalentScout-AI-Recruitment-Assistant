import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.vectorstores import FAISS
import os

def process_resume(uploaded_file):
    """
    Reads a PDF resume, processes its text, and creates a searchable vector store.

    Args:
        uploaded_file: The file object uploaded via Streamlit's file_uploader.

    Returns:
        A FAISS vector store retriever object if successful, otherwise None.
    """
    if uploaded_file is None:
        return None

    try:
        # Read the PDF content from the uploaded file
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        resume_text = ""
        for page in doc:
            resume_text += page.get_text()
        
        if not resume_text.strip():
            return None

        # 1. Split the text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_text(text=resume_text)

        # 2. Create embeddings
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=os.getenv("GOOGLE_API_KEY"))

        # 3. Create a FAISS vector store
        vector_store = FAISS.from_texts(chunks, embedding=embeddings)

        return vector_store.as_retriever()

    except Exception as e:
        print(f"Error processing resume: {e}")
        return None
