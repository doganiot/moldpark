from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from notifications.signals import notify
from core.utils import send_success_notification, send_order_notification, send_system_notification
from django.utils import timezone
from .models import EarMold, Revision, ModeledMold, QualityCheck, RevisionRequest, MoldEvaluation
from .forms import EarMoldForm, RevisionForm, ModeledMoldForm, QualityCheckForm, RevisionRequestForm, MoldEvaluationForm, PhysicalShipmentForm, TrackingUpdateForm
from center.decorators import center_required, subscription_required
from django.contrib.auth.decorators import permission_required
from producer.models import ProducerNetwork, ProducerOrder
import uuid
import logging

logger = logging.getLogger(__name__)

@login_required
@center_required
def mold_list(request):
    """Kalıp listesi görünümü"""
    try:
        center = request.user.center
        molds = center.molds.all().order_by('-created_at')
        
        # İstatistikler
        stats = {
            'total': molds.count(),
            'waiting': molds.filter(status='waiting').count(),
            'processing': molds.filter(status='processing').count(),
            'completed': molds.filter(status='completed').count(),
            'delivered': molds.filter(status='delivered').count(),
        }
        
        return render(request, 'mold/mold_list.html', {
            'molds': molds,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Mold list error: {e}")
        messages.error(request, 'Kalıp listesi yüklenirken bir hata oluştu.')
        return redirect('center:dashboard')

@login_required
@center_required
@subscription_required
def mold_create(request):
    """Yeni kalıp oluşturma - Tamamen yeniden yazıldı"""
    try:
        center = request.user.center
        
        # Abonelik kontrolü
        try:
            subscription = request.user.subscription
            if not subscription.can_create_model():
                messages.error(request, 
                    '❌ Kalıp kotanız doldu. Lütfen aboneliğinizi kontrol edin.')
                return redirect('core:subscription_dashboard')
        except Exception as e:
            logger.error(f"Subscription check error: {e}")
            messages.error(request, 
                '⚠️ Abonelik bilgileriniz kontrol edilemiyor. Lütfen tekrar deneyin.')
            return redirect('core:subscription_dashboard')
        
        # Üretici ağ kontrolü
        active_networks = ProducerNetwork.objects.filter(
            center=center,
            status='active'
        )
        
        if not active_networks.exists():
            messages.error(request, 
                '🏭 Kalıp siparişi verebilmek için bir üretici ağına katılmanız gerekiyor.')
            return redirect('center:network_management')
        
        if request.method == 'POST':
            form = EarMoldForm(request.POST, request.FILES, user=request.user)
            
            if form.is_valid():
                try:
                    # Kalıbı oluştur
                    mold = form.save()
                    
                    # Abonelik kotasını kullan
                    subscription.use_model_quota()
                    
                    # Üretici seç (şimdilik ilk aktif ağ)
                    selected_network = active_networks.first()
                    producer = selected_network.producer
                    
                    # Sipariş oluştur
                    order = ProducerOrder.objects.create(
                        producer=producer,
                        center=center,
                        ear_mold=mold,
                        order_number=f'PRD-{uuid.uuid4().hex[:8].upper()}',
                        status='received',
                        priority=mold.priority,
                        producer_notes=mold.special_instructions,
                        estimated_delivery=timezone.now() + timezone.timedelta(
                            days=7 if mold.priority == 'normal' else 
                                 4 if mold.priority == 'high' else 2
                        )
                    )
                    
                    # Kalıp durumunu güncelle
                    mold.status = 'processing'
                    mold.save()
                    
                    # Bildirimler gönder
                    try:
                        # Üreticiye bildirim
                        send_order_notification(
                            producer.user,
                            'Yeni Kalıp Siparişi',
                            f'{center.name} merkezinden {mold.patient_name} {mold.patient_surname} '
                            f'hastası için {mold.get_mold_type_display()} kalıbı siparişi aldınız. '
                            f'Sipariş No: {order.order_number}',
                            related_url=f'/producer/orders/{order.id}/',
                            order_id=order.id
                        )
                        
                        # Merkeze başarı bildirimi
                        send_success_notification(
                            request.user,
                            'Kalıp Siparişi Oluşturuldu',
                            f'Kalıbınız {producer.company_name} firmasına gönderildi. '
                            f'Sipariş No: {order.order_number}. '
                            f'Tahmini teslimat: {order.estimated_delivery.strftime("%d.%m.%Y")}',
                            related_url=f'/mold/{mold.id}/'
                        )
                        
                        # Admin'lere sistem bildirimi
                        admin_users = User.objects.filter(is_superuser=True)
                        for admin in admin_users:
                            send_system_notification(
                                admin,
                                'Yeni Kalıp Siparişi',
                                f'{center.name} merkezi tarafından {mold.get_mold_type_display()} '
                                f'kalıbı oluşturuldu ve {producer.company_name} firmasına sipariş verildi.',
                                related_url='/admin-panel/'
                            )
                    except Exception as e:
                        logger.error(f"Notification error: {e}")
                        # Bildirim hatası kalıp oluşturmayı etkilemesin
                    
                    # Kota uyarıları
                    remaining_models = subscription.get_remaining_models()
                    if subscription.plan.plan_type == 'trial' and remaining_models <= 2:
                        if remaining_models == 0:
                            messages.warning(request, 
                                '🎯 Deneme paketiniz tükendi! '
                                'Daha fazla kalıp oluşturmak için bir abonelik planı seçin.')
                        else:
                            messages.info(request, 
                                f'📊 Deneme paketinizde {remaining_models} kalıp hakkınız kaldı.')
                    
                    # Başarı mesajı
                    if mold.is_physical_shipment:
                        messages.success(request, 
                            f'✅ Fiziksel kalıp siparişi başarıyla oluşturuldu! '
                            f'Kalıbı {producer.company_name} firmasına kargo ile gönderebilirsiniz. '
                            f'Sipariş No: {order.order_number}')
                    else:
                        messages.success(request, 
                            f'✅ Dijital kalıp siparişi başarıyla oluşturuldu! '
                            f'Dosyanız {producer.company_name} firmasına gönderildi. '
                            f'Sipariş No: {order.order_number}')
                    
                    return redirect('mold:mold_detail', pk=mold.pk)
                    
                except Exception as e:
                    logger.error(f"Mold creation error: {e}")
                    messages.error(request, 
                        '❌ Kalıp oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.')
                    
            else:
                # Form hataları
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        else:
            form = EarMoldForm(user=request.user)
        
        # Template context
        context = {
            'form': form,
            'active_networks': active_networks,
            'subscription': subscription,
            'remaining_limit': subscription.get_remaining_models() if subscription else 0,
        }
        
        return render(request, 'mold/mold_form.html', context)
        
    except Exception as e:
        logger.error(f"Mold create view error: {e}")
        messages.error(request, 'Kalıp oluşturma sayfası yüklenirken bir hata oluştu.')
        return redirect('center:dashboard')

@login_required
@center_required
def mold_detail(request, pk):
    """Kalıp detay görünümü"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)
        
        # Yetki kontrolü
        if mold.center != request.user.center and not request.user.is_superuser:
            raise PermissionDenied
        
        # İlgili veriler
        producer_orders = mold.producer_orders.all().order_by('-created_at')
        modeled_files = mold.modeled_files.all().order_by('-created_at')
        evaluations = mold.evaluations.all().order_by('-created_at')
        revision_requests = RevisionRequest.objects.filter(
            modeled_mold__ear_mold=mold
        ).order_by('-created_at')
        
        # Delivery address
        delivery_address = mold.get_delivery_address()
        
        # Template context
        context = {
            'mold': mold,
            'producer_orders': producer_orders,
            'modeled_files': modeled_files,
            'evaluations': evaluations,
            'revision_requests': revision_requests,
            'delivery_address': delivery_address,
            'can_evaluate': modeled_files.filter(status='approved').exists(),
            'has_approved_files': modeled_files.filter(status='approved').exists(),
            'can_request_revision': mold.status in ['delivered', 'completed'] and modeled_files.filter(status='approved').exists(),
            'has_pending_revision': revision_requests.filter(status__in=['pending', 'accepted', 'in_progress']).exists(),
        }
        
        return render(request, 'mold/mold_detail.html', context)
        
    except PermissionDenied:
        messages.error(request, 'Bu kalıbı görüntüleme yetkiniz yok.')
        return redirect('mold:mold_list')
    except Exception as e:
        logger.error(f"Mold detail error: {e}")
        messages.error(request, 'Kalıp detayları yüklenirken bir hata oluştu.')
        return redirect('mold:mold_list')

@login_required
@center_required
def mold_edit(request, pk):
    """Kalıp düzenleme görünümü"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)
        
        # Yetki kontrolü
        if mold.center != request.user.center and not request.user.is_superuser:
            raise PermissionDenied
        
        # Düzenleme sınırlamaları
        if mold.status in ['completed', 'delivered']:
            messages.warning(request, 
                'Tamamlanmış kalıplar düzenlenemez. Revizyon talebi oluşturabilirsiniz.')
            return redirect('mold:mold_detail', pk=mold.pk)
        
        if request.method == 'POST':
            form = EarMoldForm(request.POST, request.FILES, instance=mold, user=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Kalıp başarıyla güncellendi.')
                return redirect('mold:mold_detail', pk=mold.pk)
        else:
            form = EarMoldForm(instance=mold, user=request.user)
        
        return render(request, 'mold/mold_form.html', {
            'form': form, 
            'mold': mold,
            'is_edit': True
        })
        
    except PermissionDenied:
        messages.error(request, 'Bu kalıbı düzenleme yetkiniz yok.')
        return redirect('mold:mold_list')
    except Exception as e:
        logger.error(f"Mold edit error: {e}")
        messages.error(request, 'Kalıp düzenleme sayfası yüklenirken bir hata oluştu.')
        return redirect('mold:mold_list')

@login_required
@center_required  
def mold_delete(request, pk):
    """Kalıp silme görünümü"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)
        
        # Yetki kontrolü
        if mold.center != request.user.center and not request.user.is_superuser:
            raise PermissionDenied
        
        # Silme sınırlamaları
        if mold.status in ['processing', 'completed', 'delivered']:
            messages.error(request, 
                'İşlemde olan veya tamamlanmış kalıplar silinemez.')
            return redirect('mold:mold_detail', pk=mold.pk)
        
        if request.method == 'POST':
            patient_name = f"{mold.patient_name} {mold.patient_surname}"
            mold.delete()
            messages.success(request, f'{patient_name} hastasının kalıbı başarıyla silindi.')
            return redirect('mold:mold_list')
        
        return render(request, 'mold/mold_confirm_delete.html', {'mold': mold})
        
    except PermissionDenied:
        messages.error(request, 'Bu kalıbı silme yetkiniz yok.')
        return redirect('mold:mold_list')
    except Exception as e:
        logger.error(f"Mold delete error: {e}")
        messages.error(request, 'Kalıp silme işleminde bir hata oluştu.')
        return redirect('mold:mold_list')

@login_required
@center_required
def revision_create(request, pk):
    """Revizyon oluşturma view'ı"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)
        
        # Yetki kontrolü
        if mold.center != request.user.center and not request.user.is_superuser:
            raise PermissionDenied
            
        if request.method == 'POST':
            form = RevisionForm(request.POST, request.FILES)
            if form.is_valid():
                revision = form.save(commit=False)
                revision.mold = mold
                revision.created_by = request.user
                revision.save()
                
                messages.success(request, 'Revizyon talebi başarıyla oluşturuldu.')
                return redirect('mold:mold_detail', pk=mold.pk)
        else:
            form = RevisionForm()
            
        return render(request, 'mold/revision_form.html', {
            'form': form,
            'mold': mold
        })
        
    except PermissionDenied:
        messages.error(request, 'Bu kalıp için revizyon oluşturma yetkiniz yok.')
        return redirect('mold:mold_list')
    except Exception as e:
        logger.error(f"Revision create error: {e}")
        messages.error(request, 'Revizyon oluşturulurken bir hata oluştu.')
        return redirect('mold:mold_list')

@login_required
@center_required
def quality_check(request, pk):
    """Kalite kontrolü view'ı"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)
        
        # Yetki kontrolü
        if mold.center != request.user.center and not request.user.is_superuser:
            raise PermissionDenied
            
        if request.method == 'POST':
            form = QualityCheckForm(request.POST)
            if form.is_valid():
                quality_check = form.save(commit=False)
                quality_check.mold = mold
                quality_check.checked_by = request.user
                quality_check.save()
                
                messages.success(request, 'Kalite kontrolü başarıyla kaydedildi.')
                return redirect('mold:mold_detail', pk=mold.pk)
        else:
            form = QualityCheckForm()
            
        return render(request, 'mold/quality_check.html', {
            'form': form,
            'mold': mold
        })
        
    except PermissionDenied:
        messages.error(request, 'Bu kalıp için kalite kontrolü yetkiniz yok.')
        return redirect('mold:mold_list')
    except Exception as e:
        logger.error(f"Quality check error: {e}")
        messages.error(request, 'Kalite kontrolü yapılırken bir hata oluştu.')
        return redirect('mold:mold_list')

@login_required
@center_required
def physical_shipment_detail(request, pk):
    """Fiziksel kalıp gönderim detayı view'ı"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)
        
        # Yetki kontrolü
        if mold.center != request.user.center and not request.user.is_superuser:
            raise PermissionDenied
            
        if not mold.is_physical_shipment:
            messages.error(request, 'Bu kalıp fiziksel gönderim türünde değil.')
            return redirect('mold:mold_detail', pk=mold.pk)
            
        # Üretici bilgisi
        active_orders = mold.producer_orders.filter(status__in=['received', 'processing']).first()
        producer = active_orders.producer if active_orders else None
        
        return render(request, 'mold/physical_shipment_detail.html', {
            'mold': mold,
            'producer': producer,
            'active_order': active_orders
        })
        
    except PermissionDenied:
        messages.error(request, 'Bu kalıp detaylarını görüntüleme yetkiniz yok.')
        return redirect('mold:mold_list')
    except Exception as e:
        logger.error(f"Physical shipment detail error: {e}")
        messages.error(request, 'Fiziksel gönderim detayları yüklenirken bir hata oluştu.')
        return redirect('mold:mold_list')

@login_required
@center_required
def update_tracking(request, pk):
    """Kargo takip güncelleme view'ı"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)
        
        # Yetki kontrolü
        if mold.center != request.user.center and not request.user.is_superuser:
            raise PermissionDenied
            
        if not mold.is_physical_shipment:
            messages.error(request, 'Bu kalıp fiziksel gönderim türünde değil.')
            return redirect('mold:mold_detail', pk=mold.pk)
            
        if request.method == 'POST':
            form = TrackingUpdateForm(request.POST, instance=mold)
            if form.is_valid():
                mold = form.save()
                
                # Kargo durumu güncelleme bildirimi
                try:
                    # Üretici bilgisi
                    active_order = mold.producer_orders.filter(status__in=['received', 'processing']).first()
                    if active_order:
                        producer = active_order.producer
                        
                        # Üreticiye bildirim
                        send_order_notification(
                            producer.user,
                            'Kargo Takip Güncellendi',
                            f'{mold.center.name} merkezi tarafından {mold.tracking_number} takip numaralı '
                            f'kargo bilgileri güncellendi. Durum: {mold.get_shipment_status_display()}',
                            related_url=f'/producer/orders/{active_order.id}/'
                        )
                        
                except Exception as e:
                    logger.error(f"Tracking notification error: {e}")
                
                messages.success(request, 'Kargo takip bilgileri başarıyla güncellendi.')
                return redirect('mold:physical_shipment_detail', pk=mold.pk)
        else:
            form = TrackingUpdateForm(instance=mold)
            
        return render(request, 'mold/tracking_update.html', {
            'form': form,
            'mold': mold
        })
        
    except PermissionDenied:
        messages.error(request, 'Bu kalıp için kargo takip güncelleme yetkiniz yok.')
        return redirect('mold:mold_list')
    except Exception as e:
        logger.error(f"Tracking update error: {e}")
        messages.error(request, 'Kargo takip güncelleme yapılırken bir hata oluştu.')
        return redirect('mold:mold_list')

@login_required
@center_required
def revision_request_create(request, mold_id=None):
    """Revizyon talebi oluşturma view'ı"""
    try:
        mold = None
        selected_modeled_mold = None
        
        if mold_id:
            mold = get_object_or_404(EarMold, pk=mold_id)
            
            # Yetki kontrolü
            if mold.center != request.user.center and not request.user.is_superuser:
                raise PermissionDenied
                
            # Revizyon talebi oluşturma sınırlamaları
            if mold.status not in ['delivered', 'completed']:
                messages.error(request, 'Sadece teslim edilmiş kalıplar için revizyon talebi oluşturabilirsiniz.')
                return redirect('mold:mold_detail', pk=mold.pk)
            
            # Bu kalıp için onaylanmış modeled mold var mı?
            approved_models = mold.modeled_files.filter(status='approved')
            if not approved_models.exists():
                messages.error(request, 'Bu kalıp için onaylanmış model dosyası bulunamadı.')
                return redirect('mold:mold_detail', pk=mold.pk)
            
            # İlk onaylanmış modeli seç
            selected_modeled_mold = approved_models.first()
                
        if request.method == 'POST':
            form = RevisionRequestForm(request.POST, request.FILES, user=request.user)
            if form.is_valid():
                revision_request = form.save(commit=False)
                revision_request.center = request.user.center
                revision_request.save()
                
                # Revizyon talebi bildirimi
                try:
                    # Üreticiye bildirim
                    ear_mold = revision_request.modeled_mold.ear_mold
                    producer_orders = ear_mold.producer_orders.filter(status='delivered').first()
                    
                    if producer_orders:
                        producer = producer_orders.producer
                        send_order_notification(
                            producer.user,
                            'Yeni Revizyon Talebi',
                            f'{request.user.center.name} merkezi tarafından "{ear_mold.patient_name} {ear_mold.patient_surname}" '
                            f'hastasının kalıbı için revizyon talebi oluşturuldu. '
                            f'Talep türü: {revision_request.get_revision_type_display()}',
                            related_url=f'/producer/revisions/{revision_request.id}/'
                        )
                    
                    # Admin'lere bildirim
                    admin_users = User.objects.filter(is_superuser=True)
                    for admin in admin_users:
                        send_system_notification(
                            admin,
                            'Yeni Revizyon Talebi',
                            f'{request.user.center.name} merkezi tarafından "{ear_mold.patient_name} {ear_mold.patient_surname}" '
                            f'hastasının kalıbı için revizyon talebi oluşturuldu.',
                            related_url='/admin-panel/'
                        )
                        
                except Exception as e:
                    logger.error(f"Revision request notification error: {e}")
                
                messages.success(request, 
                    f'✅ Revizyon talebi başarıyla oluşturuldu! '
                    f'Talep türü: {revision_request.get_revision_type_display()}')
                
                # Kalıp detayına yönlendir
                if mold:
                    return redirect('mold:mold_detail', pk=mold.pk)
                else:
                    return redirect('mold:revision_request_detail', pk=revision_request.pk)
        else:
            initial_data = {}
            if selected_modeled_mold:
                initial_data['modeled_mold'] = selected_modeled_mold
            
            form = RevisionRequestForm(user=request.user, initial=initial_data)
            
            # Belirli kalıp için revizyon talep ediyorsa, sadece o kalıbın modellerini göster
            if mold:
                form.fields['modeled_mold'].queryset = mold.modeled_files.filter(status='approved')
                form.fields['modeled_mold'].help_text = f'{mold.patient_name} {mold.patient_surname} hastasının kalıbı için hangi model dosyasında revizyon istiyorsunuz?'
            
        return render(request, 'mold/revision_request_form.html', {
            'form': form,
            'mold': mold,
            'selected_modeled_mold': selected_modeled_mold
        })
        
    except PermissionDenied:
        messages.error(request, 'Bu kalıp için revizyon talebi oluşturma yetkiniz yok.')
        return redirect('mold:mold_list')
    except Exception as e:
        logger.error(f"Revision request create error: {e}")
        messages.error(request, 'Revizyon talebi oluşturulurken bir hata oluştu.')
        return redirect('mold:mold_list')

@login_required
@center_required
def revision_request_list(request):
    """Revizyon talepleri listesi view'ı"""
    try:
        center = request.user.center
        revision_requests = RevisionRequest.objects.filter(
            center=center
        ).select_related('mold', 'modeled_mold').order_by('-created_at')
        
        # Filtreleme
        status = request.GET.get('status')
        if status:
            revision_requests = revision_requests.filter(status=status)
            
        revision_type = request.GET.get('revision_type')
        if revision_type:
            revision_requests = revision_requests.filter(revision_type=revision_type)
            
        priority = request.GET.get('priority')
        if priority:
            revision_requests = revision_requests.filter(priority=priority)
        
        # İstatistikler
        all_requests = RevisionRequest.objects.filter(center=center)
        stats = {
            'pending': all_requests.filter(status='pending').count(),
            'accepted': all_requests.filter(status='accepted').count(),
            'in_progress': all_requests.filter(status='in_progress').count(),
            'completed': all_requests.filter(status='completed').count(),
        }
        
        return render(request, 'mold/revision_request_list.html', {
            'revision_requests': revision_requests,
            'stats': stats,
        })
        
    except Exception as e:
        logger.error(f"Revision request list error: {e}")
        messages.error(request, 'Revizyon talepleri yüklenirken bir hata oluştu.')
        return redirect('center:dashboard')

@login_required
@center_required
def revision_request_detail(request, pk):
    """Revizyon talebi detay view'ı"""
    try:
        revision_request = get_object_or_404(RevisionRequest, pk=pk)
        
        # Yetki kontrolü
        if revision_request.center != request.user.center and not request.user.is_superuser:
            raise PermissionDenied
            
        return render(request, 'mold/revision_request_detail.html', {
            'revision_request': revision_request
        })
        
    except PermissionDenied:
        messages.error(request, 'Bu revizyon talebi detaylarını görüntüleme yetkiniz yok.')
        return redirect('mold:revision_request_list')
    except Exception as e:
        logger.error(f"Revision request detail error: {e}")
        messages.error(request, 'Revizyon talebi detayları yüklenirken bir hata oluştu.')
        return redirect('mold:revision_request_list')

@login_required
@center_required
def mold_evaluation_create(request, mold_id):
    """Kalıp değerlendirme oluşturma view'ı"""
    try:
        mold = get_object_or_404(EarMold, pk=mold_id)
        
        # Yetki kontrolü
        if mold.center != request.user.center and not request.user.is_superuser:
            raise PermissionDenied
            
        # Değerlendirme sınırlamaları
        if mold.status not in ['delivered', 'completed']:
            messages.error(request, 'Sadece teslim edilmiş kalıplar için değerlendirme yapabilirsiniz.')
            return redirect('mold:mold_detail', pk=mold.pk)
            
        # Zaten değerlendirme yapılmış mı?
        existing_evaluation = MoldEvaluation.objects.filter(
            mold=mold,
            center=request.user.center
        ).first()
        
        if existing_evaluation:
            messages.info(request, 'Bu kalıp için zaten değerlendirme yapılmış.')
            return redirect('mold:mold_detail', pk=mold.pk)
            
        if request.method == 'POST':
            form = MoldEvaluationForm(request.POST)
            if form.is_valid():
                evaluation = form.save(commit=False)
                evaluation.mold = mold
                evaluation.center = request.user.center
                evaluation.save()
                
                messages.success(request, 'Kalıp değerlendirmesi başarıyla kaydedildi.')
                return redirect('mold:mold_detail', pk=mold.pk)
        else:
            form = MoldEvaluationForm()
            
        return render(request, 'mold/mold_evaluation_form.html', {
            'form': form,
            'mold': mold
        })
        
    except PermissionDenied:
        messages.error(request, 'Bu kalıp için değerlendirme yapma yetkiniz yok.')
        return redirect('mold:mold_list')
    except Exception as e:
        logger.error(f"Mold evaluation create error: {e}")
        messages.error(request, 'Kalıp değerlendirmesi yapılırken bir hata oluştu.')
        return redirect('mold:mold_list')

@login_required
@center_required
def mold_evaluation_edit(request, pk):
    """Kalıp değerlendirme düzenleme view'ı"""
    try:
        evaluation = get_object_or_404(MoldEvaluation, pk=pk)
        
        # Yetki kontrolü
        if evaluation.center != request.user.center and not request.user.is_superuser:
            raise PermissionDenied
            
        if request.method == 'POST':
            form = MoldEvaluationForm(request.POST, instance=evaluation)
            if form.is_valid():
                form.save()
                
                messages.success(request, 'Kalıp değerlendirmesi başarıyla güncellendi.')
                return redirect('mold:mold_detail', pk=evaluation.mold.pk)
        else:
            form = MoldEvaluationForm(instance=evaluation)
            
        return render(request, 'mold/mold_evaluation_form.html', {
            'form': form,
            'evaluation': evaluation,
            'mold': evaluation.mold
        })
        
    except PermissionDenied:
        messages.error(request, 'Bu değerlendirmeyi düzenleme yetkiniz yok.')
        return redirect('mold:mold_list')
    except Exception as e:
        logger.error(f"Mold evaluation edit error: {e}")
        messages.error(request, 'Kalıp değerlendirmesi düzenlenirken bir hata oluştu.')
        return redirect('mold:mold_list')

@login_required
@center_required
def mold_evaluation_list(request):
    """Kalıp değerlendirmeleri listesi view'ı"""
    try:
        center = request.user.center
        evaluations = MoldEvaluation.objects.filter(
            center=center
        ).order_by('-created_at')
        
        return render(request, 'mold/mold_evaluation_list.html', {
            'evaluations': evaluations
        })
        
    except Exception as e:
        logger.error(f"Mold evaluation list error: {e}")
        messages.error(request, 'Kalıp değerlendirmeleri yüklenirken bir hata oluştu.')
        return redirect('center:dashboard')

@login_required
def upload_model(request, mold_id):
    """Model dosyası yükleme view'ı - Üreticiler için"""
    try:
        mold = get_object_or_404(EarMold, pk=mold_id)
        
        # Sadece üreticiler kullanabilir
        if not hasattr(request.user, 'producer'):
            messages.error(request, 'Bu işlem sadece üreticiler tarafından yapılabilir.')
            return redirect('core:home')
            
        # Model yükleme işlemi
        if request.method == 'POST':
            form = ModeledMoldForm(request.POST, request.FILES)
            if form.is_valid():
                modeled_mold = form.save(commit=False)
                modeled_mold.ear_mold = mold
                modeled_mold.producer = request.user.producer
                modeled_mold.save()
                
                messages.success(request, 'Model dosyası başarıyla yüklendi.')
                return redirect('producer:mold_detail', pk=mold.pk)
        else:
            form = ModeledMoldForm()
            
        return render(request, 'mold/upload_model.html', {
            'form': form,
            'mold': mold
        })
        
    except Exception as e:
        logger.error(f"Upload model error: {e}")
        messages.error(request, 'Model dosyası yüklenirken bir hata oluştu.')
        return redirect('producer:dashboard')

@login_required
def delete_modeled_mold(request, pk):
    """Model dosyası silme view'ı - Üreticiler için"""
    try:
        modeled_mold = get_object_or_404(ModeledMold, pk=pk)
        
        # Sadece üretici kendi modelini silebilir
        if not hasattr(request.user, 'producer') or modeled_mold.producer != request.user.producer:
            messages.error(request, 'Bu modeli silme yetkiniz yok.')
            return redirect('core:home')
            
        if request.method == 'POST':
            mold_id = modeled_mold.ear_mold.id
            modeled_mold.delete()
            
            messages.success(request, 'Model dosyası başarıyla silindi.')
            return redirect('producer:mold_detail', pk=mold_id)
            
        return render(request, 'mold/delete_modeled_mold.html', {
            'modeled_mold': modeled_mold
        })
        
    except Exception as e:
        logger.error(f"Delete modeled mold error: {e}")
        messages.error(request, 'Model dosyası silinirken bir hata oluştu.')
        return redirect('producer:dashboard')
