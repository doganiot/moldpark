from django.contrib import admin
from .models import EarMold, Revision, ModeledMold, QualityCheck, RevisionRequest, MoldEvaluation

@admin.register(EarMold)
class EarMoldAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'patient_surname', 'center', 'mold_type', 'status', 'quality_score', 'created_at')
    list_filter = ('status', 'mold_type', 'center', 'created_at')
    search_fields = ('patient_name', 'patient_surname', 'center__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Hasta Bilgileri', {
            'fields': ('patient_name', 'patient_surname', 'patient_age', 'patient_gender')
        }),
        ('Kalıp Bilgileri', {
            'fields': ('center', 'mold_type', 'vent_diameter', 'scan_file', 'notes')
        }),
        ('Durum Bilgileri', {
            'fields': ('status', 'quality_score')
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at')
        }),
    )

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
