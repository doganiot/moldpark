from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from allauth.account.views import LoginView
from django.contrib.auth import authenticate, login
from django.contrib import messages

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

def center_login(request):
    """İşitme Merkezi girişi için özel view"""
    if request.method == 'POST':
        email = request.POST.get('login')
        password = request.POST.get('password')
        
        # Email ile kullanıcıyı bul
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Birden fazla kullanıcı olabilir, ilkini al
        user = User.objects.filter(email=email).first()
        
        if user:
            # Şifre kontrolü
            authenticated_user = authenticate(request, username=user.username, password=password)
            
            if authenticated_user is not None:
                # Kullanıcı üretici mi kontrol et
                if hasattr(authenticated_user, 'producer') and authenticated_user.producer:
                    messages.error(request, 'Üretici hesapları bu sayfadan giriş yapamaz. Lütfen üretici giriş sayfasını kullanın.')
                    return redirect('producer:login')
                
                # Giriş yap
                login(request, authenticated_user)
                return redirect('accounts:smart_redirect')
            else:
                messages.error(request, 'E-posta adresi veya şifre hatalı.')
        else:
            messages.error(request, 'E-posta adresi veya şifre hatalı.')
    
    # Allauth login formunu kullan
    from allauth.account.forms import LoginForm
    form = LoginForm()
    
    return render(request, 'account/center_login.html', {'form': form}) 