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
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages

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

# Admin site'ı güvenli hale getir
admin.site.site_header = "MoldPark Yönetim Paneli"
admin.site.site_title = "MoldPark Admin"
admin.site.index_title = "Sistem Yönetimi"

urlpatterns = [
    # GÜVENLİ ADMIN ERİŞİMİ
    path('admin/', custom_admin_view, name='admin_redirect'),
    path('django-admin/', admin.site.urls),  # Gerçek admin panel
    
    # Diğer URL'ler
    path('accounts/', include('allauth.urls')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('', include('core.urls')),
    path('center/', include('center.urls')),
    path('mold/', include('mold.urls')),
    path('producer/', include('producer.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
