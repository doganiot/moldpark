from django.contrib import admin
from .models import Center, Recipient, DeliveryNote, DeliveryNoteItem

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

# CenterMessage admin kaldırıldı - Merkezi mesajlaşma sistemi kullanılıyor


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'center', 'city', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'center', 'created_at')
    search_fields = ('company_name', 'address', 'city', 'phone', 'email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)


class DeliveryNoteItemInline(admin.TabularInline):
    model = DeliveryNoteItem
    extra = 1
    fields = ('cinsi', 'miktar', 'birim_fiyat', 'tutari', 'order')
    verbose_name = 'İrsaliye Kalemi'
    verbose_name_plural = 'İrsaliye Kalemleri'


@admin.register(DeliveryNoteItem)
class DeliveryNoteItemAdmin(admin.ModelAdmin):
    list_display = ('cinsi', 'miktar', 'birim_fiyat', 'tutari', 'order')
    search_fields = ('cinsi',)
    ordering = ('order',)


@admin.register(DeliveryNote)
class DeliveryNoteAdmin(admin.ModelAdmin):
    list_display = ('note_number', 'center', 'recipient_company_name', 'issue_date', 'is_draft', 'created_at')
    list_filter = ('is_draft', 'issue_date', 'center', 'created_at')
    search_fields = ('note_number', 'recipient_company_name', 'recipient_address')
    readonly_fields = ('note_number', 'created_at', 'updated_at')
    ordering = ('-issue_date', '-created_at')
    inlines = [DeliveryNoteItemInline]
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('center', 'note_number', 'issue_date', 'is_draft')
        }),
        ('Alıcı Bilgileri', {
            'fields': ('recipient', 'recipient_company_name', 'recipient_address', 'recipient_city', 'recipient_phone')
        }),
        ('Notlar', {
            'fields': ('notes',)
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at')
        }),
    )
