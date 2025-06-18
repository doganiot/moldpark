from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, Http404
from notifications.signals import notify
from center.models import Center
from mold.models import EarMold, ModeledMold
from .models import Producer, ProducerOrder, ProducerMessage, ProducerNetwork, ProducerProductionLog
from .forms import (
    ProducerRegistrationForm, ProducerProfileForm, ProducerOrderForm, 
    ProducerOrderUpdateForm, ProducerMessageForm, ProductionLogForm, NetworkInviteForm
)
import mimetypes
import os

# ÜRETİCİ AUTHENTICATION - Ayrı sistem
def producer_required(view_func):
    """Decorator: Sadece doğrulanmış üretici merkezlerin erişimi"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Bu sayfaya erişmek için giriş yapmalısınız.')
            return redirect('producer:login')
        
        try:
            producer = request.user.producer
            if not producer.is_active or not producer.is_verified:
                messages.error(request, 'Üretici hesabınız aktif değil veya doğrulanmamış.')
                logout(request)
                return redirect('producer:login')
            return view_func(request, *args, **kwargs)
        except Producer.DoesNotExist:
            messages.error(request, 'Bu sayfaya erişmek için üretici hesabınız olmalıdır.')
            logout(request)
            return redirect('producer:login')
    return wrapper


def producer_login(request):
    """Üretici Girişi - Ayrı Authentication Sistemi"""
    if request.user.is_authenticated:
        # Eğer zaten giriş yapmışsa ve üretici ise dashboard'a yönlendir
        try:
            producer = request.user.producer
            if producer.is_active and producer.is_verified:
                return redirect('producer:dashboard')
            else:
                logout(request)
                messages.error(request, 'Üretici hesabınız aktif değil.')
        except Producer.DoesNotExist:
            # Normal kullanıcı ise çıkış yap
            logout(request)
            messages.info(request, 'Üretici girişi için lütfen üretici bilgilerinizle giriş yapın.')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if email and password:
            try:
                # Email ile kullanıcı bul
                user = User.objects.get(email=email)
                
                # ÖNEMLİ GÜVENLİK KONTROLÜ: Admin kullanıcıları engelle
                if user.is_superuser or user.is_staff:
                    messages.error(request, 'Admin hesapları bu panelden giriş yapamaz.')
                    return render(request, 'producer/login.html')
                
                # Şifre kontrolü
                user = authenticate(request, username=user.username, password=password)
                if user:
                    # Üretici kontrolü
                    try:
                        producer = user.producer
                        if producer.is_active and producer.is_verified:
                            login(request, user)
                            messages.success(request, f'Hoş geldiniz, {producer.company_name}!')
                            return redirect('producer:dashboard')
                        else:
                            messages.error(request, 'Üretici hesabınız aktif değil veya doğrulanmamış. Lütfen yönetici ile iletişime geçin.')
                    except Producer.DoesNotExist:
                        messages.error(request, 'Bu e-posta adresi ile kayıtlı üretici hesabı bulunamadı.')
                else:
                    messages.error(request, 'E-posta veya şifre hatalı.')
            except User.DoesNotExist:
                messages.error(request, 'Bu e-posta adresi ile kayıtlı kullanıcı bulunamadı.')
        else:
            messages.error(request, 'E-posta ve şifre alanları zorunludur.')
    
    return render(request, 'producer/login.html')


def producer_logout(request):
    """Üretici Çıkış"""
    logout(request)
    messages.success(request, 'Başarıyla çıkış yaptınız.')
    return redirect('producer:login')


def producer_register(request):
    """Üretici Merkez Kayıt Sayfası"""
    if request.method == 'POST':
        form = ProducerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            # Kullanıcı oluştur - Admin yetkisi verme!
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                is_staff=False,  # Kesinlikle admin yetkisi verme
                is_superuser=False  # Kesinlikle superuser yapma
            )
            
            # Producer profili oluştur
            producer = form.save(commit=False)
            producer.user = user
            producer.is_verified = False  # Admin onayı beklesin
            producer.save()
            
            # Admin'e bildirim gönder
            admin_users = User.objects.filter(is_superuser=True)
            for admin in admin_users:
                notify.send(
                    sender=user,
                    recipient=admin,
                    verb='yeni üretici merkez kaydı',
                    action_object=producer,
                    description=f'{producer.company_name} adlı üretici merkez onay bekliyor.'
                )
            
            messages.success(request, 
                'Üretici merkez kaydınız başarıyla oluşturuldu! '
                'Hesabınız admin onayından sonra aktif olacaktır.'
            )
            return redirect('producer:login')
    else:
        form = ProducerRegistrationForm()
    
    return render(request, 'producer/register.html', {'form': form})


@producer_required
def producer_dashboard(request):
    """Üretici Ana Sayfa - Güvenli Erişim"""
    producer = request.user.producer
    
    # Sadece kendi verilerine erişim
    total_orders = producer.orders.count()
    active_orders = producer.orders.exclude(status__in=['delivered', 'cancelled']).count()
    completed_orders = producer.orders.filter(status='delivered').count()
    network_centers_count = producer.network_centers.filter(status='active').count()
    
    # Ağ merkezleri - sadece kendi ağı
    network_centers = producer.network_centers.filter(status='active').select_related('center')
    
    # Son siparişler - sadece kendi siparişleri
    recent_orders = producer.orders.all()[:5]
    
    # Son mesajlar - sadece kendisine gelen
    recent_messages = producer.messages.filter(
        sender_is_producer=False, is_read=False
    )[:5]
    
    # Bu ayki sipariş sayısı ve limit kontrolü
    monthly_orders = producer.get_current_month_orders()
    remaining_limit = producer.get_remaining_limit()
    
    # Yüzde hesaplama
    if producer.mold_limit > 0:
        usage_percentage = round((monthly_orders * 100) / producer.mold_limit, 1)
    else:
        usage_percentage = 0
    
    context = {
        'producer': producer,
        'total_orders': total_orders,
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'network_centers': network_centers_count,
        'network_centers_list': network_centers,
        'recent_orders': recent_orders,
        'recent_messages': recent_messages,
        'monthly_orders': monthly_orders,
        'remaining_limit': remaining_limit,
        'usage_percentage': usage_percentage,
    }
    
    return render(request, 'producer/dashboard.html', context)


@producer_required
def producer_profile(request):
    """Üretici Profil Sayfası"""
    producer = request.user.producer
    
    if request.method == 'POST':
        form = ProducerProfileForm(request.POST, request.FILES, instance=producer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profiliniz başarıyla güncellendi.')
            return redirect('producer:profile')
    else:
        form = ProducerProfileForm(instance=producer)
    
    return render(request, 'producer/profile.html', {'form': form, 'producer': producer})


@producer_required
def order_list(request):
    """Sipariş Listesi - Sadece Kendi Siparişleri"""
    producer = request.user.producer
    orders = producer.orders.all()
    
    # Filtreleme
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    center_filter = request.GET.get('center')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    if priority_filter:
        orders = orders.filter(priority=priority_filter)
    if center_filter:
        # Sadece kendi ağındaki merkezleri kontrol et
        if producer.network_centers.filter(center_id=center_filter, status='active').exists():
            orders = orders.filter(center_id=center_filter)
    
    # Arama
    search = request.GET.get('search')
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(ear_mold__patient_name__icontains=search) |
            Q(ear_mold__patient_surname__icontains=search) |
            Q(center__name__icontains=search)
        )
    
    # Sadece kendi ağındaki merkezler
    network_centers = producer.network_centers.filter(status='active')
    
    context = {
        'orders': orders,
        'network_centers': network_centers,
    }
    
    return render(request, 'producer/order_list.html', context)


@producer_required
def order_detail(request, pk):
    """Sipariş Detayı - Güvenlik Kontrolü"""
    producer = request.user.producer
    
    # Sadece kendi siparişlerine erişim
    order = get_object_or_404(ProducerOrder, pk=pk, producer=producer)
    
    # Üretim logları
    production_logs = order.production_logs.all().order_by('-created_at')
    
    context = {
        'order': order,
        'production_logs': production_logs,
    }
    
    return render(request, 'producer/order_detail.html', context)


@producer_required
def order_update(request, pk):
    """Sipariş Güncelleme"""
    producer = request.user.producer
    
    order = get_object_or_404(ProducerOrder, pk=pk, producer=producer)
    
    if request.method == 'POST':
        form = ProducerOrderUpdateForm(request.POST, instance=order)
        if form.is_valid():
            old_status = order.status
            order = form.save()
            
            # Durum değişikliği bildirimi
            if old_status != order.status:
                notify.send(
                    sender=request.user,
                    recipient=order.center.user,
                    verb='sipariş durumu güncellendi',
                    action_object=order,
                    description=f'{order.order_number} siparişi {order.get_status_display()} durumuna geçti'
                )
            
            messages.success(request, 'Sipariş başarıyla güncellendi.')
            return redirect('producer:order_detail', pk=pk)
    else:
        form = ProducerOrderUpdateForm(instance=order)
    
    return render(request, 'producer/order_update.html', {'form': form, 'order': order})


@producer_required
def message_list(request):
    """Mesaj Listesi"""
    messages_queryset = request.user.producer.messages.all()
    
    # Filtreleme
    message_type = request.GET.get('type')
    is_read = request.GET.get('read')
    center_filter = request.GET.get('center')
    
    if message_type:
        messages_queryset = messages_queryset.filter(message_type=message_type)
    if is_read == 'true':
        messages_queryset = messages_queryset.filter(is_read=True)
    elif is_read == 'false':
        messages_queryset = messages_queryset.filter(is_read=False)
    if center_filter:
        messages_queryset = messages_queryset.filter(center_id=center_filter)
    
    # Arama
    search = request.GET.get('search')
    if search:
        messages_queryset = messages_queryset.filter(
            Q(subject__icontains=search) |
            Q(message__icontains=search) |
            Q(center__name__icontains=search)
        )
    
    network_centers = request.user.producer.network_centers.filter(status='active')
    
    context = {
        'messages': messages_queryset,
        'network_centers': network_centers,
        'message_types': ProducerMessage.MESSAGE_TYPE_CHOICES,
        'current_filters': {
            'type': message_type,
            'read': is_read,
            'center': center_filter,
            'search': search,
        }
    }
    
    return render(request, 'producer/message_list.html', context)


@producer_required
def message_detail(request, pk):
    """Mesaj Detay"""
    message = get_object_or_404(ProducerMessage, pk=pk, producer=request.user.producer)
    
    # Mesajı okundu olarak işaretle
    if not message.is_read:
        message.is_read = True
        message.read_at = timezone.now()
        message.save()
    
    return render(request, 'producer/message_detail.html', {'message': message})


@producer_required
def message_create(request):
    """Yeni Mesaj Oluşturma"""
    if request.method == 'POST':
        form = ProducerMessageForm(request.POST, request.FILES, producer=request.user.producer)
        if form.is_valid():
            message = form.save(commit=False)
            message.producer = request.user.producer
            message.sender_is_producer = True
            message.save()
            
            # Merkeze bildirim gönder
            notify.send(
                sender=request.user,
                recipient=message.center.user,
                verb='yeni mesaj gönderdi',
                action_object=message,
                description=f'{message.subject}'
            )
            
            messages.success(request, 'Mesajınız başarıyla gönderildi.')
            return redirect('producer:message_list')
    else:
        form = ProducerMessageForm(producer=request.user.producer)
    
    return render(request, 'producer/message_create.html', {'form': form})


@producer_required
def network_list(request):
    """Ağ Merkez Listesi"""
    networks = request.user.producer.network_centers.all()
    
    # Filtreleme
    status_filter = request.GET.get('status')
    if status_filter:
        networks = networks.filter(status=status_filter)
    
    context = {
        'networks': networks,
        'status_choices': ProducerNetwork.STATUS_CHOICES,
        'current_status': status_filter,
    }
    
    return render(request, 'producer/network_list.html', context)


@producer_required
def network_invite(request):
    """Ağ Daveti Gönder"""
    if request.method == 'POST':
        form = NetworkInviteForm(request.POST)
        if form.is_valid():
            center_email = form.cleaned_data['center_email']
            try:
                center_user = User.objects.get(email=center_email)
                center = Center.objects.get(user=center_user)
                
                # Zaten ağda mı kontrol et
                if ProducerNetwork.objects.filter(
                    producer=request.user.producer, center=center, status='active'
                ).exists():
                    messages.warning(request, 'Bu merkez zaten ağınızda bulunuyor.')
                    return redirect('producer:network_list')
                
                # Davet oluştur veya güncelle
                invite, created = ProducerNetwork.objects.get_or_create(
                    producer=request.user.producer,
                    center=center,
                    defaults={'status': 'pending'}
                )
                
                if not created and invite.status == 'pending':
                    messages.info(request, 'Bu merkeze zaten davet gönderilmiş.')
                else:
                    invite.status = 'pending'
                    invite.save()
                    
                    # Merkeze bildirim gönder
                    notify.send(
                        sender=request.user,
                        recipient=center.user,
                        verb='ağ daveti',
                        action_object=request.user.producer,
                        description=f'{request.user.producer.company_name} sizi ağına davet etti'
                    )
                    
                    messages.success(request, f'{center.name} merkezine davet gönderildi.')
                
                return redirect('producer:network_list')
                
            except (User.DoesNotExist, Center.DoesNotExist):
                messages.error(request, 'Bu e-posta adresine sahip aktif bir merkez bulunamadı.')
    else:
        form = NetworkInviteForm()
    
    return render(request, 'producer/network_invite.html', {'form': form})


@producer_required
def network_remove(request, center_id):
    """Merkezi Ağdan Çıkar"""
    if request.method == 'POST':
        try:
            network = ProducerNetwork.objects.get(
                producer=request.user.producer, 
                center_id=center_id,
                status='active'
            )
            
            # Ağdan çıkar
            network.status = 'inactive'
            network.save()
            
            # Merkeze bildirim gönder
            notify.send(
                sender=request.user,
                recipient=network.center.user,
                verb='ağdan çıkarıldı',
                action_object=request.user.producer,
                description=f'{request.user.producer.company_name} sizi ağından çıkardı'
            )
            
            return JsonResponse({'success': True, 'message': 'Merkez başarıyla ağdan çıkarıldı.'})
            
        except ProducerNetwork.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Merkez ağınızda bulunamadı.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Bir hata oluştu.'})
    
    return JsonResponse({'success': False, 'message': 'Geçersiz istek.'})


@producer_required
def mold_list(request):
    """Güvenli Üretici Kalıp Listesi - Sadece Bu Üreticiye Gönderilen Kalıplar"""
    producer = request.user.producer
    
    # ÖNEMLİ GÜVENLİK: Sadece bu üreticiye gönderilen siparişlerin kalıplarını al
    # Veri tabanına direkt erişim YOK!
    producer_orders = producer.orders.select_related('ear_mold', 'center').all()
    
    # Filtreleme - sadece sipariş üzerinden
    status_filter = request.GET.get('status')
    order_status_filter = request.GET.get('order_status')
    center_filter = request.GET.get('center')
    
    if status_filter:
        # EarMold status filtresi
        producer_orders = producer_orders.filter(ear_mold__status=status_filter)
    if order_status_filter:
        # ProducerOrder status filtresi
        producer_orders = producer_orders.filter(status=order_status_filter)
    if center_filter:
        # Sadece kendi ağındaki merkezleri kontrol et
        if producer.network_centers.filter(center_id=center_filter, status='active').exists():
            producer_orders = producer_orders.filter(center_id=center_filter)
    
    # Arama - güvenli arama
    search = request.GET.get('search')
    if search:
        producer_orders = producer_orders.filter(
            Q(ear_mold__patient_name__icontains=search) |
            Q(ear_mold__patient_surname__icontains=search) |
            Q(center__name__icontains=search) |
            Q(order_number__icontains=search)
        )
    
    # Sıralama
    producer_orders = producer_orders.order_by('-created_at')
    
    # İstatistikler - güvenli hesaplama
    total_orders = producer_orders.count()
    received_orders = producer_orders.filter(status='received').count()
    production_orders = producer_orders.filter(status__in=['designing', 'production', 'quality_check']).count()
    completed_orders = producer_orders.filter(status='delivered').count()
    pending_orders = producer_orders.filter(status__in=['received', 'designing']).count()
    
    # Ağ merkezleri - sadece kendi ağı
    network_centers = producer.network_centers.filter(status='active').select_related('center')
    
    # Bu ayki sipariş limiti kontrolü
    monthly_orders = producer.get_current_month_orders()
    remaining_limit = producer.get_remaining_limit()
    
    # Kalıp türü seçenekleri - mold modelinden al
    from mold.models import EarMold
    mold_status_choices = EarMold.STATUS_CHOICES
    
    context = {
        'producer': producer,
        'producer_orders': producer_orders,  # Kalıplar değil, siparişler
        'network_centers': network_centers,
        'order_status_choices': ProducerOrder.STATUS_CHOICES,
        'mold_status_choices': mold_status_choices,
        'current_filters': {
            'status': status_filter,
            'order_status': order_status_filter,
            'center': center_filter,
            'search': search,
        },
        # İstatistikler
        'total_orders': total_orders,
        'received_orders': received_orders,
        'production_orders': production_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        # Limit bilgileri
        'monthly_orders': monthly_orders,
        'remaining_limit': remaining_limit,
        'usage_percentage': round((monthly_orders * 100) / producer.mold_limit, 1) if producer.mold_limit > 0 else 0,
    }
    
    return render(request, 'producer/mold_list.html', context)


@producer_required
def mold_detail(request, pk):
    """Güvenli Kalıp Detayı - Sadece Kendi Siparişlerine Erişim"""
    producer = request.user.producer
    
    # ÖNEMLİ GÜVENLİK: Önce bu üreticiye ait sipariş olup olmadığını kontrol et
    try:
        producer_order = ProducerOrder.objects.select_related('ear_mold', 'center').get(
            pk=pk,  # Sipariş ID'si ile erişim
            producer=producer  # Sadece kendi siparişleri
        )
        ear_mold = producer_order.ear_mold
    except ProducerOrder.DoesNotExist:
        # Eğer bu üreticiye ait değilse hata ver
        messages.error(request, 'Bu kalıba erişim yetkiniz bulunmamaktadır.')
        return redirect('producer:order_list')
    
    # Ağ kontrolü - bu merkez üreticinin ağında mı? (Esnek kontrol)
    network_relation = producer.network_centers.filter(center=ear_mold.center).first()
    if not network_relation:
        messages.error(request, 'Bu merkez sizin ağınızda bulunmamaktadır.')
        return redirect('producer:order_list')
    
    # Network durumu kontrolü ve uyarı sistemi
    network_warning = None
    if network_relation.status == 'suspended':
        network_warning = 'Bu merkez ile ağ bağlantınız askıya alınmış durumda.'
        messages.warning(request, network_warning)
    elif network_relation.status == 'terminated':
        messages.error(request, 'Bu merkez ile ağ bağlantınız sonlandırılmış.')
        return redirect('producer:order_list')
    elif network_relation.status == 'pending':
        network_warning = 'Bu merkez ile ağ bağlantınız henüz onaylanmamış.'
        messages.info(request, network_warning)
    
    # Network aktivitesini güncelle
    network_relation.last_activity = timezone.now()
    network_relation.save(update_fields=['last_activity'])
    
    # Üretim logları - sadece bu siparişe ait
    production_logs = producer_order.production_logs.order_by('-created_at')
    
    # Kalıp dosyalarını al - sadece bu kalıba ait
    mold_files = ear_mold.modeled_files.all()
    
    # Revizyon dosyalarını al - sadece bu kalıba ait
    revisions = ear_mold.revisions.order_by('-created_at')
    
    # Son aktiviteler (loglar + mesajlar) - sadece bu siparişe ait
    activities = []
    
    # Production logları ekle
    for log in production_logs:
        activities.append({
            'type': 'production_log',
            'timestamp': log.created_at,
            'title': log.get_stage_display(),
            'description': log.description,
            'operator': log.operator,
            'data': log
        })
    
    # Sadece bu siparişle ilgili mesajları ekle
    related_messages = producer_order.messages.order_by('-created_at')
    for message in related_messages:
        activities.append({
            'type': 'message',
            'timestamp': message.created_at,
            'title': message.subject,
            'description': message.message[:100] + '...' if len(message.message) > 100 else message.message,
            'sender': 'Üretici' if message.sender_is_producer else 'Merkez',
            'data': message
        })
    
    # Aktiviteleri tarih sırasına göre sırala
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Form işlemleri - güvenli processing
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status and new_status in dict(ProducerOrder.STATUS_CHOICES):
                old_status = producer_order.get_status_display()
                producer_order.status = new_status
                producer_order.save()
                
                # Kalıp durumunu da senkronize et
                if new_status == 'delivered':
                    ear_mold.status = 'completed'
                    ear_mold.save()
                
                # Log oluştur
                stage_map = {
                    'designing': 'design_start',
                    'production': 'production_start',
                    'quality_check': 'quality_start',
                    'packaging': 'packaging_complete',
                    'shipping': 'shipping_start',
                    'delivered': 'delivered'
                }
                
                if new_status in stage_map:
                    ProducerProductionLog.objects.create(
                        order=producer_order,
                        stage=stage_map[new_status],
                        description=f'Durum güncellendi: {old_status} → {producer_order.get_status_display()}',
                        operator=request.user.get_full_name() or request.user.username
                    )
                
                # Merkeze bildirim gönder
                notify.send(
                    sender=request.user,
                    recipient=ear_mold.center.user,
                    verb='sipariş durumu güncellendi',
                    description=f'{ear_mold.patient_name} siparişinin durumu: {producer_order.get_status_display()}',
                    action_object=producer_order
                )
                
                messages.success(request, f'Sipariş durumu güncellendi: {producer_order.get_status_display()}')
                return redirect('producer:mold_detail', pk=pk)
        
        elif action == 'add_log':
            stage = request.POST.get('stage')
            description = request.POST.get('description')
            operator = request.POST.get('operator')
            duration = request.POST.get('duration')
            
            if stage and description:
                ProducerProductionLog.objects.create(
                    order=producer_order,
                    stage=stage,
                    description=description,
                    operator=operator or request.user.get_full_name() or request.user.username,
                    duration_minutes=int(duration) if duration else None
                )
                
                # Merkeze bildirim gönder
                notify.send(
                    sender=request.user,
                    recipient=ear_mold.center.user,
                    verb='üretim aşaması eklendi',
                    description=f'{ear_mold.patient_name}: {dict(ProducerProductionLog.STAGE_CHOICES)[stage]}',
                    action_object=producer_order
                )
                
                messages.success(request, 'Üretim logu eklendi.')
                return redirect('producer:mold_detail', pk=pk)
        
        elif action == 'add_shipping':
            shipping_company = request.POST.get('shipping_company')
            tracking_number = request.POST.get('tracking_number')
            shipping_cost = request.POST.get('shipping_cost')
            
            if shipping_company and tracking_number:
                producer_order.shipping_company = shipping_company
                producer_order.tracking_number = tracking_number
                if shipping_cost:
                    try:
                        producer_order.shipping_cost = float(shipping_cost)
                    except ValueError:
                        pass
                producer_order.status = 'shipping'
                producer_order.save()
                
                # Log oluştur
                ProducerProductionLog.objects.create(
                    order=producer_order,
                    stage='shipped',
                    description=f'Kargo: {shipping_company} - Takip No: {tracking_number}',
                    operator=request.user.get_full_name() or request.user.username
                )
                
                # Merkeze bildirim gönder
                notify.send(
                    sender=request.user,
                    recipient=ear_mold.center.user,
                    verb='sipariş kargoya verildi',
                    description=f'{ear_mold.patient_name} siparişi kargoya verildi. Takip No: {tracking_number}',
                    action_object=producer_order
                )
                
                messages.success(request, 'Kargo bilgileri eklendi ve sipariş kargoya verildi.')
                return redirect('producer:mold_detail', pk=pk)
    
    # Güvenli context - sadece kendi verileri
    context = {
        'producer_order': producer_order,
        'ear_mold': ear_mold,
        'producer': producer,
        'network_relation': network_relation,
        'network_warning': network_warning,
        'production_logs': production_logs,
        'mold_files': mold_files,
        'revisions': revisions,
        'activities': activities[:20],  # Son 20 aktivite
        'status_choices': ProducerOrder.STATUS_CHOICES,
        'stage_choices': ProducerProductionLog.STAGE_CHOICES,
    }
    
    return render(request, 'producer/mold_detail.html', context)


@producer_required
def mold_download(request, pk, file_id=None):
    """Güvenli Kalıp Dosyası İndirme - Sadece Kendi Siparişleri"""
    producer = request.user.producer
    
    # ÖNEMLİ GÜVENLİK: Önce bu üreticiye ait sipariş olup olmadığını kontrol et
    try:
        producer_order = ProducerOrder.objects.select_related('ear_mold', 'center').get(
            pk=pk,  # Sipariş ID'si ile erişim
            producer=producer  # Sadece kendi siparişleri
        )
        ear_mold = producer_order.ear_mold
    except ProducerOrder.DoesNotExist:
        messages.error(request, 'Bu kalıba erişim yetkiniz bulunmamaktadır.')
        return redirect('producer:order_list')
    
    # Ağ kontrolü - bu merkez üreticinin ağında mı? (Esnek kontrol)
    network_relation = producer.network_centers.filter(center=ear_mold.center).first()
    if not network_relation:
        messages.error(request, 'Bu merkez sizin ağınızda bulunmamaktadır.')
        return redirect('producer:order_list')
    
    # Eğer network suspended ise uyarı ver ama erişimi engelleme
    if network_relation.status == 'suspended':
        messages.warning(request, 'Bu merkez ile ağ bağlantınız askıya alınmış durumda.')
    elif network_relation.status == 'terminated':
        messages.error(request, 'Bu merkez ile ağ bağlantınız sonlandırılmış.')
        return redirect('producer:order_list')
    
    # Network aktivitesini güncelle
    from django.utils import timezone
    network_relation.last_activity = timezone.now()
    network_relation.save(update_fields=['last_activity'])
    
    # Dosyayı güvenli şekilde al
    if file_id:
        # Belirli bir modeled file indir
        mold_file = get_object_or_404(ModeledMold, pk=file_id, ear_mold=ear_mold)
        file_path = mold_file.file.path
        file_name = os.path.basename(file_path)
        download_type = 'modeled_file'
    else:
        # Ana kalıp dosyasını (scan_file) indir
        if ear_mold.scan_file:
            file_path = ear_mold.scan_file.path
            file_name = os.path.basename(file_path)
            download_type = 'scan_file'
        else:
            # Eğer scan_file yoksa, modeled_files'dan ilkini al
            mold_file = ear_mold.modeled_files.first()
            if not mold_file:
                messages.info(request, 'Bu kalıp için henüz indirilebilir dosya bulunmuyor. Merkez tarafından dosya yüklendiğinde burada görünecektir.')
                return redirect('producer:mold_detail', pk=pk)
            file_path = mold_file.file.path
            file_name = os.path.basename(file_path)
            download_type = 'modeled_file'
    
    # Dosya varlığını kontrol et
    if not os.path.exists(file_path):
        messages.error(request, 'Dosya bulunamadı veya erişilemez.')
        return redirect('producer:mold_detail', pk=pk)
    
    # Dosya indirme log'u ekle
    ProducerProductionLog.objects.create(
        order=producer_order,
        stage='design_start',
        description=f'{download_type.title()} indirildi: {file_name}',
        operator=request.user.get_full_name() or request.user.username
    )
    
    # Merkeze bildirim gönder
    notify.send(
        sender=request.user,
        recipient=ear_mold.center.user,
        verb='kalıp dosyası indirildi',
        description=f'{producer.company_name} tarafından {ear_mold.patient_name} kalıp dosyası ({download_type}) indirildi.',
        action_object=producer_order
    )
    
    try:
        # Dosya türünü al
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        # Dosya içeriğini oku
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=mime_type)
        
        # Dosya adını ayarla - güvenli encoding
        safe_filename = file_name.encode('ascii', 'ignore').decode('ascii')
        if not safe_filename:
            safe_filename = f'mold_file_{producer_order.id}'
        
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
        response['Content-Length'] = os.path.getsize(file_path)
        
        return response
        
    except (IOError, OSError) as e:
        messages.error(request, f'Dosya okunurken hata oluştu: {str(e)}')
        return redirect('producer:mold_detail', pk=pk)


@producer_required
def mold_upload_result(request, pk):
    """Güvenli Üretilen Kalıp Dosyası Yükleme - Sadece Kendi Siparişleri"""
    producer = request.user.producer
    
    # ÖNEMLİ GÜVENLİK: Önce bu üreticiye ait sipariş olup olmadığını kontrol et
    try:
        producer_order = ProducerOrder.objects.select_related('ear_mold', 'center').get(
            pk=pk,  # Sipariş ID'si ile erişim
            producer=producer  # Sadece kendi siparişleri
        )
        ear_mold = producer_order.ear_mold
    except ProducerOrder.DoesNotExist:
        messages.error(request, 'Bu siparişe erişim yetkiniz bulunmamaktadır.')
        return redirect('producer:order_list')
    
    # Ağ kontrolü - bu merkez üreticinin ağında mı? (Esnek kontrol)
    network_relation = producer.network_centers.filter(center=ear_mold.center).first()
    if not network_relation:
        messages.error(request, 'Bu merkez sizin ağınızda bulunmamaktadır.')
        return redirect('producer:order_list')
    
    # Eğer network suspended ise uyarı ver ama erişimi engelleme
    if network_relation.status == 'suspended':
        messages.warning(request, 'Bu merkez ile ağ bağlantınız askıya alınmış durumda.')
    elif network_relation.status == 'terminated':
        messages.error(request, 'Bu merkez ile ağ bağlantınız sonlandırılmış.')
        return redirect('producer:order_list')
    
    # Network aktivitesini güncelle
    network_relation.last_activity = timezone.now()
    network_relation.save(update_fields=['last_activity'])
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        description = request.POST.get('description', '')
        
        if uploaded_file:
            # Dosya türü kontrolü
            allowed_extensions = ['.stl', '.obj', '.ply', '.zip', '.rar']
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            
            if file_extension not in allowed_extensions:
                messages.error(request, f'Desteklenmeyen dosya türü. İzin verilen türler: {", ".join(allowed_extensions)}')
                return render(request, 'producer/mold_upload_result.html', {
                    'producer_order': producer_order,
                    'ear_mold': ear_mold,
                })
            
            # Dosya boyutu kontrolü (50MB)
            if uploaded_file.size > 50 * 1024 * 1024:
                messages.error(request, 'Dosya boyutu 50MB\'dan büyük olamaz.')
                return render(request, 'producer/mold_upload_result.html', {
                    'producer_order': producer_order,
                    'ear_mold': ear_mold,
                })
            
            # Yeni dosya oluştur
            mold_file = ModeledMold.objects.create(
                ear_mold=ear_mold,
                file=uploaded_file,
                notes=description,
                status='waiting'  # Admin onayı beklesin
            )
            
            # Üretim logu ekle
            ProducerProductionLog.objects.create(
                order=producer_order,
                stage='production_complete',
                description=f'Üretilen kalıp dosyası yüklendi: {uploaded_file.name}',
                operator=request.user.get_full_name() or request.user.username
            )
            
            # Siparişin durumunu güncelle
            if producer_order.status in ['received', 'designing', 'production']:
                producer_order.status = 'quality_check'
                producer_order.save()
                
                # Kalıp durumunu da güncelle
                if ear_mold.status != 'processing':
                    ear_mold.status = 'processing'
                    ear_mold.save()
            
            # Merkeze bildirim gönder
            notify.send(
                sender=request.user,
                recipient=ear_mold.center.user,
                verb='üretilen kalıp yüklendi',
                description=f'{ear_mold.patient_name} için üretilen kalıp dosyası yüklendi.',
                action_object=producer_order
            )
            
            messages.success(request, 'Üretilen kalıp dosyası başarıyla yüklendi ve kalite kontrole gönderildi.')
            return redirect('producer:mold_detail', pk=pk)
        else:
            messages.error(request, 'Lütfen bir dosya seçin.')
    
    # Güvenli context
    context = {
        'producer_order': producer_order,
        'ear_mold': ear_mold,
        'producer': producer,
        'allowed_extensions': ['.stl', '.obj', '.ply', '.zip', '.rar'],
        'max_file_size': '50MB',
    }
    
    return render(request, 'producer/mold_upload_result.html', context)


# Admin View'ları (Ana yönetim tarafından kullanılacak)

@staff_member_required
def admin_producer_list(request):
    """Admin: Üretici Listesi"""
    from django.core.paginator import Paginator
    
    producers = Producer.objects.all().order_by('-created_at')
    
    # Filtreleme
    status_filter = request.GET.get('status')
    if status_filter == 'verified':
        producers = producers.filter(is_verified=True)
    elif status_filter == 'pending':
        producers = producers.filter(is_verified=False)
    elif status_filter == 'active':
        producers = producers.filter(is_active=True)
    elif status_filter == 'inactive':
        producers = producers.filter(is_active=False)
    
    producer_type = request.GET.get('type')
    if producer_type:
        producers = producers.filter(producer_type=producer_type)
    
    # Arama
    search = request.GET.get('search')
    if search:
        producers = producers.filter(
            Q(company_name__icontains=search) |
            Q(brand_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    # Sayfalama
    paginator = Paginator(producers, 20)  # Her sayfada 20 üretici
    page_number = request.GET.get('page')
    producers_page = paginator.get_page(page_number)
    
    # İstatistikler
    all_producers = Producer.objects.all()
    verified_count = all_producers.filter(is_verified=True).count()
    active_count = all_producers.filter(is_active=True).count()
    pending_count = all_producers.filter(is_verified=False).count()
    
    context = {
        'producers': producers_page,
        'verified_count': verified_count,
        'active_count': active_count,
        'pending_count': pending_count,
        'producer_types': Producer.PRODUCER_TYPE_CHOICES,
    }
    
    return render(request, 'producer/admin/producer_list.html', context)


@staff_member_required
def admin_producer_detail(request, pk):
    """Admin: Üretici Detay"""
    producer = get_object_or_404(Producer, pk=pk)
    
    # İstatistikler
    total_orders = producer.orders.count()
    active_orders = producer.orders.exclude(status__in=['delivered', 'cancelled']).count()
    
    # Ağ merkezleri ve kalıp bilgileri
    network_centers = producer.network_centers.filter(status='active').select_related('center')
    network_centers_count = network_centers.count()
    
    # Bu üreticinin kalıpları
    producer_molds = EarMold.objects.filter(
        producer_orders__producer=producer
    ).distinct().select_related('center').order_by('-created_at')
    
    # Kalıp istatistikleri
    total_molds = producer_molds.count()
    processing_molds = producer_molds.filter(status='processing').count()
    completed_molds = producer_molds.filter(status='completed').count()
    delivered_molds = producer_molds.filter(status='delivered').count()
    
    # Merkez bazında kalıp sayıları
    center_mold_stats = {}
    for network in network_centers:
        center_molds = producer_molds.filter(center=network.center)
        center_mold_stats[network.center.id] = {
            'center': network.center,
            'total': center_molds.count(),
            'processing': center_molds.filter(status='processing').count(),
            'completed': center_molds.filter(status='completed').count(),
            'delivered': center_molds.filter(status='delivered').count(),
            'recent_molds': center_molds[:5]  # Son 5 kalıp
        }
    
    context = {
        'producer': producer,
        'total_orders': total_orders,
        'active_orders': active_orders,
        'network_centers': network_centers,
        'network_centers_count': network_centers_count,
        'producer_molds': producer_molds[:10],  # Son 10 kalıp
        'total_molds': total_molds,
        'processing_molds': processing_molds,
        'completed_molds': completed_molds,
        'delivered_molds': delivered_molds,
        'center_mold_stats': center_mold_stats,
    }
    
    return render(request, 'producer/admin/producer_detail.html', context)


@staff_member_required
def admin_producer_verify(request, pk):
    """Admin: Üretici Doğrulama"""
    producer = get_object_or_404(Producer, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'verify':
            producer.is_verified = True
            producer.verification_date = timezone.now()
            producer.save()
            
            # Üreticiye bildirim gönder
            notify.send(
                sender=request.user,
                recipient=producer.user,
                verb='hesabınız doğrulandı',
                action_object=producer,
                description='Üretici merkez hesabınız başarıyla doğrulandı.'
            )
            
            messages.success(request, f'{producer.company_name} başarıyla doğrulandı.')
        
        elif action == 'unverify':
            producer.is_verified = False
            producer.verification_date = None
            producer.save()
            messages.success(request, f'{producer.company_name} doğrulaması kaldırıldı.')
    
    return redirect('producer:admin_producer_detail', pk=pk)


@staff_member_required
def admin_producer_update_limit(request, pk):
    """Admin: Üretici Limit Güncelleme"""
    producer = get_object_or_404(Producer, pk=pk)
    
    if request.method == 'POST':
        new_limit = request.POST.get('mold_limit')
        if new_limit:
            try:
                producer.mold_limit = int(new_limit)
                producer.save()
                messages.success(request, f'{producer.company_name} kalıp limiti güncellendi.')
            except ValueError:
                messages.error(request, 'Geçersiz limit değeri.')
    
    return redirect('producer:admin_producer_detail', pk=pk)


@staff_member_required
def admin_mold_list(request):
    """Admin: Tüm Kalıpları Görüntüle"""
    from django.core.paginator import Paginator
    
    molds = EarMold.objects.all().order_by('-created_at')
    
    # Filtreleme
    status_filter = request.GET.get('status')
    mold_type_filter = request.GET.get('mold_type')
    center_filter = request.GET.get('center')
    producer_filter = request.GET.get('producer')
    
    if status_filter:
        molds = molds.filter(status=status_filter)
    if mold_type_filter:
        molds = molds.filter(mold_type=mold_type_filter)
    if center_filter:
        molds = molds.filter(center_id=center_filter)
    if producer_filter:
        molds = molds.filter(producer_orders__producer_id=producer_filter).distinct()
    
    # Arama
    search = request.GET.get('search')
    if search:
        molds = molds.filter(
            Q(patient_name__icontains=search) |
            Q(patient_surname__icontains=search) |
            Q(center__name__icontains=search)
        )
    
    # Sayfalama
    paginator = Paginator(molds, 20)  # Her sayfada 20 kalıp
    page_number = request.GET.get('page')
    molds_page = paginator.get_page(page_number)
    
    # Filtreleme için gerekli veriler
    centers = Center.objects.filter(is_active=True).order_by('name')
    producers = Producer.objects.filter(is_active=True).order_by('company_name')
    
    # İstatistikler
    total_molds = EarMold.objects.count()
    processing_molds = EarMold.objects.filter(status='processing').count()
    completed_molds = EarMold.objects.filter(status='completed').count()
    delivered_molds = EarMold.objects.filter(status='delivered').count()
    
    context = {
        'molds': molds_page,
        'centers': centers,
        'producers': producers,
        'status_choices': EarMold.STATUS_CHOICES,
        'mold_type_choices': EarMold.MOLD_TYPE_CHOICES,
        'current_filters': {
            'status': status_filter,
            'mold_type': mold_type_filter,
            'center': center_filter,
            'producer': producer_filter,
            'search': search,
        },
        # İstatistikler
        'total_molds': total_molds,
        'processing_molds': processing_molds,
        'completed_molds': completed_molds,
        'delivered_molds': delivered_molds,
    }
    
    return render(request, 'producer/admin/mold_list.html', context)


@staff_member_required
def admin_mold_download(request, pk):
    """Admin: Kalıp Dosyası İndir"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)
        
        # Önce scan_file'ı kontrol et
        if mold.scan_file:
            file_path = mold.scan_file.path
            file_name = os.path.basename(file_path)
        else:
            # Yoksa modeled_files'dan ilkini al
            file = mold.modeled_files.first()
            if not file:
                raise Http404("Bu kalıp için dosya bulunamadı.")
            file_path = file.file.path
            file_name = os.path.basename(file_path)

        # Dosya türünü al
        mime_type, _ = mimetypes.guess_type(file_path)

        # Dosya içeriğini oku
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=mime_type)

        # Dosya adını ayarla
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'

        return response
    except Exception as e:
        return HttpResponse(f"Dosya indirme hatası: {str(e)}", status=500)


