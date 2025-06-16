from django.urls import path
from . import views

app_name = 'center'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('messages/', views.message_list, name='message_list'),
    path('messages/create/', views.send_message, name='message_create'),
    path('messages/<int:pk>/', views.message_detail, name='message_detail'),
    path('messages/<int:pk>/archive/', views.message_archive, name='message_archive'),
    path('messages/<int:pk>/unarchive/', views.message_unarchive, name='message_unarchive'),
    path('messages/<int:pk>/delete/', views.message_delete, name='message_delete'),
    path('messages/<int:pk>/quick-reply/', views.message_quick_reply, name='message_quick_reply'),
    path('<int:pk>/', views.center_detail, name='center_detail'),
    path('<int:pk>/limit/', views.center_limit_update, name='center_limit_update'),
    
    # Admin URLs
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/centers/', views.admin_center_list, name='admin_center_list'),
    path('admin/centers/<int:pk>/', views.admin_center_detail, name='admin_center_detail'),
    path('admin/centers/<int:pk>/toggle-status/', views.admin_center_toggle_status, name='admin_center_toggle_status'),
    path('admin/centers/<int:pk>/update-limit/', views.admin_center_update_limit, name='admin_center_update_limit'),
    path('admin/centers/stats/', views.admin_center_stats, name='admin_center_stats'),
    path('admin/molds/', views.admin_mold_list, name='admin_mold_list'),
    path('admin/molds/<int:pk>/', views.admin_mold_detail, name='admin_mold_detail'),
    path('admin/molds/<int:pk>/update-status/', views.admin_mold_update_status, name='admin_mold_update_status'),
    path('admin/molds/<int:mold_id>/upload-model/', views.admin_upload_model, name='admin_upload_model'),
    path('admin/models/<int:model_id>/delete/', views.admin_delete_model, name='admin_delete_model'),
    path('admin/revisions/', views.admin_revision_list, name='admin_revision_list'),
    path('admin/messages/', views.admin_message_list, name='admin_message_list'),
    path('admin/messages/<int:message_id>/', views.admin_message_detail, name='admin_message_detail'),
    path('admin/messages/<int:message_id>/archive/', views.archive_message, name='archive_message'),
    path('admin/messages/<int:message_id>/unarchive/', views.unarchive_message, name='unarchive_message'),
    path('admin/messages/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    
    # User management
    path('change-avatar/', views.change_avatar, name='change_avatar'),
    path('delete-account/', views.delete_account, name='delete_account'),
    
    # Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
] 