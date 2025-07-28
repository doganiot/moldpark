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
    path('molds/<int:pk>/3d-comparison/', views.mold_3d_comparison, name='mold_3d_comparison'),
    path('molds/<int:pk>/download/', views.mold_download, name='mold_download'),  # pk = order.id

    path('molds/<int:pk>/upload-result/', views.mold_upload_result, name='mold_upload_result'),  # pk = order.id
    
    # Mesaj Sistemi - Kaldırıldı (Sadece Admin Dashboard üzerinden)
    
    # Ağ Yönetimi
    path('network/', views.network_list, name='network_list'),
    # Network invite kaldırıldı - Sadece admin ağ yönetimi
    path('network/remove/<int:center_id>/', views.network_remove, name='network_remove'),
    
    # Revizyon yönetimi
    path('revisions/', views.revision_requests, name='revision_requests'),
    path('revisions/<int:request_id>/', views.revision_request_detail, name='revision_request_detail'),
    path('revisions/<int:request_id>/respond/', views.revision_request_respond, name='revision_request_respond'),
    path('revisions/<int:request_id>/start-work/', views.revision_start_work, name='revision_start_work'),
    path('revisions/<int:request_id>/complete-work/', views.revision_complete_work, name='revision_complete_work'),
    
    # Sabit Dosya İndirme Linkleri - Kaldırıldı (Şimdilik mold_download kullanılıyor)
    
    # Admin URLs (Ana yönetim paneli için - sadece superuser erişimi)
    path('admin/producers/', views.admin_producer_list, name='admin_producer_list'),
    path('admin/producers/<int:pk>/', views.admin_producer_detail, name='admin_producer_detail'),
    path('admin/producers/<int:pk>/verify/', views.admin_producer_verify, name='admin_producer_verify'),
    path('admin/producers/<int:pk>/update-limit/', views.admin_producer_update_limit, name='admin_producer_update_limit'),
    path('admin/molds/', views.admin_mold_list, name='admin_mold_list'),
    path('admin/molds/<int:pk>/download/', views.admin_mold_download, name='admin_mold_download'),
] 