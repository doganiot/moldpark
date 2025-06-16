from django.urls import path
from . import views

app_name = 'producer'

urlpatterns = [
    # Üretici Kayıt ve Dashboard
    path('login/', views.producer_login, name='login'),
    path('register/', views.producer_register, name='register'),
    path('', views.producer_dashboard, name='dashboard'),
    path('profile/', views.producer_profile, name='profile'),
    
    # Sipariş Yönetimi
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/update/', views.order_update, name='order_update'),
    
    # Kalıp Yönetimi
    path('molds/', views.mold_list, name='mold_list'),
    path('molds/<int:pk>/', views.mold_detail, name='mold_detail'),
    path('molds/<int:pk>/download/', views.mold_download, name='mold_download'),
    path('molds/<int:pk>/download/<int:file_id>/', views.mold_download, name='mold_download_file'),
    path('molds/<int:pk>/upload-result/', views.mold_upload_result, name='mold_upload_result'),
    
    # Mesaj Sistemi
    path('messages/', views.message_list, name='message_list'),
    path('messages/<int:pk>/', views.message_detail, name='message_detail'),
    path('messages/create/', views.message_create, name='message_create'),
    
    # Ağ Yönetimi
    path('network/', views.network_list, name='network_list'),
    path('network/invite/', views.network_invite, name='network_invite'),
    path('network/remove/<int:center_id>/', views.network_remove, name='network_remove'),
    
    # Admin URLs (Ana yönetim paneli için)
    path('admin/', views.admin_producer_list, name='admin_producer_list'),
    path('admin/<int:pk>/', views.admin_producer_detail, name='admin_producer_detail'),
    path('admin/<int:pk>/verify/', views.admin_producer_verify, name='admin_producer_verify'),
    path('admin/<int:pk>/update-limit/', views.admin_producer_update_limit, name='admin_producer_update_limit'),
    path('admin/molds/', views.admin_mold_list, name='admin_mold_list'),
    path('admin/molds/<int:pk>/download/', views.admin_mold_download, name='admin_mold_download'),
] 