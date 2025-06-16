from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from notifications.signals import notify
from .models import EarMold, Revision, ModeledMold, QualityCheck
from .forms import EarMoldForm, RevisionForm, ModeledMoldForm, QualityCheckForm
from center.decorators import center_required
from django.contrib.auth.decorators import permission_required

@login_required
@center_required
def mold_list(request):
    molds = request.user.center.molds.all()
    return render(request, 'mold/mold_list.html', {'molds': molds})

@login_required
@center_required
def mold_create(request):
    center = request.user.center
    
    # Kalıp hakkı kontrolü
    used_molds = center.molds.count()
    if used_molds >= center.mold_limit:
        messages.error(request, f'Kalıp hakkınız dolmuş. Maksimum {center.mold_limit} kalıp oluşturabilirsiniz.')
        return redirect('mold:mold_list')
    
    if request.method == 'POST':
        form = EarMoldForm(request.POST, request.FILES)
        if form.is_valid():
            # Tekrar kontrol et (eş zamanlı işlemler için)
            if center.molds.count() >= center.mold_limit:
                messages.error(request, f'Kalıp hakkınız dolmuş. Maksimum {center.mold_limit} kalıp oluşturabilirsiniz.')
                return redirect('mold:mold_list')
            
            mold = form.save(commit=False)
            mold.center = center
            mold.save()
            
            # Notify admin users
            admin_users = User.objects.filter(is_superuser=True)
            for admin in admin_users:
                notify.send(
                    sender=request.user,
                    recipient=admin,
                    verb='yeni bir kalıp yükledi',
                    action_object=mold,
                    description=f'{mold.patient_name} {mold.patient_surname} - {mold.get_mold_type_display()}'
                )
            
            messages.success(request, 'Kalıp başarıyla oluşturuldu.')
            return redirect('mold:mold_detail', pk=mold.pk)
    else:
        form = EarMoldForm()
    
    # Kalan hak bilgisini template'e gönder
    remaining_limit = center.mold_limit - used_molds
    
    return render(request, 'mold/mold_form.html', {
        'form': form,
        'remaining_limit': remaining_limit,
        'used_molds': used_molds,
        'total_limit': center.mold_limit
    })

@login_required
@center_required
def mold_detail(request, pk):
    mold = get_object_or_404(EarMold, pk=pk)
    if mold.center != request.user.center and not request.user.is_superuser:
        raise PermissionDenied
    model_form = ModeledMoldForm()
    
    return render(request, 'mold/mold_detail.html', {
        'mold': mold,
        'model_form': model_form
    })

@login_required
@center_required
def mold_edit(request, pk):
    mold = get_object_or_404(EarMold, pk=pk)
    if mold.center != request.user.center and not request.user.is_superuser:
        raise PermissionDenied
    
    if request.method == 'POST':
        form = EarMoldForm(request.POST, request.FILES, instance=mold)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kalıp başarıyla güncellendi.')
            return redirect('mold:mold_detail', pk=mold.pk)
    else:
        form = EarMoldForm(instance=mold)
    
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
            
            # Notify admin users
            admin_users = User.objects.filter(is_superuser=True)
            for admin in admin_users:
                notify.send(
                    sender=request.user,
                    recipient=admin,
                    verb='revizyon talep etti',
                    action_object=revision,
                    description=revision.description[:100] + '...' if len(revision.description) > 100 else revision.description
                )
            
            messages.success(request, 'Revizyon talebi başarıyla oluşturuldu.')
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
