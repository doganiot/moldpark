from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from notifications.signals import notify
from django.utils import timezone
from .models import EarMold, Revision, ModeledMold, QualityCheck, RevisionRequest, MoldEvaluation
from .forms import EarMoldForm, RevisionForm, ModeledMoldForm, QualityCheckForm, RevisionRequestForm, MoldEvaluationForm
from center.decorators import center_required
from django.contrib.auth.decorators import permission_required
from producer.models import ProducerNetwork, ProducerOrder
import uuid

@login_required
@center_required
def mold_list(request):
    molds = request.user.center.molds.all()
    return render(request, 'mold/mold_list.html', {'molds': molds})

@login_required
@center_required
def mold_create(request):
    center = request.user.center
    
    # DEBUG: Merkez bilgilerini logla
    print(f"DEBUG - Merkez: {center.name} (ID: {center.id})")
    print(f"DEBUG - Kullanıcı: {request.user.username} (ID: {request.user.id})")
    
    # Kalıp hakkı kontrolü
    used_molds = center.molds.count()
    print(f"DEBUG - Kullanılan kalıp sayısı: {used_molds}/{center.mold_limit}")
    
    if used_molds >= center.mold_limit:
        print(f"DEBUG - HATA: Kalıp limiti aşıldı!")
        messages.error(request, f'Kalıp hakkınız dolmuş. Maksimum {center.mold_limit} kalıp oluşturabilirsiniz.')
        return redirect('mold:mold_list')
    
    # Üretici ağ kontrolü
    active_networks = ProducerNetwork.objects.filter(
        center=center,
        status='active'
    )
    
    print(f"DEBUG - Aktif ağ sayısı: {active_networks.count()}")
    for network in active_networks:
        print(f"DEBUG - Ağ: {network.producer.company_name} (Durum: {network.status}, Doğrulanmış: {network.producer.is_verified})")
    
    if not active_networks.exists():
        print(f"DEBUG - HATA: Aktif üretici ağı bulunamadı!")
        
        # Tüm network durumlarını kontrol et
        all_networks = ProducerNetwork.objects.filter(center=center)
        print(f"DEBUG - Toplam network sayısı: {all_networks.count()}")
        for network in all_networks:
            print(f"DEBUG - Network: {network.producer.company_name} - Durum: {network.status}")
        
        messages.error(request, 'Kalıp siparişi verebilmek için bir üretici ağına katılmanız gerekiyor.')
        return redirect('center:network_management')
    
    if request.method == 'POST':
        print(f"DEBUG - POST isteği alındı")
        form = EarMoldForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            print(f"DEBUG - Form geçerli")
            # Tekrar kontrol et (eş zamanlı işlemler için)
            if center.molds.count() >= center.mold_limit:
                print(f"DEBUG - HATA: POST sırasında kalıp limiti aşıldı!")
                messages.error(request, f'Kalıp hakkınız dolmuş. Maksimum {center.mold_limit} kalıp oluşturabilirsiniz.')
                return redirect('mold:mold_list')
            
            mold = form.save(commit=False)
            mold.center = center
            mold.save()
            print(f"DEBUG - Kalıp oluşturuldu: {mold.id}")
            
            # ÜRETİCİ SİPARİŞİ OTOMATIK OLUŞTUR
            try:
                # Aktif ağlardan ilkini seç (gelecekte kullanıcı seçebilir)
                selected_network = active_networks.first()
                producer = selected_network.producer
                print(f"DEBUG - Seçilen üretici: {producer.company_name}")
                
                # Sipariş oluştur
                order = ProducerOrder.objects.create(
                    producer=producer,
                    center=center,
                    ear_mold=mold,
                    order_number=f'PRD-{uuid.uuid4().hex[:8].upper()}',
                    status='received',
                    priority=form.cleaned_data.get('priority', 'normal'),
                    producer_notes=form.cleaned_data.get('special_instructions', ''),
                    estimated_delivery=timezone.now() + timezone.timedelta(
                        days=7 if form.cleaned_data.get('priority') == 'normal' else 
                             4 if form.cleaned_data.get('priority') == 'high' else 2
                    )
                )
                print(f"DEBUG - Sipariş oluşturuldu: {order.order_number}")
                
                # Kalıp durumunu güncelle
                mold.status = 'processing'
                mold.save()
                print(f"DEBUG - Kalıp durumu güncellendi: {mold.status}")
                
                # ÜRETİCİYE BİLDİRİM GÖNDER
                notify.send(
                    sender=center,
                    recipient=producer.user,
                    verb='yeni kalıp siparişi gönderdi',
                    action_object=order,
                    description=f'{center.name} - {mold.patient_name} {mold.patient_surname} ({mold.get_mold_type_display()})',
                    target=mold
                )
                print(f"DEBUG - Üreticiye bildirim gönderildi")
                
                # MERKEZE ONAY BİLDİRİMİ
                notify.send(
                    sender=producer,
                    recipient=request.user,
                    verb='sipariş başarıyla oluşturuldu',
                    action_object=order,
                    description=f'Sipariş No: {order.order_number} - {producer.company_name} tarafından alındı.',
                    target=mold
                )
                print(f"DEBUG - Merkeze onay bildirimi gönderildi")
                
                messages.success(request, 
                    f'Kalıp başarıyla oluşturuldu ve {producer.company_name} firmasına sipariş gönderildi. '
                    f'Sipariş No: {order.order_number}'
                )
                
            except Exception as e:
                print(f"DEBUG - SİPARİŞ OLUŞTURMA HATASI: {str(e)}")
                # Sipariş oluşturulamazsa kalıbı beklemede bırak
                mold.status = 'waiting'
                mold.save()
                messages.warning(request, 
                    'Kalıp oluşturuldu ancak sipariş oluşturulurken bir hata oluştu. '
                    f'Lütfen yönetici ile iletişime geçin. Hata: {str(e)}'
                )
            
            # Admin bildirim
            admin_users = User.objects.filter(is_superuser=True)
            for admin in admin_users:
                notify.send(
                    sender=request.user,
                    recipient=admin,
                    verb='yeni bir kalıp yükledi',
                    action_object=mold,
                    description=f'{mold.patient_name} {mold.patient_surname} - {mold.get_mold_type_display()}'
                )
            print(f"DEBUG - Admin bildirimleri gönderildi")
            
            return redirect('mold:mold_detail', pk=mold.pk)
        else:
            print(f"DEBUG - Form geçersiz! Hatalar: {form.errors}")
            for field, errors in form.errors.items():
                print(f"DEBUG - {field}: {errors}")
    else:
        print(f"DEBUG - GET isteği - Form oluşturuluyor")
        form = EarMoldForm(user=request.user)
    
    # Kalan hak bilgisini template'e gönder
    remaining_limit = center.mold_limit - used_molds
    
    print(f"DEBUG - Template'e gönderilen veriler:")
    print(f"  - remaining_limit: {remaining_limit}")
    print(f"  - used_molds: {used_molds}")
    print(f"  - total_limit: {center.mold_limit}")
    print(f"  - active_networks: {active_networks.count()}")
    
    return render(request, 'mold/mold_form.html', {
        'form': form,
        'remaining_limit': remaining_limit,
        'used_molds': used_molds,
        'total_limit': center.mold_limit,
        'active_networks': active_networks
    })

