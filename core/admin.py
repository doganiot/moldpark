from django.contrib import admin
from .models import ContactMessage, Message, MessageRecipient

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'subject']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Seçilen mesajları okundu olarak işaretle"
    
    actions = [mark_as_read]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        'subject', 'sender', 'recipient', 'message_type', 
        'priority', 'is_read', 'is_broadcast', 'created_at'
    ]
    list_filter = [
        'message_type', 'priority', 'is_read', 'is_broadcast', 
        'is_archived', 'created_at'
    ]
    search_fields = [
        'subject', 'content', 'sender__username', 
        'sender__first_name', 'sender__last_name',
        'recipient__username', 'recipient__first_name', 'recipient__last_name'
    ]
    readonly_fields = ['created_at', 'read_at', 'replied_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Mesaj Bilgileri', {
            'fields': ('sender', 'recipient', 'message_type', 'subject', 'content')
        }),
        ('Ayarlar', {
            'fields': ('priority', 'attachment', 'reply_to')
        }),
        ('Toplu Mesaj', {
            'fields': ('is_broadcast', 'broadcast_to_centers', 'broadcast_to_producers'),
            'classes': ('collapse',)
        }),
        ('Durum', {
            'fields': ('is_read', 'is_archived', 'is_replied')
        }),
        ('Tarihler', {
            'fields': ('created_at', 'read_at', 'replied_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'recipient', 'reply_to')
    
    def mark_as_read(self, request, queryset):
        count = 0
        for message in queryset:
            if not message.is_read:
                message.mark_as_read()
                count += 1
        self.message_user(request, f'{count} mesaj okundu olarak işaretlendi.')
    mark_as_read.short_description = "Seçilen mesajları okundu olarak işaretle"
    
    def mark_as_archived(self, request, queryset):
        count = queryset.update(is_archived=True)
        self.message_user(request, f'{count} mesaj arşivlendi.')
    mark_as_archived.short_description = "Seçilen mesajları arşivle"
    
    actions = [mark_as_read, mark_as_archived]


@admin.register(MessageRecipient)
class MessageRecipientAdmin(admin.ModelAdmin):
    list_display = ['message', 'recipient', 'is_read', 'read_at']
    list_filter = ['is_read', 'read_at', 'message__message_type']
    search_fields = [
        'message__subject', 'recipient__username', 
        'recipient__first_name', 'recipient__last_name'
    ]
    readonly_fields = ['read_at']
    ordering = ['-message__created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('message', 'recipient')
    
    def mark_as_read(self, request, queryset):
        count = 0
        for recipient in queryset:
            if not recipient.is_read:
                recipient.mark_as_read()
                count += 1
        self.message_user(request, f'{count} mesaj alıcısı okundu olarak işaretlendi.')
    mark_as_read.short_description = "Seçilen mesaj alıcılarını okundu olarak işaretle"
    
    actions = [mark_as_read]