@producer_required
def mold_download_file(request, pk, file_id):
    """Belirli modeled dosya indirme"""
    return mold_download(request, pk, file_id)


@producer_required 
def permanent_scan_download(request, mold_id):
    """
    Sabit Ana Tarama Dosyası İndirme Linki
    Bu link kalıcıdır ve süre kısıtlaması yoktur
    """
    producer = request.user.producer
    
    try:
        # Kalıbı bul
        ear_mold = get_object_or_404(EarMold, pk=mold_id)
        
        # Bu kalıp için üreticinin siparişi var mı kontrol et
        producer_order = ProducerOrder.objects.filter(
            ear_mold=ear_mold,
            producer=producer
        ).first()
        
        if not producer_order:
            messages.error(request, 'Bu kalıba erişim yetkiniz bulunmamaktadır.')
            return redirect('producer:mold_list')
        
        # Ağ kontrolü
        network_relation = producer.network_centers.filter(center=ear_mold.center).first()
        if not network_relation:
            messages.error(request, 'Bu merkez sizin ağınızda bulunmamaktadır.')
            return redirect('producer:mold_list')
        
        # Sadece terminated durumunda erişimi engelle
        if network_relation.status == 'terminated':
            messages.error(request, 'Bu merkez ile ağ bağlantınız sonlandırılmış.')
            return redirect('producer:mold_list')
        
        # Ana tarama dosyası kontrolü
        if not ear_mold.scan_file:
            messages.info(request, 'Bu kalıp için ana tarama dosyası henüz yüklenmemiş.')
            return redirect('producer:mold_detail', pk=producer_order.pk)
        
        file_path = ear_mold.scan_file.path
        
        # Dosya varlığını kontrol et
        if not os.path.exists(file_path):
            messages.error(request, 'Dosya bulunamadı veya erişilemez.')
            return redirect('producer:mold_detail', pk=producer_order.pk)
        
        # Network aktivitesini güncelle
        network_relation.last_activity = timezone.now()
        network_relation.save(update_fields=['last_activity'])
        
        # Dosya indirme log'u ekle
        ProducerProductionLog.objects.create(
            order=producer_order,
            stage='design_start',
            description=f'Ana tarama dosyası indirildi (sabit link): {os.path.basename(file_path)}',
            operator=request.user.get_full_name() or request.user.username
        )
        
        # Merkeze bildirim gönder
        notify.send(
            sender=request.user,
            recipient=ear_mold.center.user,
            verb='ana tarama dosyası indirildi',
            description=f'{producer.company_name} tarafından {ear_mold.patient_name} ana tarama dosyası indirildi (sabit link).',
            action_object=producer_order
        )
        
        try:
            # Dosya türünü al
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Dosya içeriğini oku
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type=mime_type)
            
            # Dosya adını ayarla
            file_name = os.path.basename(file_path)
            safe_filename = file_name.encode('ascii', 'ignore').decode('ascii')
            if not safe_filename:
                safe_filename = f'scan_file_{ear_mold.id}_{ear_mold.patient_name}'
            
            response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            response['Content-Length'] = os.path.getsize(file_path)
            
            return response
            
        except (IOError, OSError) as e:
            messages.error(request, f'Dosya okunurken hata oluştu: {str(e)}')
            return redirect('producer:mold_detail', pk=producer_order.pk)
            
    except EarMold.DoesNotExist:
        messages.error(request, 'Kalıp bulunamadı.')
        return redirect('producer:mold_list')


