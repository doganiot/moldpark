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
        from producer.models import Producer, ProducerOrder
        producers = Producer.objects.all()
        
        # MoldPark üretim merkezini bul
        moldpark_producer = Producer.objects.filter(
            company_name='MoldPark Üretim Merkezi'
        ).first()
        
        # DEBUG: Print etmek için
        print(f"DEBUG - MoldPark Producer: {moldpark_producer}")
        print(f"DEBUG - Producer count: {producers.count()}")
        if moldpark_producer:
            print(f"DEBUG - MoldPark Company: {moldpark_producer.company_name}")
        
        # MoldPark siparişlerini al
        moldpark_orders = []
        if moldpark_producer:
            moldpark_orders = ProducerOrder.objects.filter(
                producer=moldpark_producer
            ).select_related('center', 'ear_mold').order_by('-created_at')[:10]
            
    except ImportError as e:
        print(f"DEBUG - Import Error: {e}")
        producers = []
        moldpark_producer = None
        moldpark_orders = []
    except Exception as e:
        print(f"DEBUG - Other Error: {e}")
        producers = []
        moldpark_producer = None
        moldpark_orders = []
    
    centers = Center.objects.all()
    molds = EarMold.objects.all()
    messages = CenterMessage.objects.order_by('-created_at')[:5]
    
    # Kullanıcı bilgileri için center ve producer verilerini hazırla
    center_users = []
    for center in centers:
        center_users.append({
            'type': 'center',
            'name': center.name,
            'company': center.name,
            'username': center.user.username,
            'email': center.user.email,
            'password_display': '••••••••',  # Güvenlik için maskelenmiş
            'is_active': center.is_active,
            'created_at': center.created_at,
            'user_id': center.user.id,
            'profile_id': center.id
        })
    
    producer_users = []
    for producer in producers:
        producer_users.append({
            'type': 'producer',
            'name': producer.company_name,
            'company': producer.company_name,
            'username': producer.user.username,
            'email': producer.user.email,
            'password_display': '••••••••',  # Güvenlik için maskelenmiş
            'is_active': producer.is_active,
            'created_at': producer.created_at,
            'user_id': producer.user.id,
            'profile_id': producer.id
        })
    
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
        'moldpark_orders': len(moldpark_orders),
        'moldpark_active_orders': len([o for o in moldpark_orders if o.status in ['received', 'designing', 'production', 'quality_check']]),
        'total_users': len(center_users) + len(producer_users),
    }
    
    context = {
        'centers': centers,
        'moldpark_center': moldpark_center,
        'producers': producers,
        'moldpark_producer': moldpark_producer,
        'moldpark_orders': moldpark_orders,
        'molds': molds,
        'recent_messages': messages,
        'center_users': center_users,
        'producer_users': producer_users,
        'stats': stats,
    }
    return render(request, 'core/dashboard_admin.html', context)
