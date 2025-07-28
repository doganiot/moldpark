from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def smart_redirect(request):
    """Kullanıcı tipine göre doğru dashboard'a yönlendir"""
    if request.user.is_superuser or request.user.is_staff:
        return redirect('center:admin_dashboard')
    elif hasattr(request.user, 'producer') and request.user.producer:
        return redirect('producer:dashboard')
    elif hasattr(request.user, 'center') and request.user.center:
        return redirect('center:dashboard')
    else:
        # Hiçbiri değilse ana sayfaya yönlendir
        return redirect('core:home')

@login_required 
def smart_home_redirect(request):
    """Logo tıklamasında kullanıcıyı kendi dashboard'una yönlendir"""
    if request.user.is_superuser or request.user.is_staff:
        return redirect('center:admin_dashboard')
    elif hasattr(request.user, 'producer') and request.user.producer:
        return redirect('producer:dashboard')
    elif hasattr(request.user, 'center') and request.user.center:
        return redirect('center:dashboard')
    else:
        return redirect('core:home') 