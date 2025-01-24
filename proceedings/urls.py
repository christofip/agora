from django.urls import path
from . import views

app_name = 'proceedings'

urlpatterns = [
    path('', views.SessionListView.as_view(), name='session_list'),
    path('session/<str:filename>/', views.SessionDetailView.as_view(), name='session_detail'),
    path('session/<str:filename>/topics/', views.session_topics_view, name='session_topics'),
    path('session/<str:filename>/qa/', views.session_qa_view, name='session_qa'),
] 