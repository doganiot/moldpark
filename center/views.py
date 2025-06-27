from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Center
from .forms import CenterProfileForm, CenterLimitForm
from .decorators import center_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import logout

from django.db.models import Count, Q
from django.db import models
from datetime import datetime, timedelta
from mold.models import EarMold
from producer.models import ProducerNetwork, Producer
from django.http import JsonResponse
from django.utils import timezone

# Create your views here.

@login_required
def dashboard(request):
    try:
        center = request.user.center
    except Center.DoesNotExist:
        messages.error(request, "Profiliniz eksik. Lütfen merkez bilgilerinizi tamamlayın.")
        return redirect('center:profile')
    
    # Tüm kalıpları al
    molds = center.molds.all()
    
    # İstatistikleri hesapla
    total_molds = molds.count()
    
    # Bekleyen kalıplar: Teslim edilmemiş, iptal edilmemiş ve tamamlanmamış olanlar
    pending_molds = molds.exclude(status__in=['delivered', 'rejected', 'completed']).count()
    
    processing_molds = molds.filter(status='processing').count()
    completed_molds = molds.filter(status='completed').count()
    
    # Son 5 kalıbı al
    recent_molds = molds.order_by('-created_at')[:5]
    
    # Abonelik ve limit kontrolü
    from core.models import UserSubscription
    
    try:
        subscription = UserSubscription.objects.get(user=request.user, is_active=True)
        used_molds = subscription.current_usage
        remaining_limit = max(0, subscription.plan.limit_per_month - used_molds)
        usage_percentage = int((used_molds / subscription.plan.limit_per_month) * 100) if subscription.plan.limit_per_month > 0 else 0
        usage_offset = 327 - (327 * usage_percentage / 100)  # SVG circle için
    except UserSubscription.DoesNotExist:
        # Fallback eski sistem
        used_molds = total_molds
        remaining_limit = max(0, center.mold_limit - used_molds)
        usage_percentage = int((used_molds / center.mold_limit) * 100) if center.mold_limit > 0 else 0
        usage_offset = 327 - (327 * usage_percentage / 100)
        subscription = None
    
    # Üretici ağ bilgileri
    producer_networks = ProducerNetwork.objects.filter(
        center=center, 
        status='active'
    ).select_related('producer')
    
    return render(request, 'center/dashboard.html', {
        'center': center,
        'molds': molds,
        'total_molds': total_molds,
        'pending_molds': pending_molds,
        'processing_molds': processing_molds,
        'completed_molds': completed_molds,
        'recent_molds': recent_molds,
        'used_molds': used_molds,
        'remaining_limit': remaining_limit,
        'producer_networks': producer_networks,
        'subscription': subscription,
        'usage_percentage': usage_percentage,
        'usage_offset': usage_offset,
    })

@login_required
def profile(request):
    try:
        center = request.user.center
    except Center.DoesNotExist:
        if request.method == 'POST':
            form = CenterProfileForm(request.POST)
            if form.is_valid():
                center = form.save(commit=False)
                center.user = request.user
                center.save()
                messages.success(request, 'Merkez profiliniz oluşturuldu.')
                return redirect('center:dashboard')
        else:
            form = CenterProfileForm()
        return render(request, 'center/profile_create.html', {'form': form})

    if request.method == 'POST':
        form = CenterProfileForm(request.POST, instance=center)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil bilgileriniz güncellendi.')
            return redirect('center:profile')
    else:
        form = CenterProfileForm(instance=center)
    password_form = PasswordChangeForm(request.user)
    return render(request, 'center/profile.html', {'form': form, 'password_form': password_form})

# Merkez mesajlaşma view'ları kaldırıldı - Sadece Admin Dashboard üzerinden mesajlaşma

def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
def center_detail(request, pk):
    center = get_object_or_404(Center, pk=pk)
    is_own = (request.user == center.user)
    is_admin_user = request.user.is_staff or request.user.is_superuser
    limit_form = None
    if is_admin_user:
        limit_form = CenterLimitForm(instance=center)
    return render(request, 'center/center_detail.html', {
        'center': center,
        'is_own': is_own,
        'is_admin_user': is_admin_user,
        'limit_form': limit_form,
    })

