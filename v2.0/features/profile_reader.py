import os
import json
import PyPDF2
from langchain_core.tools import tool

@tool
def read_user_profile(query: str = "") -> str:
    """
    CRITICAL TOOL: Reads Mr. Harjas's personal information, contact details, and full resume PDF.
    Use this tool EVERY TIME before you start filling out a job application in the browser.
    """
    try:
        # Resolve absolute paths based on where this script is located
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "my_data")
        
        json_path = os.path.join(data_dir, "quick_fill.json")
        pdf_path = os.path.join(data_dir, "harjas_resume.pdf")
        
        result = "--- MR. HARJAS PROFILE DATA ---\n\n"
        
        # 1. Read the Quick Fill JSON
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
                result += "--- QUICK FILL FIELDS ---\n"
                for key, value in data.items():
                    result += f"{key.replace('_', ' ').title()}: {value}\n"
        else:
            result += "WARNING: quick_fill.json not found.\n"
            
        # 2. Read the PDF Resume
        if os.path.exists(pdf_path):
            result += "\n--- FULL RESUME TEXT (harjas_resume.pdf) ---\n"
            with open(pdf_path, 'rb') as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    result += page.extract_text() + "\n"
        else:
            result += "\nWARNING: harjas_resume.pdf not found."
            
        return result
        
    except Exception as e:
        print(f"\n[CRITICAL SDE DEBUG] Raw Error: {str(e)}") 
        return f"SYSTEM ERROR reading profile data: {str(e)}"