from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Center, CenterMessage
from .forms import CenterProfileForm, CenterMessageForm, CenterLimitForm
from .decorators import center_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import logout
from notifications.models import Notification
from django.db.models import Count, Q
from django.db import models
from datetime import datetime, timedelta
from mold.models import EarMold
from django.http import JsonResponse

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
    pending_molds = molds.filter(status='waiting').count()
    processing_molds = molds.filter(status='processing').count()
    completed_molds = molds.filter(status='completed').count()
    
    # Son 5 kalıbı al
    recent_molds = molds.order_by('-created_at')[:5]
    
    # Son 5 mesajı al
    recent_messages = center.received_messages.filter(is_archived=False).order_by('-created_at')[:5]
    
    # Kullanılan kalıp hakkını güncelle (kalan hakkı hesapla)
    used_molds = total_molds
    remaining_limit = max(0, center.mold_limit - used_molds)
    
    # Üretici ağ bilgileri
    from producer.models import ProducerNetwork
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
        'recent_messages': recent_messages,
        'used_molds': used_molds,
        'remaining_limit': remaining_limit,
        'producer_networks': producer_networks,
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

@login_required
def message_list(request):
    center = request.user.center
    folder = request.GET.get('folder', 'inbox')
    
    if folder == 'sent':
        messages = center.sent_messages.all().order_by('-created_at')
    elif folder == 'archived':
        messages = center.received_messages.filter(is_archived=True).order_by('-created_at')
    else:  # inbox
        messages = center.received_messages.filter(is_archived=False).order_by('-created_at')
    
    unread_count = center.received_messages.filter(is_read=False).count()
    
    return render(request, 'center/message_list.html', {
        'object_list': messages,
        'folder': folder,
        'unread_count': unread_count
    })

@login_required
@center_required
def send_message(request):
    # Admin kullanıcıya Center yoksa otomatik oluştur
    if (request.user.is_staff or request.user.is_superuser) and not hasattr(request.user, 'center'):
        Center.objects.create(user=request.user, name='Ana Merkez', address='-', phone='-')
    
    if request.method == 'POST':
        form = CenterMessageForm(request.POST, user=request.user)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user.center
            message.save()
            messages.success(request, 'Mesajınız gönderildi.')
            return redirect('center:message_list')
    else:
        form = CenterMessageForm(user=request.user)
    
    return render(request, 'center/send_message.html', {'form': form})

@login_required
@center_required
def message_detail(request, pk):
    message = get_object_or_404(CenterMessage, pk=pk)
    if message.receiver == request.user.center and not message.is_read:
        message.is_read = True
        message.save()
    return render(request, 'center/message_detail.html', {'message': message})

@login_required
@center_required
def message_archive(request, pk):
    message = get_object_or_404(CenterMessage, pk=pk, receiver=request.user.center)
    message.is_archived = True
    message.save()
    messages.success(request, 'Mesaj arşivlendi.')
    return redirect('center:message_list')

@login_required
@center_required
def message_unarchive(request, pk):
    message = get_object_or_404(CenterMessage, pk=pk, receiver=request.user.center)
    message.is_archived = False
    message.save()
    messages.success(request, 'Mesaj arşivden çıkarıldı.')
    return redirect('center:message_list')

@login_required
@center_required
def message_delete(request, pk):
    message = get_object_or_404(CenterMessage, pk=pk)
    # Sadece alıcı veya gönderen silebilir
    if message.receiver == request.user.center or message.sender == request.user.center:
        message.delete()
        messages.success(request, 'Mesaj silindi.')
    else:
        messages.error(request, 'Bu mesajı silme yetkiniz yok.')
    return redirect('center:message_list')

