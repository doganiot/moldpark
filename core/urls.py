from django.urls import path
from . import views
from .api import SystemStatusAPI, production_pipeline_api, alerts_api, health_check_api

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),
    path('terms/', views.terms_of_service, name='terms'),
    path('privacy/', views.privacy_policy, name='privacy'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('api/system-status/', SystemStatusAPI.as_view(), name='api_system_status'),
    path('api/production-pipeline/', production_pipeline_api, name='api_production_pipeline'),
    path('api/alerts/', alerts_api, name='api_alerts'),
    path('api/health-check/', health_check_api, name='api_health_check'),
    
    # Mesajlaşma Sistemi
    path('messages/', views.message_list, name='message_list'),
    path('messages/create/', views.message_create, name='message_create'),
    path('messages/<int:pk>/', views.message_detail, name='message_detail'),
    path('messages/<int:pk>/mark-read/', views.message_mark_read, name='message_mark_read'),
    path('messages/<int:pk>/archive/', views.message_archive, name='message_archive'),
    path('messages/<int:pk>/delete/', views.message_delete, name='message_delete'),
] 