@producer_required
def permanent_model_download(request, file_id):
    """
    Sabit Model Dosyası İndirme Linki
    Bu link kalıcıdır ve süre kısıtlaması yoktur
    """
    producer = request.user.producer
    
    try:
        # Model dosyasını bul
        model_file = get_object_or_404(ModeledMold, pk=file_id)
        ear_mold = model_file.ear_mold
        
        # Bu kalıp için üreticinin siparişi var mı kontrol et
        producer_order = ProducerOrder.objects.filter(
            ear_mold=ear_mold,
            producer=producer
        ).first()
        
        if not producer_order:
            messages.error(request, 'Bu dosyaya erişim yetkiniz bulunmamaktadır.')
            return redirect('producer:mold_list')
        
        # Ağ kontrolü
        network_relation = producer.network_centers.filter(center=ear_mold.center).first()
        if not network_relation:
            messages.error(request, 'Bu merkez sizin ağınızda bulunmamaktadır.')
            return redirect('producer:mold_list')
        
        # Sadece terminated durumunda erişimi engelle
        if network_relation.status == 'terminated':
            messages.error(request, 'Bu merkez ile ağ bağlantınız sonlandırılmış.')
            return redirect('producer:mold_list')
        
        file_path = model_file.file.path
        
        # Dosya varlığını kontrol et
        if not os.path.exists(file_path):
            messages.error(request, 'Dosya bulunamadı veya erişilemez.')
            return redirect('producer:mold_detail', pk=producer_order.pk)
        
        # Network aktivitesini güncelle
        network_relation.last_activity = timezone.now()
        network_relation.save(update_fields=['last_activity'])
        
        # Dosya indirme log'u ekle
        ProducerProductionLog.objects.create(
            order=producer_order,
            stage='design_start',
            description=f'Model dosyası indirildi (sabit link): {os.path.basename(file_path)}',
            operator=request.user.get_full_name() or request.user.username
        )
        
        # Merkeze bildirim gönder
        notify.send(
            sender=request.user,
            recipient=ear_mold.center.user,
            verb='model dosyası indirildi',
            description=f'{producer.company_name} tarafından {ear_mold.patient_name} model dosyası indirildi (sabit link).',
            action_object=producer_order
        )
        
        try:
            # Dosya türünü al
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Dosya içeriğini oku
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type=mime_type)
            
            # Dosya adını ayarla
            file_name = os.path.basename(file_path)
            safe_filename = file_name.encode('ascii', 'ignore').decode('ascii')
            if not safe_filename:
                safe_filename = f'model_file_{model_file.id}_{ear_mold.patient_name}'
            
            response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            response['Content-Length'] = os.path.getsize(file_path)
            
            return response
            
        except (IOError, OSError) as e:
            messages.error(request, f'Dosya okunurken hata oluştu: {str(e)}')
            return redirect('producer:mold_detail', pk=producer_order.pk)
            
    except ModeledMold.DoesNotExist:
        messages.error(request, 'Model dosyası bulunamadı.')
        return redirect('producer:mold_list')