@login_required
@center_required
def message_quick_reply(request, pk):
    original_message = get_object_or_404(CenterMessage, pk=pk)
    
    if request.method == 'POST':
        message_text = request.POST.get('message')
        if message_text:
            # Yeni mesaj oluştur
            new_message = CenterMessage.objects.create(
                sender=request.user.center,
                receiver=original_message.sender,  # Orijinal mesajı gönderene yanıt
                subject=f"Re: {original_message.subject}",
                message=message_text
            )
            messages.success(request, 'Yanıtınız gönderildi.')
            return redirect('center:message_detail', pk=new_message.pk)
        else:
            messages.error(request, 'Mesaj içeriği boş olamaz.')
    
    return redirect('center:message_detail', pk=pk)

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
    from mold.models import EarMold
    from django.db.models import Count
    
    # İstatistikler
    total_centers = Center.objects.filter(is_active=True).count()
    total_molds = EarMold.objects.all().count()
    waiting_models = EarMold.objects.filter(status='waiting').count()
    in_progress = EarMold.objects.filter(status='processing').count()
    completed = EarMold.objects.filter(status='completed').count()
    delivered = EarMold.objects.filter(status='delivered').count()
    
    # Son mesajlar
    recent_messages = CenterMessage.objects.all().order_by('-created_at')[:5]
    
    # Merkez bazlı kalıp istatistikleri
    center_stats = Center.objects.annotate(
        total_molds=Count('molds'),
        waiting_molds=Count('molds', filter=models.Q(molds__status='waiting')),
        processing_molds=Count('molds', filter=models.Q(molds__status='processing')),
        completed_molds=Count('molds', filter=models.Q(molds__status='completed'))
    ).filter(is_active=True)
    
    return render(request, 'center/admin_dashboard.html', {
        'total_centers': total_centers,
        'total_molds': total_molds,
        'waiting_models': waiting_models,
        'in_progress': in_progress,
        'completed': completed,
        'delivered': delivered,
        'recent_messages': recent_messages,
        'center_stats': center_stats
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
        return JsonResponse({'success': True, 'message': 'Bildirim okundu olarak işaretlendi.'})
    
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
    from .models import CenterMessage, Center
    
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
    messages = CenterMessage.objects.all().order_by('-created_at')
    
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
    message = get_object_or_404(CenterMessage, id=message_id)
    message.is_archived = True
    message.save()
    messages.success(request, 'Mesaj başarıyla arşivlendi.')
    return redirect('center:admin_message_list')

@staff_member_required
def unarchive_message(request, message_id):
    message = get_object_or_404(CenterMessage, id=message_id)
    message.is_archived = False
    message.save()
    messages.success(request, 'Mesaj arşivden çıkarıldı.')
    return redirect('center:admin_message_list')

@staff_member_required
def delete_message(request, message_id):
    message = get_object_or_404(CenterMessage, id=message_id)
    message.delete()
    messages.success(request, 'Mesaj başarıyla silindi.')
    return redirect('center:admin_message_list')

@staff_member_required
def admin_message_detail(request, message_id):
    message = get_object_or_404(CenterMessage, id=message_id)
    
    # Mesajı okundu olarak işaretle
    if not message.is_read:
        message.is_read = True
        message.save()
    
    return render(request, 'center/message_detail.html', {
        'message': message
    })

@staff_member_required
def admin_center_list(request):
    """Tüm merkezlerin listesi ve yönetimi"""
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    # Merkezleri getir ve istatistiklerle birleştir
    centers = Center.objects.annotate(
        total_molds=Count('molds'),
        active_molds=Count('molds', filter=Q(molds__status__in=['waiting', 'processing'])),
        completed_molds=Count('molds', filter=Q(molds__status='completed')),
        delivered_molds=Count('molds', filter=Q(molds__status='delivered')),
        revision_molds=Count('molds', filter=Q(molds__status='revision'))
    ).order_by('-created_at')
    
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
def admin_center_detail(request, pk):
    """Merkez detay sayfası - tüm bilgiler"""
    from django.db.models import Count, Avg
    from datetime import datetime, timedelta
    
    center = get_object_or_404(Center, pk=pk)
    
    # Merkez istatistikleri
    molds = center.molds.all()
    total_molds = molds.count()
    completed_molds = molds.filter(status='completed').count()
    active_molds = molds.exclude(status__in=['completed', 'delivered']).count()
    
    # Kalite puanı ortalaması
    avg_quality = molds.filter(quality_score__isnull=False).aggregate(
        avg_score=Avg('quality_score')
    )['avg_score'] or 0
    
    # Bu ay kullanım
    now = datetime.now()
    monthly_usage = molds.filter(
        created_at__year=now.year,
        created_at__month=now.month
    ).count()
    
    # Kullanım oranı (toplam kalıp / mold_limit)
    usage_percentage = (total_molds / center.mold_limit * 100) if center.mold_limit > 0 else 0
    remaining_limit = max(0, center.mold_limit - total_molds)
    
    # Son kalıplar
    recent_molds = molds.order_by('-created_at')[:10]
    
    # İstatistikler
    stats = {
        'total_molds': total_molds,
        'completed_molds': completed_molds,
        'active_molds': active_molds,
        'avg_quality': avg_quality,
        'monthly_usage': monthly_usage,
        'usage_percentage': usage_percentage,
        'remaining_limit': remaining_limit,
    }
    
    return render(request, 'center/admin_center_detail.html', {
        'center': center,
        'stats': stats,
        'recent_molds': recent_molds,
    })

@staff_member_required
def admin_center_stats(request):
    """Merkez istatistikleri ve raporlar"""
    from django.db.models import Count, Avg, Sum
    from datetime import datetime, timedelta
    import json
    
    # Genel istatistikler
    stats = {
        'total_centers': Center.objects.count(),
        'active_centers': Center.objects.filter(is_active=True).count(),
        'total_molds': EarMold.objects.count(),
        'avg_quality': EarMold.objects.filter(quality_score__isnull=False).aggregate(
            avg=Avg('quality_score')
        )['avg'] or 0
    }
    
    # Kalıp durumları için grafik verileri
    status_data = []
    status_labels = []
    for status_choice in EarMold.STATUS_CHOICES:
        count = EarMold.objects.filter(status=status_choice[0]).count()
        if count > 0:
            status_data.append(count)
            status_labels.append(status_choice[1])
    
    # Kalıp tipleri için grafik verileri
    type_data = []
    type_labels = []
    for type_choice in EarMold.MOLD_TYPE_CHOICES:
        count = EarMold.objects.filter(mold_type=type_choice[0]).count()
        if count > 0:
            type_data.append(count)
            type_labels.append(type_choice[1])
    
    # Aylık trend verileri (son 6 ay)
    trend_data = []
    trend_labels = []
    now = datetime.now()
    for i in range(5, -1, -1):
        month_date = now - timedelta(days=30*i)
        count = EarMold.objects.filter(
            created_at__year=month_date.year,
            created_at__month=month_date.month
        ).count()
        trend_data.append(count)
        trend_labels.append(month_date.strftime('%m/%Y'))
    
    # En aktif merkezler
    top_active_centers = Center.objects.annotate(
        mold_count=Count('molds')
    ).order_by('-mold_count')[:5]
    
    # En kaliteli merkezler
    top_quality_centers = Center.objects.annotate(
        avg_quality=Avg('molds__quality_score')
    ).filter(avg_quality__isnull=False).order_by('-avg_quality')[:5]
    
    # Merkez performans tablosu
    center_performance = []
    for center in Center.objects.all():
        total_molds = center.molds.count()
        completed_molds = center.molds.filter(status='completed').count()
        avg_quality = center.molds.filter(quality_score__isnull=False).aggregate(
            avg=Avg('quality_score')
        )['avg']
        
        # Bu ay kullanım
        monthly_usage = center.molds.filter(
            created_at__year=now.year,
            created_at__month=now.month
        ).count()
        
        usage_percentage = (monthly_usage / center.mold_limit * 100) if center.mold_limit > 0 else 0
        
        # Son aktivite
        last_activity = center.molds.order_by('-created_at').first()
        
        center_performance.append({
            'name': center.name,
            'user': center.user,
            'is_active': center.is_active,
            'total_molds': total_molds,
            'completed_molds': completed_molds,
            'avg_quality': avg_quality,
            'monthly_usage': monthly_usage,
            'monthly_limit': center.mold_limit,
            'usage_percentage': usage_percentage,
            'last_activity': last_activity.created_at if last_activity else None
        })
    
    return render(request, 'center/admin_center_stats.html', {
        'stats': stats,
        'status_labels': json.dumps(status_labels),
        'status_data': json.dumps(status_data),
        'type_labels': json.dumps(type_labels),
        'type_data': json.dumps(type_data),
        'trend_labels': json.dumps(trend_labels),
        'trend_data': json.dumps(trend_data),
        'top_active_centers': top_active_centers,
        'top_quality_centers': top_quality_centers,
        'center_performance': center_performance,
    })

@staff_member_required
def admin_center_toggle_status(request, pk):
    """Merkez aktiflik durumunu değiştir"""
    if request.method == 'POST':
        center = get_object_or_404(Center, pk=pk)
        center.is_active = not center.is_active
        center.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Merkez {"aktifleştirildi" if center.is_active else "pasifleştirildi"}.',
            'is_active': center.is_active
        })
    
    return JsonResponse({'success': False, 'message': 'Geçersiz istek.'})

