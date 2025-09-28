import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure the API key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found in .env file.")
else:
    genai.configure(api_key=api_key)

    print("Finding available models for your API key...")
    print("-" * 30)
    
    # List all available models
    for m in genai.list_models():
      # Check if the model supports the 'generateContent' method
      if 'generateContent' in m.supported_generation_methods:
        print(f"- {m.name}")
        
    print("-" * 30)
    print("You can use any of the model names listed above in the app.py file.")
