from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ContactMessage
from .forms import ContactForm
from django.views.generic import TemplateView
from django.contrib.auth.decorators import user_passes_test
from center.models import Center, CenterMessage
from mold.models import EarMold
from accounts.forms import CustomSignupForm

def home(request):
    if request.user.is_authenticated:
        # Kullanıcının üretici olup olmadığını kontrol et
        is_producer = False
        try:
            is_producer = hasattr(request.user, 'producer') and request.user.producer is not None
        except:
            is_producer = False
        
        return render(request, 'core/home.html', {'is_producer': is_producer})
    
    # Giriş yapmamış kullanıcılar için kayıt formu
    if request.method == 'POST':
        try:
            form = CustomSignupForm(request.POST)
            if form.is_valid():
                try:
                    user = form.save(request)
                    messages.success(request, 'Kaydınız başarıyla oluşturuldu! Giriş yapabilirsiniz.')
                    return redirect('account_login')
                except Exception as e:
                    messages.error(request, 'Kayıt sırasında bir hata oluştu. Lütfen tekrar deneyin.')
            else:
                messages.error(request, 'Lütfen formdaki hataları düzeltin.')
        except Exception as e:
            form = CustomSignupForm()
            messages.error(request, 'Form yüklenirken bir hata oluştu.')
    else:
        try:
            form = CustomSignupForm()
        except Exception as e:
            # Basit bir form oluştur
            form = None
            messages.error(request, 'Form yüklenirken bir hata oluştu. Lütfen kayıt sayfasını kullanın.')
    
    return render(request, 'core/home.html', {'signup_form': form})

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mesajınız başarıyla gönderildi.')
            return redirect('core:contact')
    else:
        form = ContactForm()
    
    return render(request, 'core/contact.html', {'form': form})

class TermsView(TemplateView):
    template_name = 'core/terms.html'

class PrivacyView(TemplateView):
    template_name = 'core/privacy.html'

@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    # Import Producer modeli burada yapalım
    try:
        from producer.models import Producer
        producers = Producer.objects.all()
    except ImportError:
        producers = []
    
    centers = Center.objects.all()
    molds = EarMold.objects.all()
    messages = CenterMessage.objects.order_by('-created_at')[:5]
    
    # MoldPark merkez yönetimi bilgisi
    moldpark_center = {
        'name': 'MoldPark Merkez Yönetimi',
        'is_active': True,
        'user': {'email': 'admin@moldpark.com'},
        'phone': 'Sistem Yönetimi',
        'address': 'Merkezi Kalıp Üretim Sistemi',
        'created_at': None,
        'is_moldpark': True
    }
    
    # İstatistikler
    stats = {
        'total_centers': centers.count() + 1,  # MoldPark dahil
        'active_centers': centers.filter(is_active=True).count() + 1,  # MoldPark aktif
        'total_producers': len(producers),
        'verified_producers': len([p for p in producers if hasattr(p, 'is_verified') and p.is_verified]),
        'total_molds': molds.count(),
        'pending_molds': molds.filter(status='pending').count(),
    }
    
    context = {
        'centers': centers,
        'moldpark_center': moldpark_center,
        'producers': producers,
        'molds': molds,
        'recent_messages': messages,
        'stats': stats,
    }
    return render(request, 'core/dashboard_admin.html', context)
