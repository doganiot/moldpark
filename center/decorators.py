from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from .models import Center

def center_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            request.user.center
        except Center.DoesNotExist:
            messages.error(request, "Profiliniz eksik. Lütfen merkez bilgilerinizi tamamlayın.")
            return redirect('center:profile')
        return view_func(request, *args, **kwargs)
    return _wrapped_view 