from django.contrib import admin
from .models import ContactMessage, Message, MessageRecipient, PricingPlan, UserSubscription, PaymentHistory

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
    list_display = ('subject', 'sender', 'created_at', 'priority')
    list_filter = ('priority', 'created_at')
    search_fields = ('subject', 'content', 'sender__username')
    readonly_fields = ('created_at', 'read_at', 'replied_at')


@admin.register(MessageRecipient)
class MessageRecipientAdmin(admin.ModelAdmin):
    list_display = ('message', 'recipient', 'is_read', 'read_at')
    list_filter = ('is_read', 'read_at')
    search_fields = ('message__subject', 'recipient__username')


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'price_usd', 'price_try', 'monthly_model_limit', 'is_active')
    list_filter = ('plan_type', 'is_active', 'is_monthly')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Plan Bilgileri', {
            'fields': ('name', 'plan_type', 'description', 'is_active')
        }),
        ('Fiyatlandırma', {
            'fields': ('price_usd', 'price_try', 'is_monthly')
        }),
        ('Limitler ve Özellikler', {
            'fields': ('monthly_model_limit', 'features')
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'models_used_this_month', 'get_remaining_display', 'start_date', 'end_date')
    list_filter = ('status', 'plan__plan_type', 'currency', 'start_date')
    search_fields = ('user__username', 'user__email', 'plan__name')
    readonly_fields = ('created_at', 'updated_at', 'last_reset_date')
    
    def get_remaining_display(self, obj):
        remaining = obj.get_remaining_models()
        if remaining is None:
            return 'Sınırsız'
        return f'{remaining} model'
    get_remaining_display.short_description = 'Kalan Model'
    
    fieldsets = (
        ('Abonelik Bilgileri', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Tarih Bilgileri', {
            'fields': ('start_date', 'end_date', 'last_reset_date')
        }),
        ('Kullanım İstatistikleri', {
            'fields': ('models_used_this_month',)
        }),
        ('Ödeme Bilgileri', {
            'fields': ('amount_paid', 'currency')
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'currency', 'payment_type', 'status', 'created_at')
    list_filter = ('status', 'payment_type', 'currency', 'created_at')
    search_fields = ('user__username', 'user__email', 'transaction_id')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Ödeme Bilgileri', {
            'fields': ('user', 'subscription', 'amount', 'currency', 'payment_type', 'status')
        }),
        ('Ödeme Detayları', {
            'fields': ('payment_method', 'transaction_id', 'notes')
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at')
        }),
    )
