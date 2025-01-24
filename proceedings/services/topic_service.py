import os
import json
from datetime import datetime
from pathlib import Path
import google.generativeai as genai
from django.conf import settings
import re

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

    def extract_topics(self, text: str) -> dict:
        """Extract topics from the session text using the signpost"""
        prompt = """
        Ανάλυσε το παρακάτω κείμενο της συνεδρίασης και εντόπισε όλα τα νομοθετικά θέματα.
        
        ΣΗΜΑΝΤΙΚΟ: Κάθε νέο θέμα ξεκινά με τη φράση "Η σχετική έκθεση". 
        Χρησιμοποίησε αυτή τη φράση ως σημείο αναφοράς για να εντοπίσεις τα θέματα.
        
        Για κάθε θέμα που εντοπίζεις, παρέχε:
        1. Τίτλο του νομοσχεδίου/πρότασης/τροπολογίας (όπως αναφέρεται μετά το "Η σχετική έκθεση")
        2. Σκοπό (τι προσπαθεί να επιτύχει)
        3. Προτεινόμενες αλλαγές (τι συγκεκριμένα προτείνεται να αλλάξει)
        
        Μορφοποίησε την απάντηση σε markdown ως εξής:
        
        ## [Αριθμός]. [Τίτλος νομοσχεδίου]
        
        ### Σκοπός
        [Περιγραφή σκοπού]
        
        ### Προτεινόμενες Αλλαγές
        - [Αλλαγή 1]
        - [Αλλαγή 2]
        κλπ.
        
        Αν δεν υπάρχουν θέματα που ξεκινούν με "Η σχετική έκθεση", απάντησε:
        "Δεν εντοπίστηκαν νομοθετικά θέματα με την τυπική μορφή έκθεσης στα πρακτικά."
        
        Κείμενο συνεδρίασης:
        {text}
        """

        # First, let's identify all sections starting with "Η σχετική έκθεση"
        sections = re.split(r'(?=Η σχετική έκθεση)', text)
        
        # If we don't find any sections, use the entire text
        if len(sections) <= 1:
            response = self.model.generate_content(prompt.format(text=text))
            return {
                'topics': response.text,
                'generated_at': str(datetime.now()),
                'sections_found': 0
            }
        
        # Create a more focused prompt for the identified sections
        sections_prompt = """
        Ανάλυσε τα παρακάτω νομοθετικά θέματα που εντοπίστηκαν στη συνεδρίαση.
        
        Για κάθε θέμα, παρέχε:
        1. Τίτλο του νομοσχεδίου/πρότασης/τροπολογίας
        2. Σκοπό (τι προσπαθεί να επιτύχει)
        3. Προτεινόμενες αλλαγές (τι συγκεκριμένα προτείνεται να αλλάξει)
        
        Θέματα προς ανάλυση:
        
        {sections}
        
        Μορφοποίησε την απάντηση σε markdown ως εξής:
        
        ## [Αριθμός]. [Τίτλος νομοσχεδίου]
        
        ### Σκοπός
        [Περιγραφή σκοπού]
        
        ### Προτεινόμενες Αλλαγές
        - [Αλλαγή 1]
        - [Αλλαγή 2]
        κλπ.
        """
        
        # Join the sections with clear separators
        formatted_sections = "\n\n---ΝΕΟΣ ΤΟΜΕΑΣ---\n\n".join(sections[1:])  # Skip first split if empty
        
        response = self.model.generate_content(sections_prompt.format(sections=formatted_sections))
        
        return {
            'topics': response.text,
            'generated_at': str(datetime.now()),
            'sections_found': len(sections) - 1
        }

    def get_or_generate_topics(self, filename: str, text: str) -> dict:
        """Get cached topics or generate new ones"""
        topics_data = self.get_cached_topics(filename)
        
        if topics_data is None:
            topics_data = self.extract_topics(text)
            self.cache_topics(filename, topics_data)
        
        return topics_data 