@login_required
@center_required
def mold_detail(request, pk):
    mold = get_object_or_404(EarMold, pk=pk)
    if mold.center != request.user.center and not request.user.is_superuser:
        raise PermissionDenied
    
    # İlgili sipariş bilgilerini al
    producer_orders = mold.producer_orders.all().order_by('-created_at')
    model_form = ModeledMoldForm()
    
    # Onaylanmış kalıp dosyası var mı kontrol et
    has_approved_files = mold.modeled_files.filter(status='approved').exists()
    
    return render(request, 'mold/mold_detail.html', {
        'mold': mold,
        'model_form': model_form,
        'producer_orders': producer_orders,
        'has_approved_files': has_approved_files,
    })

@login_required
@center_required
def mold_edit(request, pk):
    mold = get_object_or_404(EarMold, pk=pk)
    if mold.center != request.user.center and not request.user.is_superuser:
        raise PermissionDenied
    
    if request.method == 'POST':
        form = EarMoldForm(request.POST, request.FILES, instance=mold, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kalıp başarıyla güncellendi.')
            return redirect('mold:mold_detail', pk=mold.pk)
    else:
        form = EarMoldForm(instance=mold, user=request.user)
    
    return render(request, 'mold/mold_form.html', {'form': form, 'mold': mold})

@login_required
@center_required
def mold_delete(request, pk):
    mold = get_object_or_404(EarMold, pk=pk)
    if mold.center != request.user.center and not request.user.is_superuser:
        raise PermissionDenied
    
    if request.method == 'POST':
        mold.delete()
        messages.success(request, 'Kalıp başarıyla silindi.')
        return redirect('mold:mold_list')
    
    return render(request, 'mold/mold_confirm_delete.html', {'mold': mold})

@login_required
def revision_create(request, pk):
    mold = get_object_or_404(EarMold, pk=pk)
    if mold.center != request.user.center and not request.user.is_superuser:
        raise PermissionDenied
    
    if request.method == 'POST':
        form = RevisionForm(request.POST)
        if form.is_valid():
            revision = form.save(commit=False)
            revision.mold = mold
            revision.save()
            
            # Update mold status
            mold.status = 'revision'
            mold.save()
            
            # İlgili üretici siparişlerini güncelle
            producer_orders = mold.producer_orders.filter(status__in=['received', 'designing', 'production'])
            for order in producer_orders:
                order.status = 'designing'  # Revizyon için tasarıma geri dön
                order.save()
                
                # ÜRETİCİYE REVİZYON BİLDİRİMİ
                notify.send(
                    sender=request.user,
                    recipient=order.producer.user,
                    verb='revizyon talep etti',
                    action_object=revision,
                    description=f'Sipariş: {order.order_number} - {revision.description[:100]}',
                    target=mold
                )
            
            # Admin bildirim
            admin_users = User.objects.filter(is_superuser=True)
            for admin in admin_users:
                notify.send(
                    sender=request.user,
                    recipient=admin,
                    verb='revizyon talep etti',
                    action_object=revision,
                    description=revision.description[:100] + '...' if len(revision.description) > 100 else revision.description
                )
            
            messages.success(request, 'Revizyon talebi başarıyla oluşturuldu ve üreticiye bildirildi.')
            return redirect('mold:mold_detail', pk=mold.pk)
    else:
        form = RevisionForm()
    
    return render(request, 'mold/revision_form.html', {'form': form, 'mold': mold})

@login_required
@permission_required('mold.add_modeledmold')
def upload_model(request, mold_id):
    mold = get_object_or_404(EarMold, pk=mold_id)
    
    if request.method == 'POST':
        form = ModeledMoldForm(request.POST, request.FILES)
        if form.is_valid():
            model = form.save(commit=False)
            model.ear_mold = mold
            model.save()
            
            messages.success(request, 'Model başarıyla yüklendi.')
            
            # Merkeze bildirim gönder
            notify.send(
                sender=request.user,
                recipient=mold.center.user,
                verb='yeni bir model yükledi',
                target=mold,
                description=f'{mold.patient_name} isimli hasta için yeni bir model yüklendi.'
            )
        else:
            messages.error(request, 'Model yüklenirken bir hata oluştu.')
    
    return redirect('mold:mold_detail', pk=mold_id)

@login_required
@permission_required('mold.delete_modeledmold')
def delete_modeled_mold(request, pk):
    model = get_object_or_404(ModeledMold, pk=pk)
    mold_id = model.ear_mold.id
    
    try:
        model.delete()
        messages.success(request, 'Model başarıyla silindi.')
    except Exception as e:
        messages.error(request, 'Model silinirken bir hata oluştu.')
    
    return redirect('mold:mold_detail', pk=mold_id)

@login_required
def quality_check(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied
    
    mold = get_object_or_404(EarMold, pk=pk)
    if request.method == 'POST':
        form = QualityCheckForm(request.POST)
        if form.is_valid():
            check = form.save(commit=False)
            check.mold = mold
            check.save()
            
            # Update mold quality score
            mold.quality_score = check.score
            mold.save()
            
            messages.success(request, 'Kalite kontrol başarıyla kaydedildi.')
            return redirect('mold:mold_detail', pk=mold.pk)
    else:
        form = QualityCheckForm()
    
    return render(request, 'mold/quality_form.html', {'form': form, 'mold': mold})


# YENİ VİEW'LAR - REVİZYON VE DEĞERLENDİRME SİSTEMİ

@login_required
@center_required
def revision_request_create(request, mold_id=None):
    """Revizyon talebi oluşturma"""
    mold = None
    if mold_id:
        mold = get_object_or_404(EarMold, pk=mold_id)
        # Sadece kalıbın sahibi revizyon talep edebilir
        if mold.center != request.user.center:
            raise PermissionDenied("Bu kalıp için revizyon talep etme yetkiniz yok.")
    
    if request.method == 'POST':
        form = RevisionRequestForm(request.POST, request.FILES, center=request.user.center)
        if form.is_valid():
            revision_request = form.save(commit=False)
            revision_request.center = request.user.center
            # modeled_mold seçildiğinde mold otomatik olarak belirlenir
            revision_request.mold = revision_request.modeled_mold.ear_mold
            revision_request.save()
            
            # Kalıp durumunu revizyon olarak güncelle
            mold = revision_request.mold
            mold.status = 'revision'
            mold.save()
            
            # Referans alınan kalıp dosyasını da revizyona düş
            revision_request.modeled_mold.status = 'waiting'  # Revizyon için beklemeye al
            revision_request.modeled_mold.save()
            
            # Admin'lere bildirim gönder
            admin_users = User.objects.filter(is_superuser=True)
            for admin in admin_users:
                notify.send(
                    sender=request.user,
                    recipient=admin,
                    verb='revizyon talebi oluşturdu',
                    action_object=revision_request,
                    description=f'{mold.patient_name} {mold.patient_surname} - {revision_request.get_revision_type_display()}',
                    target=mold
                )
            
            # İlgili üreticiye bildirim gönder
            producer_orders = mold.producer_orders.filter(status='delivered')
            for order in producer_orders:
                notify.send(
                    sender=request.user,
                    recipient=order.producer.user,
                    verb='revizyon talebi oluşturdu',
                    action_object=revision_request,
                    description=f'Sipariş: {order.order_number} - {revision_request.title}',
                    target=mold
                )
            
            messages.success(request, 'Revizyon talebiniz başarıyla oluşturuldu ve ilgili taraflara bildirildi.')
            return redirect('mold:mold_detail', pk=mold.pk)
    else:
        form = RevisionRequestForm(center=request.user.center)
    
    return render(request, 'mold/revision_request_form.html', {
        'form': form,
        'mold': mold
    })


@login_required
@center_required
def revision_request_list(request):
    """Revizyon talepleri listesi"""
    revision_requests = RevisionRequest.objects.filter(
        center=request.user.center
    ).order_by('-created_at')
    
    # Filtreleme
    status_filter = request.GET.get('status')
    if status_filter:
        revision_requests = revision_requests.filter(status=status_filter)
    
    return render(request, 'mold/revision_request_list.html', {
        'revision_requests': revision_requests,
        'status_filter': status_filter,
        'status_choices': RevisionRequest.STATUS_CHOICES
    })


@login_required
@center_required
def revision_request_detail(request, pk):
    """Revizyon talebi detayı"""
    revision_request = get_object_or_404(RevisionRequest, pk=pk)
    
    # Sadece kendi taleplerini görebilir
    if revision_request.center != request.user.center and not request.user.is_superuser:
        raise PermissionDenied
    
    return render(request, 'mold/revision_request_detail.html', {
        'revision_request': revision_request
    })


@login_required
@center_required
def mold_evaluation_create(request, mold_id):
    """Kalıp değerlendirmesi oluşturma"""
    mold = get_object_or_404(EarMold, pk=mold_id)
    
    # Sadece kalıbın sahibi değerlendirme yapabilir
    if mold.center != request.user.center:
        raise PermissionDenied("Bu kalıp için değerlendirme yapma yetkiniz yok.")
    
    # Kalıp teslim edilmiş olmalı
    if mold.status != 'delivered':
        messages.error(request, 'Değerlendirme sadece teslim edilmiş kalıplar için yapılabilir.')
        return redirect('mold:mold_detail', pk=mold_id)
    
    # Daha önce değerlendirme yapılmış mı kontrol et
    existing_evaluation = MoldEvaluation.objects.filter(
        mold=mold,
        center=request.user.center
    ).first()
    
    if existing_evaluation:
        messages.info(request, 'Bu kalıp için zaten bir değerlendirme yapmışsınız. Mevcut değerlendirmenizi güncelleyebilirsiniz.')
        return redirect('mold:mold_evaluation_edit', pk=existing_evaluation.pk)
    
    if request.method == 'POST':
        form = MoldEvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.mold = mold
            evaluation.center = request.user.center
            evaluation.save()
            
            # İlgili üreticiye bildirim gönder
            producer_orders = mold.producer_orders.filter(status='delivered')
            for order in producer_orders:
                notify.send(
                    sender=request.user,
                    recipient=order.producer.user,
                    verb='kalıp değerlendirmesi yaptı',
                    action_object=evaluation,
                    description=f'Kalite: {evaluation.quality_score}/10, Hız: {evaluation.speed_score}/10',
                    target=mold
                )
            
            # Admin'lere bildirim gönder
            admin_users = User.objects.filter(is_superuser=True)
            for admin in admin_users:
                notify.send(
                    sender=request.user,
                    recipient=admin,
                    verb='kalıp değerlendirmesi yaptı',
                    action_object=evaluation,
                    description=f'{mold.patient_name} {mold.patient_surname} - Genel: {evaluation.overall_satisfaction}/10',
                    target=mold
                )
            
            messages.success(request, 'Değerlendirmeniz başarıyla kaydedildi. Geri bildiriminiz için teşekkürler!')
            return redirect('mold:mold_detail', pk=mold_id)
    else:
        form = MoldEvaluationForm()
    
    return render(request, 'mold/mold_evaluation_form.html', {
        'form': form,
        'mold': mold
    })


@login_required
@center_required
def mold_evaluation_edit(request, pk):
    """Kalıp değerlendirmesi düzenleme"""
    evaluation = get_object_or_404(MoldEvaluation, pk=pk)
    
    # Sadece kendi değerlendirmelerini düzenleyebilir
    if evaluation.center != request.user.center:
        raise PermissionDenied("Bu değerlendirmeyi düzenleme yetkiniz yok.")
    
    if request.method == 'POST':
        form = MoldEvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Değerlendirmeniz başarıyla güncellendi.')
            return redirect('mold:mold_detail', pk=evaluation.mold.pk)
    else:
        form = MoldEvaluationForm(instance=evaluation)
    
    return render(request, 'mold/mold_evaluation_form.html', {
        'form': form,
        'mold': evaluation.mold,
        'evaluation': evaluation
    })


@login_required
@center_required
def mold_evaluation_list(request):
    """Kalıp değerlendirmeleri listesi"""
    evaluations = MoldEvaluation.objects.filter(
        center=request.user.center
    ).select_related('mold').order_by('-created_at')
    
    return render(request, 'mold/mold_evaluation_list.html', {
        'evaluations': evaluations
    })
