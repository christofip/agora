from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView
from django.conf import settings
import os
from datetime import datetime
from .services.summarizer import SessionSummarizer
from .services.qa_service import QAService
import json
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
import markdown
from django.utils.safestring import mark_safe
from .services.topic_service import TopicExtractor

# Create your views here.

def test_setup(request):
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        file = request.FILES['pdf_file']
        fs = FileSystemStorage()
        filename = fs.save(f'pdf_documents/{file.name}', file)
        uploaded_file_url = fs.url(filename)
        return render(request, 'proceedings/test_setup.html', {
            'uploaded_file_url': uploaded_file_url
        })
    return render(request, 'proceedings/test_setup.html')

class Session:
    def __init__(self, filename):
        self.filename = filename
        self.path = f'pdf_documents/{filename}'
        self.title = filename.replace('.pdf', '')
        self._cache = {}
        self.summarizer = SessionSummarizer()
        self.topic_extractor = TopicExtractor()
        self.mps = [
            {"name": "MP 1", "party": "Party A", "contributions": "Placeholder contribution"},
            {"name": "MP 2", "party": "Party B", "contributions": "Placeholder contribution"},
        ]

    def _get_cached_property(self, name, generator_func):
        if name not in self._cache:
            try:
                data = generator_func()
                self._cache[name] = mark_safe(markdown.markdown(data))
            except Exception as e:
                print(f"Error getting {name}: {e}")
                self._cache[name] = f"Error loading {name}."
        return self._cache[name]

    def _get_pdf_content(self):
        """Get the PDF content using the summarizer's PDF reader"""
        pdf_path = os.path.join(settings.MEDIA_ROOT, 'pdf_documents', self.filename)
        return self.summarizer.read_pdf_content(pdf_path)

    @property
    def summary(self):
        return self._get_cached_property('summary', 
            lambda: self.summarizer.get_or_generate_summary(self.filename).get('summary', ''))

    @property
    def topics(self):
        return self._get_cached_property('topics',
            lambda: self.topic_extractor.get_or_generate_topics(
                self.filename, 
                self._get_pdf_content()  # Pass the PDF content instead of summary
            ).get('topics', ''))

    @property
    def url(self):
        return f'/media/pdf_documents/{self.filename}'

class SessionListView(ListView):
    template_name = 'proceedings/session_list.html'
    context_object_name = 'sessions'
    
    def get_queryset(self):
        pdf_dir = os.path.join(settings.MEDIA_ROOT, 'pdf_documents')
        sessions = []
        
        if os.path.exists(pdf_dir):
            for filename in sorted(os.listdir(pdf_dir)):
                if filename.endswith('.pdf'):
                    sessions.append(Session(filename))
                    
        return sessions

@method_decorator(csrf_protect, name='dispatch')
class SessionDetailView(DetailView):
    template_name = 'proceedings/session_detail.html'
    context_object_name = 'session'
    
    def get_object(self):
        filename = self.kwargs.get('filename')
        return Session(filename)

    def post(self, request, *args, **kwargs):
        """Handle Q&A interactions"""
        try:
            data = json.loads(request.body)
            question = data.get('question')
            chat_history = data.get('chat_history', [])
            
            if not question:
                return JsonResponse({'error': 'Question is required'}, status=400)

            session = self.get_object()
            qa_service = QAService()
            
            answer = qa_service.get_answer(
                question=question,
                chat_history=chat_history,
                filename=session.filename
            )

            return JsonResponse({
                'answer': answer
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

# Add a new view for fetching summary
def get_session_summary(request, filename):
    summarizer = SessionSummarizer()
    summary_data = summarizer.get_or_generate_summary(filename)
    return JsonResponse(summary_data)

@require_http_methods(["GET"])
def session_topics_view(request, filename):
    """API endpoint to get topics for a session"""
    try:
        session = Session(filename)
        topics_data = session.topic_extractor.get_or_generate_topics(
            filename,
            os.path.join(settings.MEDIA_ROOT, 'pdf_documents', filename)
        )
        return JsonResponse({
            'topics': topics_data.get('topics', ''),
            'status': 'success'
        })
    except Exception as e:
        print(f"Error getting topics: {e}")
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)

@method_decorator(csrf_protect, name='dispatch')
@require_http_methods(["POST"])
def session_qa_view(request, filename):
    """API endpoint for Q&A interactions"""
    try:
        data = json.loads(request.body)
        question = data.get('question')
        chat_history = data.get('chat_history', [])
        
        if not question:
            return JsonResponse({'error': 'Question is required'}, status=400)

        session = Session(filename)
        qa_service = QAService()
        
        answer = qa_service.get_answer(
            question=question,
            chat_history=chat_history,
            filename=session.filename
        )

        return JsonResponse({
            'answer': answer,
            'status': 'success'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error in Q&A: {e}")  # For debugging
        return JsonResponse({'error': str(e)}, status=500)
