from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),
    path('terms/', views.TermsView.as_view(), name='terms'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
] 