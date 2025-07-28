from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('smart-redirect/', views.smart_redirect, name='smart_redirect'),
    path('smart-home/', views.smart_home_redirect, name='smart_home_redirect'),
] 