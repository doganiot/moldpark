"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.views.static import serve
from accounts.views import center_login
import os

def admin_access_check(user):
    """Admin paneline sadece superuser erişimi kontrolü"""
    if not user.is_authenticated:
        return False
    
    # Üretici hesapları admin paneline erişemez
    if hasattr(user, 'producer'):
        return False
    
    # Sadece superuser'lar erişebilir
    return user.is_superuser

def custom_admin_view(request):
    """Custom admin wrapper with security check"""
    if not admin_access_check(request.user):
        messages.error(request, 'Admin paneline erişim yetkiniz yok.')
        if hasattr(request.user, 'producer'):
            return redirect('producer:dashboard')
        elif hasattr(request.user, 'center'):
            return redirect('center:dashboard')
        else:
            return redirect('core:home')
    
    # Superuser ise normal admin site'a yönlendir
    return redirect('/django-admin/')

def service_worker_view(request):
    """Service Worker dosyasını serve et"""
    try:
        sw_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR / 'static', 'sw.js')
        if not os.path.exists(sw_path):
            sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
        
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        response = HttpResponse(content, content_type='application/javascript')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    except FileNotFoundError:
        return HttpResponse('Service Worker not found', status=404)

# Admin site'ı güvenli hale getir
admin.site.site_header = "MoldPark Yönetim Paneli"
admin.site.site_title = "MoldPark Admin"
admin.site.index_title = "Sistem Yönetimi"

urlpatterns = [
    # SERVICE WORKER
    path('sw.js', service_worker_view, name='service_worker'),
    
    # GÜVENLİ ADMIN ERİŞİMİ
    path('admin/', custom_admin_view, name='admin_redirect'),
    path('django-admin/', admin.site.urls),  # Gerçek admin panel
    
    # API ve Sistem URL'leri
    # Custom login pages (allauth'dan önce tanımlanmalı)
    path('account/center-login/', center_login, name='account_center_login'),
    # path('accounts/', include('allauth.urls')),  # allauth URL'leri - temporarily disabled
    # Django-notifications-hq paketini spesifik path'e taşı
    path('django-notifications/', include('notifications.urls', namespace='notifications')),
    # Language switcher
    path('i18n/', include('django.conf.urls.i18n')),
]

# Internationalized URLs
urlpatterns += i18n_patterns(
    # path('account/', include('allauth.urls')),  # Temporarily disabled
    path('accounts/', include('accounts.urls')),  # accounts app URL'leri
    path('', include('core.urls')),
    path('center/', include('center.urls')),
    path('mold/', include('mold.urls')),
    path('producer/', include('producer.urls')),
    prefix_default_language=False,  # Don't prefix default language
)

# Static ve Media dosyaları
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Debug Toolbar (sadece development ortamında)
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