@user_passes_test(is_admin)
@login_required
def center_limit_update(request, pk):
    center = get_object_or_404(Center, pk=pk)
    if request.method == 'POST':
        form = CenterLimitForm(request.POST, instance=center)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kalıp limiti güncellendi.')
            return redirect('center:center_detail', pk=center.pk)
    else:
        form = CenterLimitForm(instance=center)
    return render(request, 'center/center_detail.html', {
        'center': center,
        'is_own': False,
        'is_admin_user': True,
        'limit_form': form,
    })

@staff_member_required
def admin_dashboard(request):
    # Temel istatistikler
    total_centers = Center.objects.count()
    active_centers = Center.objects.filter(is_active=True).count()
    total_molds = EarMold.objects.count()
    
    # Kalıp durumları
    mold_status_counts = EarMold.objects.values('status').annotate(count=Count('id'))
    mold_stats = {item['status']: item['count'] for item in mold_status_counts}
    
    # ÜRETİCİ İSTATİSTİKLERİ
    from producer.models import Producer, ProducerOrder, ProducerNetwork
    total_producers = Producer.objects.count()
    active_producers = Producer.objects.filter(is_active=True, is_verified=True).count()
    total_networks = ProducerNetwork.objects.count()
    active_networks = ProducerNetwork.objects.filter(status='active').count()
    
    # Sipariş istatistikleri
    total_orders = ProducerOrder.objects.count()
    order_status_counts = ProducerOrder.objects.values('status').annotate(count=Count('id'))
    order_stats = {item['status']: item['count'] for item in order_status_counts}
    
    # Son aktiviteler (birleştirilmiş)
    from datetime import timedelta
    from django.utils import timezone
    
    last_week = timezone.now() - timedelta(days=7)
    
    # Son kalıplar
    recent_molds = EarMold.objects.filter(created_at__gte=last_week).order_by('-created_at')[:5]
    
    # Son siparişler
    recent_orders = ProducerOrder.objects.filter(created_at__gte=last_week).order_by('-created_at')[:5]
    
    # Son network katılımları
    recent_networks = ProducerNetwork.objects.filter(joined_at__gte=last_week).order_by('-joined_at')[:5]
    
    # Aylık trendler
    from django.utils.timezone import now
    import calendar
    
    current_month = now().month
    current_year = now().year
    
    monthly_molds = EarMold.objects.filter(
        created_at__year=current_year,
        created_at__month=current_month
    ).count()
    
    monthly_orders = ProducerOrder.objects.filter(
        created_at__year=current_year,
        created_at__month=current_month
    ).count()
    
    # Sorunlu durumlar - DEBUG VE DOĞRU STATUS KONTROLÜ
    from django.db.models import Q
    
    # Debug: Mevcut sipariş statuslarını kontrol et
    actual_order_statuses = list(ProducerOrder.objects.values_list('status', flat=True).distinct())
    print(f"DEBUG - Mevcut sipariş statusları: {actual_order_statuses}")
    
    # Beklemede olan siparişler (sadece gerçekte var olan statuslar)
    pending_statuses = [s for s in ['pending', 'received', 'designing'] if s in actual_order_statuses]
    pending_orders = ProducerOrder.objects.filter(status__in=pending_statuses).count() if pending_statuses else 0
    
    # Debug: Mevcut kalıp statuslarını kontrol et  
    actual_mold_statuses = list(EarMold.objects.values_list('status', flat=True).distinct())
    print(f"DEBUG - Mevcut kalıp statusları: {actual_mold_statuses}")
    
    # Revizyon bekleyen kalıplar (sadece gerçekte var olan statuslar)
    revision_statuses = [s for s in ['revision', 'revision_requested'] if s in actual_mold_statuses]
    revision_molds = EarMold.objects.filter(status__in=revision_statuses).count() if revision_statuses else 0
    
    # Gecikmiş sipariş sorgusu - Sadece aktif ve gerçekten gecikmiş olanları say
    current_time = timezone.now()
    
    # Sadece gerçekte var olan statuslarda olanları kontrol et
    valid_overdue_statuses = [s for s in ['received', 'designing', 'production', 'quality_check'] if s in actual_order_statuses]
    
    # Gecikmiş siparişleri daha akıllı şekilde hesapla:
    # 1. estimated_delivery NULL olmamalı
    # 2. Gerçekten geçmişte olmalı
    # 3. Sipariş durumu aktif olmalı (teslim edilmemiş)
    # 4. İlgili kalıp da teslim edilmemiş olmalı
    overdue_orders = ProducerOrder.objects.filter(
        estimated_delivery__isnull=False,  # NULL tarih kontrolü
        estimated_delivery__lt=current_time.date(),  # Sadece tarih karşılaştırması
        status__in=valid_overdue_statuses,
        ear_mold__status__in=['pending', 'processing', 'quality_check', 'waiting']  # Kalıp da aktif durumda
    ).exclude(
        ear_mold__status__in=['delivered', 'completed']  # Teslim edilmiş kalıpları hariç tut
    ).count()
    
    # Chart verileri
    mold_chart_data = {
        'labels': [dict(EarMold.STATUS_CHOICES).get(k, k) for k in mold_stats.keys()],
        'data': list(mold_stats.values())
    }
    
    order_chart_data = {
        'labels': [dict(ProducerOrder.STATUS_CHOICES).get(k, k) for k in order_stats.keys()],
        'data': list(order_stats.values())
    }
    
    # Mesajlaşma sistemi kaldırıldı
    
    # Kritik uyarılar - Sadece gerçek sorunları göster
    warnings = []
    if overdue_orders > 0:
        warnings.append(f'{overdue_orders} adet aktif gecikmiş sipariş (kalıp teslim edilmemiş)')
    if revision_molds > 0:
        warnings.append(f'{revision_molds} adet revizyon bekleyen kalıp')
    if pending_orders > 10:  # 5'ten 10'a çıkardık
        warnings.append(f'{pending_orders} adet beklemede olan sipariş (Normal seviyenin üstünde)')
    
    return render(request, 'center/admin_dashboard.html', {
        'total_centers': total_centers,
        'active_centers': active_centers,
        'total_molds': total_molds,
        'total_producers': total_producers,
        'active_producers': active_producers,
        'total_networks': total_networks,
        'active_networks': active_networks,
        'total_orders': total_orders,
        'monthly_molds': monthly_molds,
        'monthly_orders': monthly_orders,
        'pending_orders': pending_orders,
        'revision_molds': revision_molds,
        'overdue_orders': overdue_orders,
        'mold_stats': mold_stats,
        'order_stats': order_stats,
        'mold_chart_data': mold_chart_data,
        'order_chart_data': order_chart_data,
        'recent_molds': recent_molds,
        'recent_orders': recent_orders,
        'recent_networks': recent_networks,

        'warnings': warnings,
    })