@staff_member_required
def admin_center_update_limit(request, pk):
    """Merkez kalıp limitini güncelle"""
    center = get_object_or_404(Center, pk=pk)
    
    if request.method == 'POST':
        # Hem monthly_limit hem de mold_limit parametrelerini kontrol et
        new_limit = request.POST.get('monthly_limit') or request.POST.get('mold_limit')
        
        if not new_limit:
            messages.error(request, 'Limit değeri boş olamaz.')
            return redirect('center:admin_center_detail', pk=center.pk)
        
        try:
            limit_value = int(new_limit)
            if limit_value < 1 or limit_value > 1000:
                messages.error(request, 'Limit değeri 1-1000 arasında olmalıdır.')
                return redirect('center:admin_center_detail', pk=center.pk)
            
            # mold_limit'i güncelle (temel kalıp limiti)
            center.mold_limit = limit_value
            center.save()
            messages.success(request, f'{center.name} merkezinin kalıp limiti {limit_value} olarak güncellendi.')
        except (ValueError, TypeError):
            messages.error(request, f'Geçersiz limit değeri: {new_limit}')
    
    return redirect('center:admin_center_detail', pk=center.pk)

@login_required
@center_required
def network_management(request):
    """Center için üretici ağ yönetimi"""
    center = request.user.center
    
    # Aktif ağlar
    from producer.models import ProducerNetwork
    active_networks = ProducerNetwork.objects.filter(
        center=center, 
        status='active'
    ).select_related('producer').order_by('-joined_at')
    
    # Bekleyen davetler
    pending_networks = ProducerNetwork.objects.filter(
        center=center,
        status='pending'
    ).select_related('producer').order_by('-joined_at')
    
    # Reddedilen/askıya alınan ağlar
    inactive_networks = ProducerNetwork.objects.filter(
        center=center,
        status__in=['suspended', 'terminated']
    ).select_related('producer').order_by('-last_activity')
    
    return render(request, 'center/network_management.html', {
        'center': center,
        'active_networks': active_networks,
        'pending_networks': pending_networks,
        'inactive_networks': inactive_networks,
    })

@login_required
@center_required
def network_leave(request, network_id):
    """Üretici ağından ayrıl"""
    from producer.models import ProducerNetwork
    
    if request.method == 'POST':
        network = get_object_or_404(ProducerNetwork, 
                                  id=network_id, 
                                  center=request.user.center)
        
        producer_name = network.producer.company_name
        network.status = 'terminated'
        network.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{producer_name} ağından ayrıldınız.'
        })
    
    return JsonResponse({'success': False, 'message': 'Geçersiz istek.'})
