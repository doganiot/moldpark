from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from .models import Center
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.urls import reverse

def center_required(view_func):
    """
    Decorator to ensure user has a center and active subscription
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Giriş yapılmış mı kontrol et
        if not request.user.is_authenticated:
            messages.error(request, 'Bu sayfaya erişmek için giriş yapmanız gerekiyor.')
            return redirect('account_login')
        
        # Center hesabı var mı kontrol et
        if not hasattr(request.user, 'center'):
            messages.error(request, 'Bu sayfaya erişmek için bir işitme merkezi hesabına sahip olmanız gerekiyor.')
            return redirect('account_login')
        
        # Abonelik kontrolü (sadece dashboard ve subscription sayfaları hariç)
        from core.models import UserSubscription
        from django.urls import resolve
        
        # Abonelik kontrolünden muaf sayfalar
        exempt_views = ['dashboard', 'subscription_request', 'profile', 'change_avatar']
        current_view = resolve(request.path_info).url_name
        
        if current_view not in exempt_views:
            try:
                subscription = UserSubscription.objects.get(user=request.user)
                if subscription.status != 'active':
                    messages.warning(request, '⚠️ Aboneliğiniz aktif değil. Lütfen abonelik durumunuzu kontrol edin.')
                    return redirect('center:dashboard')
            except UserSubscription.DoesNotExist:
                messages.warning(request, '⚠️ Henüz aboneliğiniz bulunmuyor. Lütfen admin onayı bekleyin.')
                return redirect('center:dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    """
    Admin paneline erişim izni kontrolü - staff veya superuser olması gerekir
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Bu sayfaya erişmek için giriş yapmanız gerekiyor.')
            return redirect('account_login')
        
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, 'Bu sayfaya erişim izniniz yok.')
            if hasattr(request.user, 'center'):
                return redirect('center:dashboard')
            elif hasattr(request.user, 'producer'):
                return redirect('producer:dashboard')
            else:
                return redirect('account_login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def subscription_required(view_func):
    """
    Decorator to ensure user has valid subscription for creating models
    """
    @wraps(view_func)
    @center_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            # Abonelik varlığını kontrol et
            if not hasattr(request.user, 'subscription'):
                messages.error(request, 
                    'Kalıp oluşturmak için aktif bir aboneliğe ihtiyacınız var. '
                    'Lütfen önce bir abonelik planı seçin.')
                return redirect('core:subscription_dashboard')
            
            subscription = request.user.subscription
            
            # Abonelik geçerliliğini kontrol et
            if not subscription.is_valid():
                messages.error(request, 
                    'Aboneliğiniz geçerli değil. Kalıp oluşturmak için aktif bir aboneliğe ihtiyacınız var.')
                return redirect('core:subscription_dashboard')
            
            # Kalıp oluşturma hakkını kontrol et
            if not subscription.can_create_model():
                remaining = subscription.get_remaining_models()
                if remaining == 0:
                    if subscription.plan.plan_type == 'trial':
                        messages.error(request, 
                            '🎯 Deneme paketiniz tükendi! '
                            'Kalıp oluşturmaya devam etmek için bir abonelik planı seçin.')
                    else:
                        messages.error(request, 
                            '📊 Bu ay için kalıp limitiniz doldu. '
                            'Daha fazla kalıp oluşturmak için planınızı yükseltin.')
                    return redirect('core:subscription_dashboard')
                elif remaining <= 2 and subscription.plan.plan_type == 'trial':
                    # Deneme paketi az kaldığında uyarı ver ama devam ettir
                    messages.warning(request, 
                        f'⚠️ Deneme paketinizde sadece {remaining} kalıp hakkınız kaldı. '
                        f'Planları incelemeyi unutmayın!')
            
        except Exception as e:
            messages.error(request, 
                'Abonelik bilgilerinize erişilemiyor. '
                'Lütfen sayfayı yenileyin veya destek ile iletişime geçin.')
            return redirect('core:subscription_dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view 