@staff_member_required
def admin_mold_list(request):
    from mold.models import EarMold
    from center.models import Center
    molds = EarMold.objects.select_related('center').all().order_by('-created_at')
    # Filtreleme
    center_id = request.GET.get('center')
    status = request.GET.get('status')
    mold_type = request.GET.get('mold_type')
    if center_id:
        molds = molds.filter(center_id=center_id)
    if status:
        molds = molds.filter(status=status)
    if mold_type:
        molds = molds.filter(mold_type=mold_type)
    centers = Center.objects.all()
    status_choices = EarMold._meta.get_field('status').choices if hasattr(EarMold._meta.get_field('status'), 'choices') else []
    mold_type_choices = EarMold._meta.get_field('mold_type').choices if hasattr(EarMold._meta.get_field('mold_type'), 'choices') else []
    return render(request, 'center/admin_mold_list.html', {
        'molds': molds,
        'centers': centers,
        'status_choices': status_choices,
        'mold_type_choices': mold_type_choices,
        'selected_center': center_id,
        'selected_status': status,
        'selected_mold_type': mold_type,
    })

@staff_member_required
def admin_mold_detail(request, pk):
    from mold.models import EarMold
    from mold.forms import ModeledMoldForm
    mold = get_object_or_404(EarMold, pk=pk)
    status_choices = EarMold._meta.get_field('status').choices
    model_form = ModeledMoldForm()
    return render(request, 'center/admin_mold_detail.html', {
        'mold': mold, 
        'status_choices': status_choices,
        'model_form': model_form
    })

