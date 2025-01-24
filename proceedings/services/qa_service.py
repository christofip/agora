import os
import json
from pathlib import Path
import google.generativeai as genai
from django.conf import settings
from django.core.cache import cache
from typing import List, Dict
import PyPDF2
import re
from tqdm import tqdm

class PDFTextExtractor:
    def __init__(self):
        self.page_break_pattern = re.compile(r'\f')  # Form feed character
        self.whitespace_pattern = re.compile(r'\s+')

    def extract_text(self, pdf_path: str) -> str:
        """Extract and preprocess text from PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                # Create PDF reader object
                reader = PyPDF2.PdfReader(file)
                
                # Extract text from each page with progress bar
                text_parts = []
                for page in tqdm(reader.pages, desc="Extracting PDF text"):
                    text = page.extract_text()
                    if text:
                        # Basic preprocessing
                        text = self._preprocess_text(text)
                        text_parts.append(text)

                return '\n'.join(text_parts)

        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")

    def _preprocess_text(self, text: str) -> str:
        """Clean and preprocess extracted text"""
        # Remove form feed characters
        text = self.page_break_pattern.sub('\n', text)
        
        # Normalize whitespace
        text = self.whitespace_pattern.sub(' ', text)
        
        # Remove headers/footers (customize based on your PDF format)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Skip page numbers
            if line.strip().isdigit():
                continue
            # Skip common headers/footers (customize as needed)
            if any(header in line for header in ['ΒΟΥΛΗ ΤΩΝ ΑΝΤΙΠΡΟΣΩΠΩΝ', 'Σελίδα']):
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

class PDFChunkManager:
    CACHE_DIR = 'media/chunks'
    CHUNK_SIZE = 1000  # Approximate characters per chunk
    OVERLAP = 100      # Character overlap between chunks
    
    def __init__(self):
        self.extractor = PDFTextExtractor()
        os.makedirs(self.CACHE_DIR, exist_ok=True)

    def get_cache_path(self, filename: str) -> dict:
        """Get path for cached chunks"""
        base = os.path.splitext(filename)[0]
        return {
            'chunks': os.path.join(self.CACHE_DIR, f"{base}_chunks.json"),
        }

    def chunk_exists(self, filename: str) -> bool:
        """Check if chunks exist for this file"""
        return os.path.exists(self.get_cache_path(filename)['chunks'])

    def create_chunks(self, pdf_path: str, filename: str):
        """Create and cache chunks from PDF text"""
        # Extract text
        text = self.extractor.extract_text(pdf_path)
        
        # Create chunks
        chunks = self._create_text_chunks(text)
        
        # Save chunks
        cache_path = self.get_cache_path(filename)['chunks']
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

    def _create_text_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            # Get chunk with overlap
            end = start + self.CHUNK_SIZE
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                # Find last period or newline
                last_break = max(
                    chunk.rfind('. '),
                    chunk.rfind('.\n'),
                    chunk.rfind('\n')
                )
                if last_break != -1:
                    chunk = chunk[:last_break + 1]
                    end = start + last_break + 1

            # Add chunk if it's not too short
            if len(chunk.strip()) > 100:  # Minimum chunk size
                chunks.append(chunk.strip())
            
            # Move start position, accounting for overlap
            start = end - self.OVERLAP

        return chunks

    def get_relevant_chunks(self, filename: str, query: str, k: int = 5) -> List[str]:
        """Get most relevant chunks for a query using basic keyword matching"""
        cache_path = self.get_cache_path(filename)['chunks']
        
        with open(cache_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        # Simple relevance scoring based on keyword matching
        query_words = set(query.lower().split())
        chunk_scores = []
        
        for chunk in chunks:
            chunk_words = set(chunk.lower().split())
            score = len(query_words.intersection(chunk_words))
            chunk_scores.append((score, chunk))
        
        # Sort by score and return top k chunks
        chunk_scores.sort(reverse=True)
        return [chunk for score, chunk in chunk_scores[:k]]

class QAService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        self.chunk_manager = PDFChunkManager()
        
    def _get_cache_key(self, question: str, filename: str) -> str:
        return f"qa_cache:{filename}:{hash(question)}"

    def get_answer(self, question: str, chat_history: List[Dict], filename: str) -> str:
        # Check cache first
        cache_key = self._get_cache_key(question, filename)
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response

        # Ensure chunks exist
        if not self.chunk_manager.chunk_exists(filename):
            pdf_path = os.path.join(settings.MEDIA_ROOT, 'pdf_documents', filename)
            self.chunk_manager.create_chunks(pdf_path, filename)

        # Get relevant chunks
        relevant_chunks = self.chunk_manager.get_relevant_chunks(filename, question)
        
        # Format context and prompt
        context = "\n".join(relevant_chunks)
        formatted_history = "\n".join([
            f"{'Χρήστης' if msg['role'] == 'user' else 'Βοηθός'}: {msg['content']}"
            for msg in chat_history[-3:]
        ])

        prompt = f"""
        Είσαι ένας βοηθός που βοηθά τους χρήστες να κατανοήσουν τα πρακτικά των συνεδριάσεων της Βουλής των Αντιπροσώπων της Κύπρου.

        Οδηγίες:
        1. Χρησιμοποίησε μόνο τις πληροφορίες που παρέχονται στο παρακάτω κείμενο για να απαντήσεις στην ερώτηση
        2. Αν η πληροφορία δεν υπάρχει στο κείμενο, απάντησε "Δεν μπορώ να βρω αυτή την πληροφορία στα πρακτικά της συνεδρίασης"
        3. Απάντησε στα Ελληνικά με σαφή και κατανοητό τρόπο
        4. Αν χρειάζεται να αναφέρεις αριθμούς ή ημερομηνίες, γράψε τους με ακρίβεια
        5. Αν αναφέρεσαι σε βουλευτές, χρησιμοποίησε το πλήρες όνομα και την ιδιότητά τους

        Σχετικό κείμενο από τη συνεδρίαση:
        {context}

        Προηγούμενη συζήτηση:
        {formatted_history}

        Ερώτηση: {question}
        
        Απάντηση:
        """

        # Generate response
        response = self.model.generate_content(prompt)
        answer = response.text

        # Cache the response
        cache.set(cache_key, answer, timeout=3600)

        return answer
