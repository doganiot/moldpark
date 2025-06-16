from django.contrib import admin
from .models import EarMold, Revision, ModeledMold, QualityCheck

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
