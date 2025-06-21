from django.contrib import admin
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
    
    fieldsets = (
        ('Kalıp ve Merkez Bilgileri', {
            'fields': ('mold', 'center')
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