@staff_member_required
def admin_mold_update_status(request, pk):
    from mold.models import EarMold
    from notifications.signals import notify
    mold = get_object_or_404(EarMold, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status and new_status != mold.status:
            mold.status = new_status
            mold.save()
            # Bildirim gönder
            notify.send(
                sender=request.user,
                recipient=mold.center.user,
                verb='kalıp durumu güncellendi',
                action_object=mold,
                description=f'Kalıbınızın yeni durumu: {mold.get_status_display()}'
            )
            messages.success(request, 'Kalıp durumu güncellendi ve merkeze bildirildi.')
        return redirect('center:admin_mold_detail', pk=mold.pk)
    return redirect('center:admin_mold_detail', pk=mold.pk)

@staff_member_required
def admin_upload_model(request, mold_id):
    """Admin tarafından model yükleme"""
    from mold.models import EarMold, ModeledMold
    from mold.forms import ModeledMoldForm
    from notifications.signals import notify
    
    mold = get_object_or_404(EarMold, pk=mold_id)
    
    if request.method == 'POST':
        form = ModeledMoldForm(request.POST, request.FILES)
        if form.is_valid():
            model = form.save(commit=False)
            model.ear_mold = mold
            model.status = 'approved'  # Model durumunu otomatik "Onaylandı" yap
            model.save()
            
            # Kalıp durumunu "Tamamlandı" olarak güncelle
            if mold.status != 'completed':
                mold.status = 'completed'
                mold.save()
            
            # Merkeze bildirim gönder
            notify.send(
                sender=request.user,
                recipient=mold.center.user,
                verb='işlenmiş model yükledi',
                action_object=mold,
                description=f'{mold.patient_name} {mold.patient_surname} için işlenmiş model hazır ve kalıp tamamlandı.'
            )
            
            messages.success(request, 'Model başarıyla yüklendi ve onaylandı, kalıp durumu "Tamamlandı" olarak güncellendi ve merkeze bildirildi.')
        else:
            messages.error(request, 'Model yüklenirken bir hata oluştu.')
    
    return redirect('center:admin_mold_detail', pk=mold_id)

@staff_member_required
def admin_delete_model(request, model_id):
    """Admin tarafından model silme"""
    from mold.models import ModeledMold
    
    model = get_object_or_404(ModeledMold, pk=model_id)
    mold_id = model.ear_mold.id
    
    if request.method == 'POST':
        try:
            model.delete()
            messages.success(request, 'Model başarıyla silindi.')
        except Exception as e:
            messages.error(request, 'Model silinirken bir hata oluştu.')
    
    return redirect('center:admin_mold_detail', pk=mold_id)

@login_required
def change_avatar(request):
    center = request.user.center
    if request.method == 'POST' and 'avatar' in request.FILES:
        center.avatar = request.FILES['avatar']
        center.save()
        messages.success(request, 'Profil fotoğrafınız güncellendi.')
    return redirect('center:profile')

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Hesabınız ve tüm verileriniz silindi.')
        return redirect('core:home')
    return redirect('center:profile')

@staff_member_required
def admin_revision_list(request):
    from mold.models import Revision
    revisions = Revision.objects.select_related('mold', 'mold__center').order_by('-created_at')
    return render(request, 'center/admin_revision_list.html', {'revisions': revisions})

@login_required
def notification_list(request):
    # Filtre parametresi
    filter_type = request.GET.get('filter', 'all')
    
    notifications = request.user.notifications.all()
    
    if filter_type == 'unread':
        notifications = notifications.unread()
    elif filter_type == 'read':
        notifications = notifications.read()
    
    notifications = notifications.order_by('-timestamp')
    
    return render(request, 'center/notification_list.html', {
        'object_list': notifications,
        'filter': filter_type
    })

@login_required
def mark_notification_read(request, notification_id):
    """Tek bir bildirimi okundu olarak işaretle"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.mark_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        unread_count = request.user.notifications.unread().count()
        return JsonResponse({
            'success': True, 
            'message': 'Bildirim okundu olarak işaretlendi.',
            'unread_count': unread_count
        })
    
    return redirect('center:notification_list')

@login_required
def mark_all_notifications_read(request):
    """Tüm bildirimleri okundu olarak işaretle"""
    request.user.notifications.unread().mark_all_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Tüm bildirimler okundu olarak işaretlendi.'})
    
    return redirect('center:notification_list')

@login_required
def delete_notification(request, notification_id):
    """Bildirimi sil"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Bildirim silindi.'})
    
    return redirect('center:notification_list')

@staff_member_required
def admin_message_list(request):
    from .models import Center
    
    # Admin kullanıcıya Center yoksa otomatik oluştur
    if not hasattr(request.user, 'center'):
        Center.objects.create(
            user=request.user,
            name='Ana Merkez',
            address='-',
            phone='-',
            is_active=True
        )
    
    # Tüm mesajları getir
    # CenterMessage kaldırıldı - Merkezi mesajlaşma sistemi kullanılıyor
    messages = []
    
    # Filtreleme
    filter_type = request.GET.get('filter')
    if filter_type == 'unread':
        messages = messages.filter(is_read=False)
    elif filter_type == 'archived':
        messages = messages.filter(is_archived=True)
    
    # Arama
    search_query = request.GET.get('search')
    if search_query:
        messages = messages.filter(
            models.Q(subject__icontains=search_query) |
            models.Q(message__icontains=search_query) |
            models.Q(sender__name__icontains=search_query) |
            models.Q(receiver__name__icontains=search_query)
        )
    
    return render(request, 'center/admin_message_list.html', {
        'messages': messages,
        'filter_type': filter_type,
        'search_query': search_query
    })

@staff_member_required
def archive_message(request, message_id):
    messages.error(request, 'Bu özellik artık kullanılmıyor. Merkezi mesajlaşma sistemi kullanın.')
    return redirect('center:admin_message_list')

@staff_member_required
def unarchive_message(request, message_id):
    messages.error(request, 'Bu özellik artık kullanılmıyor. Merkezi mesajlaşma sistemi kullanın.')
    return redirect('center:admin_message_list')

@staff_member_required
def delete_message(request, message_id):
    messages.error(request, 'Bu özellik artık kullanılmıyor. Merkezi mesajlaşma sistemi kullanın.')
    return redirect('center:admin_message_list')

@staff_member_required
def admin_message_detail(request, message_id):
    messages.error(request, 'Bu özellik artık kullanılmıyor. Merkezi mesajlaşma sistemi kullanın.')
    return redirect('center:admin_message_list')
    
    # Bu fonksiyon artık kullanılmıyor

@staff_member_required
def admin_center_list(request):
    """Tüm merkezlerin listesi ve yönetimi"""
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    from producer.models import ProducerNetwork
    
    # Merkezleri getir ve istatistiklerle birleştir
    centers = Center.objects.annotate(
        total_molds=Count('molds'),
        active_molds=Count('molds', filter=Q(molds__status__in=['waiting', 'processing'])),
        completed_molds=Count('molds', filter=Q(molds__status='completed')),
        delivered_molds=Count('molds', filter=Q(molds__status='delivered')),
        revision_molds=Count('molds', filter=Q(molds__status='revision'))
    ).prefetch_related('producer_networks__producer').order_by('-created_at')
    
    # Her merkez için aktif üretici ağını ekle
    for center in centers:
        center.active_producer = None
        active_network = center.producer_networks.filter(status='active').first()
        if active_network:
            center.active_producer = active_network.producer
    
    # Filtreleme
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    
    if status_filter == 'active':
        centers = centers.filter(is_active=True)
    elif status_filter == 'inactive':
        centers = centers.filter(is_active=False)
    
    if search_query:
        centers = centers.filter(
            Q(name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    return render(request, 'center/admin_center_list.html', {
        'centers': centers,
        'status_filter': status_filter,
        'search_query': search_query
    })

@staff_member_required
def admin_center_detail(request, center_id):
    """Admin center detail view - sadeleştirilmiş"""
    center = get_object_or_404(Center, id=center_id)
    
    # İstatistikler
    stats = {
        'total_molds': center.molds.count(),
        'completed_molds': center.molds.filter(status='delivered').count(),
        'active_molds': center.molds.exclude(status__in=['delivered', 'cancelled']).count(),
    }
    
    # Son kalıplar
    recent_molds = center.molds.order_by('-created_at')[:5]
    
    context = {
        'center': center,
        'stats': stats,
        'recent_molds': recent_molds,
    }
    
    return render(request, 'center/admin_center_detail.html', context)

@staff_member_required
def admin_center_toggle_status(request, center_id):
    """Toggle center active status"""
    if request.method == 'POST':
        center = get_object_or_404(Center, id=center_id)
        center.is_active = not center.is_active
        center.save()
        
        # Notification
        from notifications.signals import notify
        notify.send(
            sender=request.user,
            recipient=center.user,
            verb=f"Hesap {'Aktif' if center.is_active else 'Pasif'} Edildi",
            description=f"Hesabınız admin tarafından {'aktif' if center.is_active else 'pasif'} edildi."
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Merkez durumu {"aktif" if center.is_active else "pasif"} olarak güncellendi.'
        })
    
    return JsonResponse({'success': False, 'message': 'Geçersiz istek.'})

@staff_member_required
def admin_center_edit_user(request, center_id):
    """Edit center user information"""
    if request.method == 'POST':
        center = get_object_or_404(Center, id=center_id)
        
        try:
            # Update user info
            center.user.email = request.POST.get('email', center.user.email)
            center.user.save()
            
            # Update center info
            center.name = request.POST.get('center_name', center.name)
            center.phone = request.POST.get('phone', center.phone)
            center.mold_limit = int(request.POST.get('mold_limit', center.mold_limit))
            center.save()
            
            # Notification
            from notifications.signals import notify
            notify.send(
                sender=request.user,
                recipient=center.user,
                verb="Bilgiler Güncellendi",
                description="Hesap bilgileriniz admin tarafından güncellendi."
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Bilgiler başarıyla güncellendi.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Hata: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Geçersiz istek.'})

@staff_member_required
def admin_center_change_producer(request, center_id):
    """Change center's producer network"""
    if request.method == 'POST':
        center = get_object_or_404(Center, id=center_id)
        producer_id = request.POST.get('producer_id')
        
        if not producer_id:
            return JsonResponse({'success': False, 'message': 'Üretici seçilmedi.'})
        
        try:
            from producer.models import Producer, ProducerNetwork
            
            producer = get_object_or_404(Producer, id=producer_id)
            
            # Terminate existing networks
            center.producer_networks.filter(status='active').update(
                status='terminated',
                terminated_at=timezone.now(),
                termination_reason='Admin tarafından transfer edildi'
            )
            
            # Create new network
            assignment_reason = request.POST.get('assignment_reason', f'Admin tarafından {producer.company_name} üreticisine transfer edildi')
            network = ProducerNetwork.objects.create(
                producer=producer,
                center=center,
                status='active',
                joined_at=timezone.now(),
                activated_at=timezone.now(),
                auto_assigned=True,
                assignment_reason=assignment_reason
            )
            
            # Notifications
            from notifications.signals import notify
            notify.send(
                sender=request.user,
                recipient=center.user,
                verb="Üretici Ağı Değiştirildi",
                description=f"Üretici ağınız {producer.company_name} olarak değiştirildi."
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Merkez {producer.company_name} üreticisine başarıyla transfer edildi.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Transfer işlemi başarısız: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Geçersiz istek.'})

@staff_member_required
def admin_center_delete(request, center_id):
    """Delete center and user"""
    if request.method == 'POST':
        center = get_object_or_404(Center, id=center_id)
        
        # Check for active molds
        active_molds = center.molds.exclude(status__in=['delivered', 'cancelled']).count()
        if active_molds > 0:
            return JsonResponse({
                'success': False,
                'message': f'Bu merkezin {active_molds} aktif kalıbı bulunuyor. Önce kalıpları tamamlayın.'
            })
        
        try:
            center_name = center.name
            user = center.user
            
            # Terminate all networks
            center.producer_networks.update(
                status='terminated',
                terminated_at=timezone.now(),
                termination_reason='Merkez silindi'
            )
            
            # Delete center and user
            center.delete()
            user.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'{center_name} merkezi başarıyla silindi.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Silme işlemi başarısız: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Geçersiz istek.'})

@staff_member_required  
def get_producers_api(request):
    """API endpoint to get all producers for dropdowns"""
    try:
        from producer.models import Producer
        producers = Producer.objects.filter(is_active=True, is_verified=True)
        
        producer_list = []
        for producer in producers:
            producer_list.append({
                'id': producer.id,
                'company_name': producer.company_name,
            })
        
        return JsonResponse({
            'success': True,
            'producers': producer_list
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
@center_required
def network_management(request):
    """İşitme merkezi üretici ağ yönetimi"""
    center = request.user.center
    
    # Tüm network durumları
    all_networks = ProducerNetwork.objects.filter(center=center).select_related('producer')
    active_networks = all_networks.filter(status='active')
    pending_networks = all_networks.filter(status='pending')
    terminated_networks = all_networks.filter(status='terminated')
    
    # İstatistikler
    stats = {
        'total_networks': all_networks.count(),
        'active_count': active_networks.count(),
        'pending_count': pending_networks.count(),
        'terminated_count': terminated_networks.count(),
    }
    
    return render(request, 'center/network_management.html', {
        'center': center,
        'active_networks': active_networks,
        'pending_networks': pending_networks,
        'terminated_networks': terminated_networks,
        'stats': stats,
    })
