from django.urls import path
from . import views
from .api import SystemStatusAPI, production_pipeline_api, alerts_api, health_check_api

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),
    path('terms/', views.TermsView.as_view(), name='terms'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('api/system-status/', SystemStatusAPI.as_view(), name='api_system_status'),
    path('api/production-pipeline/', production_pipeline_api, name='api_production_pipeline'),
    path('api/alerts/', alerts_api, name='api_alerts'),
    path('api/health-check/', health_check_api, name='api_health_check'),
] 