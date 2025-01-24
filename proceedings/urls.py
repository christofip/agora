from django.urls import path
from . import views

app_name = 'proceedings'

urlpatterns = [
    path('', views.SessionListView.as_view(), name='session_list'),
    path('session/<str:filename>/', views.SessionDetailView.as_view(), name='session_detail'),
    path('session/<str:filename>/summary/', views.get_session_summary, name='session_summary'),
] 