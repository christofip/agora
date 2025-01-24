import os
import json
from datetime import datetime
from pathlib import Path
import google.generativeai as genai
from django.conf import settings
from PyPDF2 import PdfReader

class TopicExtractor:
    CACHE_DIR = 'media/topics'

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        os.makedirs(self.CACHE_DIR, exist_ok=True)

    def get_cache_path(self, filename: str) -> str:
        """Get path for cached topics"""
        base = os.path.splitext(filename)[0]
        return os.path.join(self.CACHE_DIR, f"{base}_topics.json")

    def get_cached_topics(self, filename: str) -> dict:
        """Retrieve cached topics if they exist"""
        cache_path = self.get_cache_path(filename)
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def cache_topics(self, filename: str, topics_data: dict):
        """Save topics to cache"""
        cache_path = self.get_cache_path(filename)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(topics_data, f, ensure_ascii=False, indent=2)

    def read_pdf_content(self, pdf_path: str) -> str:
        """Read content from PDF file"""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    def extract_topics(self, text: str) -> dict:
        """Extract topics from the session text"""
        if not text.strip():
            return {
                'topics': "Error: No content available to analyze",
                'generated_at': str(datetime.now()),
                'sections_found': False
            }

        prompt = """
        Ανάλυσε το παρακάτω κείμενο της κοινοβουλευτικής συνεδρίασης και εντόπισε όλα τα νομοθετικά θέματα.
        
        Για κάθε θέμα που εντοπίζεις, παρέχε:
        1. Τίτλο του νομοσχεδίου/πρότασης/τροπολογίας
        2. Σκοπό (τι προσπαθεί να επιτύχει)
        3. Προτεινόμενες αλλαγές (τι συγκεκριμένα προτείνεται να αλλάξει)
        4. Αποτέλεσμα ψηφοφορίας (αν υπάρχει)
        
        Μορφοποίησε την απάντηση σε markdown ως εξής:
        
        ## 1. [Τίτλος νομοσχεδίου]
        
        ### Σκοπός
        [Περιγραφή σκοπού]
        
        ### Προτεινόμενες Αλλαγές
        - [Αλλαγή 1]
        - [Αλλαγή 2]
        
        ### Αποτέλεσμα
        [Αποτέλεσμα ψηφοφορίας αν υπάρχει]
        
        Κείμενο συνεδρίασης:
        {text}
        """
        
        try:
            response = self.model.generate_content(prompt.format(text=text[:30000]))
            return {
                'topics': response.text,
                'generated_at': str(datetime.now()),
                'sections_found': True
            }
        except Exception as e:
            print(f"Error generating topics: {e}")
            return {
                'topics': f"Error generating topics: {str(e)}",
                'generated_at': str(datetime.now()),
                'sections_found': False
            }

    def get_or_generate_topics(self, filename: str, text: str) -> dict:
        """Get cached topics or generate new ones"""
        topics_data = self.get_cached_topics(filename)
        
        if topics_data is None:
            if os.path.isfile(text):
                text = self.read_pdf_content(text)
            topics_data = self.extract_topics(text)
            self.cache_topics(filename, topics_data)
        
        return topics_data 