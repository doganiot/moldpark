from django.urls import path
from . import views

app_name = 'producer'

urlpatterns = [
    # Üretici Kayıt ve Dashboard
    path('login/', views.producer_login, name='login'),
    path('logout/', views.producer_logout, name='logout'),
    path('register/', views.producer_register, name='register'),
    path('', views.producer_dashboard, name='dashboard'),
    path('profile/', views.producer_profile, name='profile'),
    
    # Sipariş Yönetimi
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/update/', views.order_update, name='order_update'),
    
    # Güvenli Kalıp Yönetimi (Sipariş-based)
    path('molds/', views.mold_list, name='mold_list'),  # Artık producer_orders listesi
    path('molds/<int:pk>/', views.mold_detail, name='mold_detail'),  # pk = order.id
    path('molds/<int:pk>/download/', views.mold_download, name='mold_download'),  # pk = order.id
    path('molds/<int:pk>/download/<int:file_id>/', views.mold_download_file, name='mold_download_file'),  # pk = order.id
    path('molds/<int:pk>/upload-result/', views.mold_upload_result, name='mold_upload_result'),  # pk = order.id
    
    # Mesaj Sistemi
    path('messages/', views.message_list, name='message_list'),
    path('messages/<int:pk>/', views.message_detail, name='message_detail'),
    path('messages/create/', views.message_create, name='message_create'),
    
    # Ağ Yönetimi
    path('network/', views.network_list, name='network_list'),
    path('network/invite/', views.network_invite, name='network_invite'),
    path('network/remove/<int:center_id>/', views.network_remove, name='network_remove'),
    
    # Sabit Dosya İndirme Linkleri (Ana Tarama Dosyaları)
    path('files/scan/<int:mold_id>/', views.permanent_scan_download, name='permanent_scan_download'),
    path('files/model/<int:file_id>/', views.permanent_model_download, name='permanent_model_download'),
    
    # Admin URLs (Ana yönetim paneli için - sadece superuser erişimi)
    path('admin/producers/', views.admin_producer_list, name='admin_producer_list'),
    path('admin/producers/<int:pk>/', views.admin_producer_detail, name='admin_producer_detail'),
    path('admin/producers/<int:pk>/verify/', views.admin_producer_verify, name='admin_producer_verify'),
    path('admin/producers/<int:pk>/update-limit/', views.admin_producer_update_limit, name='admin_producer_update_limit'),
    path('admin/molds/', views.admin_mold_list, name='admin_mold_list'),
    path('admin/molds/<int:pk>/download/', views.admin_mold_download, name='admin_mold_download'),
] 