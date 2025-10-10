from django.urls import path
from . import views

app_name = 'center'

urlpatterns = [
    # Center Dashboard
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('change-avatar/', views.change_avatar, name='change_avatar'),
    path('delete-account/', views.delete_account, name='delete_account'),
    
    # Network Management
    path('network/', views.network_management, name='network_management'),

    # Usage Details
    path('usage/', views.billing_invoices, name='usage_details'),
    path('usage/<int:invoice_id>/', views.billing_invoice_detail, name='usage_invoice_detail'),

    # Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    
    # Admin URLs
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/centers/', views.admin_center_list, name='admin_center_list'),
    path('admin/centers/<int:center_id>/', views.admin_center_detail, name='admin_center_detail'),
    path('admin/centers/<int:center_id>/toggle-status/', views.admin_center_toggle_status, name='admin_center_toggle_status'),
    path('admin/centers/<int:center_id>/edit-user/', views.admin_center_edit_user, name='admin_center_edit_user'),
    path('admin/centers/<int:center_id>/change-producer/', views.admin_center_change_producer, name='admin_center_change_producer'),
    path('admin/centers/<int:center_id>/delete/', views.admin_center_delete, name='admin_center_delete'),
    
    # Mold Admin
    path('admin/molds/', views.admin_mold_list, name='admin_mold_list'),
    path('admin/molds/<int:pk>/', views.admin_mold_detail, name='admin_mold_detail'),
    path('admin/molds/<int:pk>/update-status/', views.admin_mold_update_status, name='admin_mold_update_status'),
    path('admin/molds/<int:mold_id>/upload-model/', views.admin_upload_model, name='admin_upload_model'),
    path('admin/models/<int:model_id>/delete/', views.admin_delete_model, name='admin_delete_model'),

    # Mold Detail
    path('molds/<int:pk>/', views.mold_detail, name='mold_detail'),

    # Delivery Approval
    path('molds/<int:mold_id>/approve-delivery/', views.approve_delivery, name='approve_delivery'),
    
    # Admin revizyon yönetimi
    path('admin/revisions/', views.admin_revision_list, name='admin_revision_list'),
    
    # API endpoints
    path('api/producers/', views.get_producers_api, name='get_producers_api'),
] 