import os
import json
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
from django.conf import settings
import PyPDF2

class SessionSummarizer:
    CACHE_DIR = 'media/summaries'

    def __init__(self):
        # Ensure cache directory exists
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        
        # Initialize Gemini (you'll need to set GEMINI_API_KEY in settings)
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')

    def get_cache_path(self, filename):
        """Get path for cached summary"""
        return os.path.join(self.CACHE_DIR, f"{filename}.json")

    def get_cached_summary(self, filename):
        """Retrieve cached summary if it exists"""
        cache_path = self.get_cache_path(filename)
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def cache_summary(self, filename, summary_data):
        """Save summary to cache"""
        cache_path = self.get_cache_path(filename)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)

    def read_pdf_content(self, pdf_path):
        """Extract text content from PDF"""
        text_content = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
            return text_content
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    def generate_summary(self, pdf_path):
        """Generate summary using Gemini"""
        # Read PDF content
        pdf_content = self.read_pdf_content(pdf_path)
        if not pdf_content:
            return {
                'summary': "Error: Could not read PDF content",
                'generated_at': str(datetime.now()),
                'format': 'markdown'
            }

        prompt = f"""
        Based on the following parliamentary session transcript, please provide a summary including:
        1. Main topics discussed - an emphasis on the discussion around legislation
        2. Notable debates or disagreements
        3. Key decisions made
        4. Voting results with the number of votes for and against

        Format the response in markdown with clear headings and bullet points.

        Transcript:
        {pdf_content[:30000]}  # Limiting content length to avoid token limits
        """
        
        response = self.model.generate_content(prompt)
        
        return {
            'summary': response.text,
            'generated_at': str(datetime.now()),
            'format': 'markdown'
        }

    def get_or_generate_summary(self, filename):
        """Get cached summary or generate new one"""
        # Try to get cached summary
        summary_data = self.get_cached_summary(filename)
        
        if summary_data is None:
            # Generate new summary
            pdf_path = os.path.join(settings.MEDIA_ROOT, 'pdf_documents', filename)
            summary_data = self.generate_summary(pdf_path)
            # Cache the new summary
            self.cache_summary(filename, summary_data)
        
        return summary_data
