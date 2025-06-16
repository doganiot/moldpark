from django.contrib import admin
from .models import Center, CenterMessage

@admin.register(Center)
class CenterAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'phone', 'mold_limit', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'user__username', 'phone', 'address')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    fieldsets = (
        ('Merkez Bilgileri', {
            'fields': ('name', 'user', 'phone', 'address')
        }),
        ('Ayarlar', {
            'fields': ('mold_limit', 'is_active', 'notification_preferences')
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at',)
        }),
    )

@admin.register(CenterMessage)
class CenterMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('subject', 'message', 'sender__name', 'receiver__name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
