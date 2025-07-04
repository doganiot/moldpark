from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from .models import Center
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.urls import reverse

def center_required(view_func):
    """
    Decorator to ensure user has a center
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'center'):
            messages.error(request, 'Bu sayfaya erişmek için bir işitme merkezi hesabına sahip olmanız gerekiyor.')
            return redirect('account_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def subscription_required(view_func):
    """
    Decorator to ensure user has valid subscription for creating models
    """
    @wraps(view_func)
    @login_required
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