from django.urls import path
from . import views
from .api import SystemStatusAPI, production_pipeline_api, alerts_api, health_check_api
from . import api

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('help/', views.help_center, name='help_center'),
    path('contact/', views.contact, name='contact'),
    path('terms/', views.terms_of_service, name='terms'),
    path('privacy/', views.privacy_policy, name='privacy'),
    path('pricing/', views.pricing, name='pricing'),
    path('features/', views.features, name='features'),
    path('subscribe/<int:plan_id>/', views.subscribe_to_plan, name='subscribe_to_plan'),
    path('subscription/', views.subscription_dashboard, name='subscription_dashboard'),
    
    # Abonelik Talep Sistemi
    path('subscription/request/', views.request_subscription, name='request_subscription'),
    path('subscription/requests/', views.subscription_requests, name='subscription_requests'),
    path('subscription/requests/<int:request_id>/cancel/', views.subscription_request_cancel, name='subscription_request_cancel'),
    
    # Admin Dashboard - Multiple URL aliases for better UX
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard_alt'),
    
    # Admin Abonelik Yönetimi
    path('admin/subscription-requests/<int:request_id>/approve/', views.admin_approve_subscription_request, name='admin_approve_subscription_request'),
    path('admin/subscription-requests/<int:request_id>/reject/', views.admin_reject_subscription_request, name='admin_reject_subscription_request'),
    
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

    # Yeni API Endpoints
    path('api/system-health/', api.system_health_api, name='system_health_api'),
    path('api/run-health-check/', api.run_health_check_api, name='run_health_check_api'),
    path('api/smart-notifications-status/', api.smart_notifications_status_api, name='smart_notifications_status_api'),
    path('api/trigger-smart-notifications/', api.trigger_smart_notifications_api, name='trigger_smart_notifications_api'),
    path('api/performance-insights/', api.performance_insights_api, name='performance_insights_api'),
    
    # Basit Bildirim Sistemi
    path('notifications/', views.simple_notifications, name='simple_notifications'),
    path('notifications/<int:notification_id>/', views.notification_redirect, name='notification_redirect'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_as_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    path('documentation/', views.documentation, name='documentation'),
] 