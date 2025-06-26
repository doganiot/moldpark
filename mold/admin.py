from django.contrib import admin
from django.http import JsonResponse
from django.utils import timezone
from notifications.signals import notify
from django.contrib.auth.models import User
from .models import EarMold, Revision, ModeledMold, QualityCheck, RevisionRequest, MoldEvaluation

@admin.register(EarMold)
class EarMoldAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'patient_surname', 'center', 'mold_type', 'is_physical_shipment', 'status', 'shipment_status', 'priority', 'created_at')
    list_filter = ('status', 'mold_type', 'center', 'is_physical_shipment', 'shipment_status', 'priority', 'created_at')
    search_fields = ('patient_name', 'patient_surname', 'center__name', 'tracking_number')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Hasta Bilgileri', {
            'fields': ('patient_name', 'patient_surname', 'patient_age', 'patient_gender')
        }),
        ('Kalıp Bilgileri', {
            'fields': ('center', 'mold_type', 'vent_diameter', 'scan_file', 'notes', 'priority', 'special_instructions')
        }),
        ('Sipariş Türü', {
            'fields': ('is_physical_shipment',)
        }),
        ('Fiziksel Gönderim Bilgileri', {
            'fields': ('carrier_company', 'tracking_number', 'shipment_date', 'shipment_status', 'estimated_delivery', 'shipment_notes'),
            'classes': ('collapse',),
            'description': 'Bu bölüm sadece fiziksel kalıp gönderimi için kullanılır.'
        }),
        ('Durum Bilgileri', {
            'fields': ('status', 'quality_score')
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_fieldsets(self, request, obj=None):
        """Fiziksel gönderim değilse kargo alanlarını gizle"""
        fieldsets = super().get_fieldsets(request, obj)
        if obj and not obj.is_physical_shipment:
            # Fiziksel gönderim alanlarını gizle
            fieldsets = [fs for fs in fieldsets if fs[0] != 'Fiziksel Gönderim Bilgileri']
        return fieldsets

@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ('mold', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('mold__patient_name', 'mold__patient_surname', 'description')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(ModeledMold)
class ModeledMoldAdmin(admin.ModelAdmin):
    list_display = ['ear_mold', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['ear_mold__patient_name', 'notes']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(QualityCheck)
class QualityCheckAdmin(admin.ModelAdmin):
    list_display = ('mold', 'result', 'score', 'created_at')
    list_filter = ('result', 'created_at')
    search_fields = ('mold__patient_name', 'mold__patient_surname', 'notes')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(RevisionRequest)
class RevisionRequestAdmin(admin.ModelAdmin):
    list_display = ('mold', 'center', 'revision_type', 'status', 'priority', 'created_at')
    list_filter = ('status', 'revision_type', 'priority', 'created_at')
    search_fields = ('mold__patient_name', 'mold__patient_surname', 'center__name', 'title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    actions = ['mark_as_accepted', 'mark_as_rejected', 'mark_as_in_progress', 'mark_as_completed']
    
    fieldsets = (
        ('Kalıp ve Merkez Bilgileri', {
            'fields': ('modeled_mold', 'mold', 'center')
        }),
        ('Revizyon Detayları', {
            'fields': ('revision_type', 'title', 'description', 'priority')
        }),
        ('Durum Bilgileri', {
            'fields': ('status', 'admin_notes', 'producer_response')
        }),
        ('Ek Dosyalar', {
            'fields': ('reference_image', 'attachment')
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at', 'resolved_at')
        }),
    )

    def mark_as_accepted(self, request, queryset):
        """Seçilen revizyon taleplerini kabul edildi olarak işaretle"""
        updated = 0
        for revision_request in queryset:
            if revision_request.status == 'pending':
                revision_request.status = 'accepted'
                revision_request.save()
                
                # Merkeze bildirim gönder
                notify.send(
                    sender=request.user,
                    recipient=revision_request.center.user,
                    verb='revizyon talebiniz admin tarafından kabul edildi',
                    action_object=revision_request,
                    description=f'{revision_request.mold.patient_name} - {revision_request.get_revision_type_display()}',
                    target=revision_request.mold
                )
                updated += 1
        
        self.message_user(request, f'{updated} revizyon talebi kabul edildi olarak işaretlendi.')
    mark_as_accepted.short_description = "Seçili talepleri kabul edildi olarak işaretle"

    def mark_as_rejected(self, request, queryset):
        """Seçilen revizyon taleplerini reddedildi olarak işaretle"""
        updated = 0
        for revision_request in queryset:
            if revision_request.status in ['pending', 'accepted']:
                revision_request.status = 'rejected'
                revision_request.save()
                
                # Revizyon reddedildiğinde kalıp durumunu da "reddedildi" yap
                revision_request.mold.status = 'rejected'
                revision_request.mold.save()
                
                # Merkeze bildirim gönder (eski sistem)
                notify.send(
                    sender=request.user,
                    recipient=revision_request.center.user,
                    verb='revizyon talebiniz admin tarafından reddedildi',
                    action_object=revision_request,
                    description=f'{revision_request.mold.patient_name} - {revision_request.get_revision_type_display()}',
                    target=revision_request.mold
                )
                
                # Yeni basit bildirim sistemi ile de gönder
                from core.utils import send_error_notification
                send_error_notification(
                    user=revision_request.center.user,
                    title="Revizyon Talebi Reddedildi",
                    message=f"{revision_request.mold.patient_name} - {revision_request.get_revision_type_display()} revizyon talebiniz admin tarafından reddedildi. Kalıp durumu 'Reddedildi' olarak güncellendi.",
                    related_url=f"/mold/{revision_request.mold.id}/"
                )
                
                updated += 1
        
        self.message_user(request, f'{updated} revizyon talebi reddedildi olarak işaretlendi. Kalıp durumları güncellendi.')
    mark_as_rejected.short_description = "Seçili talepleri reddedildi olarak işaretle"

    def mark_as_in_progress(self, request, queryset):
        """Seçilen revizyon taleplerini işlemde olarak işaretle"""
        updated = 0
        for revision_request in queryset:
            if revision_request.status == 'accepted':
                revision_request.status = 'in_progress'
                revision_request.save()
                
                # Kalıp dosyasını revizyona düş
                revision_request.modeled_mold.status = 'waiting'
                revision_request.modeled_mold.save()
                
                # Kalıp durumunu güncelle
                revision_request.mold.status = 'revision'
                revision_request.mold.save()
                
                # Merkeze bildirim gönder
                notify.send(
                    sender=request.user,
                    recipient=revision_request.center.user,
                    verb='revizyon talebiniz işleme alındı',
                    action_object=revision_request,
                    description=f'{revision_request.mold.patient_name} - {revision_request.get_revision_type_display()}',
                    target=revision_request.mold
                )
                updated += 1
        
        self.message_user(request, f'{updated} revizyon talebi işlemde olarak işaretlendi.')
    mark_as_in_progress.short_description = "Seçili talepleri işlemde olarak işaretle"

    def mark_as_completed(self, request, queryset):
        """Seçilen revizyon taleplerini tamamlandı olarak işaretle"""
        updated = 0
        for revision_request in queryset:
            if revision_request.status in ['in_progress', 'accepted']:
                revision_request.status = 'completed'
                revision_request.resolved_at = timezone.now()
                revision_request.save()
                
                # Kalıp durumunu güncelle
                revision_request.mold.status = 'completed'
                revision_request.mold.save()
                
                # Merkeze bildirim gönder
                notify.send(
                    sender=request.user,
                    recipient=revision_request.center.user,
                    verb='revizyon talebiniz tamamlandı',
                    action_object=revision_request,
                    description=f'{revision_request.mold.patient_name} - {revision_request.get_revision_type_display()}',
                    target=revision_request.mold
                )
                updated += 1
        
        self.message_user(request, f'{updated} revizyon talebi tamamlandı olarak işaretlendi.')
    mark_as_completed.short_description = "Seçili talepleri tamamlandı olarak işaretle"

@admin.register(MoldEvaluation)
class MoldEvaluationAdmin(admin.ModelAdmin):
    list_display = ('mold', 'center', 'quality_score', 'speed_score', 'overall_satisfaction', 'would_recommend', 'created_at')
    list_filter = ('quality_score', 'speed_score', 'overall_satisfaction', 'would_recommend', 'created_at')
    search_fields = ('mold__patient_name', 'mold__patient_surname', 'center__name', 'positive_feedback', 'negative_feedback')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Kalıp ve Merkez Bilgileri', {
            'fields': ('mold', 'center')
        }),
        ('Puanlama', {
            'fields': ('quality_score', 'speed_score', 'communication_score', 'packaging_score', 'overall_satisfaction')
        }),
        ('Geri Bildirimler', {
            'fields': ('positive_feedback', 'negative_feedback', 'suggestions')
        }),
        ('Genel Değerlendirme', {
            'fields': ('would_recommend',)
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at')
        }),
    )
