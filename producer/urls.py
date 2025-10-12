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
    path('orders/create-physical/', views.create_physical_mold_order, name='create_physical_mold_order'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/update/', views.order_update, name='order_update'),

    # Güvenli Kalıp Yönetimi (Sipariş-based)
    path('molds/', views.mold_list, name='mold_list'),
    path('molds/<int:pk>/', views.mold_detail, name='mold_detail'),
    path('molds/<int:pk>/3d-comparison/', views.mold_3d_comparison, name='mold_3d_comparison'),
    path('molds/<int:pk>/download/', views.mold_download, name='mold_download'),
    path('molds/<int:pk>/upload-result/', views.mold_upload_result, name='mold_upload_result'),

    # Fiziksel Kalıp Süreci
    path('molds/<int:pk>/receive-shipment/', views.receive_physical_shipment, name='receive_physical_shipment'),
    path('molds/<int:pk>/start-production/', views.start_physical_production, name='start_physical_production'),
    path('molds/<int:pk>/complete-production/', views.complete_physical_production, name='complete_physical_production'),
    path('molds/<int:pk>/ship-to-center/', views.ship_to_center, name='ship_to_center'),
    path('molds/<int:pk>/mark-delivered/', views.mark_delivered, name='mark_delivered'),

    # Ağ Yönetimi
    path('network/', views.network_list, name='network_list'),
    path('network/remove/<int:center_id>/', views.network_remove, name='network_remove'),

    # Revizyon yönetimi
    path('revisions/', views.revision_requests, name='revision_requests'),
    path('revisions/<int:request_id>/', views.revision_request_detail, name='revision_request_detail'),
    path('revisions/<int:request_id>/respond/', views.revision_request_respond, name='revision_request_respond'),
    path('revisions/<int:request_id>/start-work/', views.revision_start_work, name='revision_start_work'),
    path('revisions/<int:request_id>/complete-work/', views.revision_complete_work, name='revision_complete_work'),

    # Ödeme ve Finansal Takip
    path('payments/', views.producer_payments, name='payments'),
    path('payments/<int:invoice_id>/', views.producer_payment_detail, name='payment_detail'),

    # Admin URLs
    path('admin/producers/', views.admin_producer_list, name='admin_producer_list'),
    path('admin/producers/<int:pk>/', views.admin_producer_detail, name='admin_producer_detail'),
    path('admin/producers/<int:pk>/verify/', views.admin_producer_verify, name='admin_producer_verify'),
    path('admin/producers/<int:pk>/update-limit/', views.admin_producer_update_limit, name='admin_producer_update_limit'),
    path('admin/molds/', views.admin_mold_list, name='admin_mold_list'),
    path('admin/molds/<int:pk>/download/', views.admin_mold_download, name='admin_mold_download'),
] 