import os
import json
from django.conf import settings
import genai

class BaseService:
    def __init__(self, cache_dir):
        self.CACHE_DIR = cache_dir
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')

    def get_cache_path(self, filename):
        base = os.path.splitext(filename)[0]
        return os.path.join(self.CACHE_DIR, f"{base}_{self.__class__.__name__.lower()}.json")

    def get_cached_data(self, filename):
        cache_path = self.get_cache_path(filename)
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def cache_data(self, filename, data):
        cache_path = self.get_cache_path(filename)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2) 