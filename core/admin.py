from django.contrib import admin
from django.utils.html import format_html
from .models import ContactMessage, Message, PricingPlan, UserSubscription, PaymentHistory, SimpleNotification, SubscriptionRequest, PricingConfiguration

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


@admin.register(SimpleNotification)
class SimpleNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'user__email', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']
    list_editable = ['is_read']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Bildirim Bilgileri', {
            'fields': ('user', 'title', 'message', 'notification_type')
        }),
        ('Durum', {
            'fields': ('is_read', 'created_at', 'read_at')
        }),
        ('Ek Bilgiler', {
            'fields': ('related_url', 'related_object_id'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SubscriptionRequest)
class SubscriptionRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'created_at', 'processed_at', 'processed_by')
    list_filter = ('status', 'plan__plan_type', 'created_at', 'processed_at')
    search_fields = ('user__username', 'user__email', 'plan__name', 'user_notes', 'admin_notes')
    readonly_fields = ('created_at',)
    ordering = ['-created_at']
    
    actions = ['approve_requests', 'reject_requests']
    
    fieldsets = (
        ('Talep Bilgileri', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Notlar', {
            'fields': ('user_notes', 'admin_notes')
        }),
        ('İşlem Bilgileri', {
            'fields': ('processed_by', 'processed_at', 'created_at')
        }),
    )
    
    def approve_requests(self, request, queryset):
        """Seçilen talepleri onayla"""
        approved_count = 0
        for subscription_request in queryset.filter(status='pending'):
            if subscription_request.approve(request.user):
                approved_count += 1
        
        self.message_user(request, f'{approved_count} talep onaylandı.')
    approve_requests.short_description = "Seçilen talepleri onayla"
    
    def reject_requests(self, request, queryset):
        """Seçilen talepleri reddet"""
        rejected_count = 0
        for subscription_request in queryset.filter(status='pending'):
            if subscription_request.reject(request.user, 'Toplu reddetme'):
                rejected_count += 1
        
        self.message_user(request, f'{rejected_count} talep reddedildi.')
    reject_requests.short_description = "Seçilen talepleri reddet"


@admin.register(PricingConfiguration)
class PricingConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'effective_date', 
        'is_active_badge',
        'physical_mold_price', 
        'digital_modeling_price',
        'moldpark_commission_rate',
        'credit_card_commission_rate',
        'created_at'
    ]
    list_filter = ['is_active', 'effective_date', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'pricing_summary_display']
    ordering = ['-effective_date', '-created_at']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'description', 'is_active', 'effective_date')
        }),
        ('Fiyatlar (KDV Dahil)', {
            'fields': (
                'physical_mold_price', 
                'digital_modeling_price',
                'monthly_system_fee'
            ),
            'description': 'Tüm fiyatlar KDV dahil olarak girilmelidir.'
        }),
        ('Komisyon Oranları', {
            'fields': (
                'moldpark_commission_rate',
                'credit_card_commission_rate',
                'vat_rate'
            ),
            'description': 'Komisyon oranları yüzde (%) olarak girilmelidir. Örn: 6.50 = %6.5'
        }),
        ('Fiyatlandırma Özeti', {
            'fields': ('pricing_summary_display',),
            'classes': ('collapse',),
            'description': 'Bu fiyatlandırmanın detaylı hesaplama özeti'
        }),
        ('Sistem Bilgileri', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_pricing', 'deactivate_pricing']
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ AKTİF</span>')
        return format_html('<span style="color: gray;">—</span>')
    is_active_badge.short_description = 'Durum'
    
    def pricing_summary_display(self, obj):
        """Fiyatlandırma özetini güzel bir şekilde göster"""
        if not obj.pk:
            return "Önce kaydedin, sonra özet görüntülenecek."
        
        summary = obj.get_pricing_summary()
        
        html = """
        <div style="font-family: monospace; background: #f5f5f5; padding: 15px; border-radius: 5px;">
            <h3 style="margin-top: 0;">📊 Fiziksel Kalıp (450 TL)</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td><strong>KDV Dahil Fiyat:</strong></td><td style="text-align: right;">{physical_with_vat:.2f} ₺</td></tr>
                <tr><td><strong>KDV Hariç Tutar:</strong></td><td style="text-align: right;">{physical_without_vat:.2f} ₺</td></tr>
                <tr><td>KDV ({vat_rate:.1f}%):</td><td style="text-align: right;">{physical_vat:.2f} ₺</td></tr>
                <tr><td>MoldPark Hizmeti ({moldpark_rate:.2f}%):</td><td style="text-align: right; color: red;">-{physical_moldpark:.2f} ₺</td></tr>
                <tr><td>Kredi Kartı Kom. ({cc_rate:.2f}%):</td><td style="text-align: right; color: orange;">-{physical_cc:.2f} ₺</td></tr>
                <tr style="border-top: 2px solid #333;"><td><strong>Üreticiye Net:</strong></td><td style="text-align: right; font-weight: bold; color: green;">{physical_net:.2f} ₺</td></tr>
            </table>
            
            <h3>📊 3D Modelleme (50 TL)</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td><strong>KDV Dahil Fiyat:</strong></td><td style="text-align: right;">{digital_with_vat:.2f} ₺</td></tr>
                <tr><td><strong>KDV Hariç Tutar:</strong></td><td style="text-align: right;">{digital_without_vat:.2f} ₺</td></tr>
                <tr><td>KDV ({vat_rate:.1f}%):</td><td style="text-align: right;">{digital_vat:.2f} ₺</td></tr>
                <tr><td>MoldPark Hizmeti ({moldpark_rate:.2f}%):</td><td style="text-align: right; color: red;">-{digital_moldpark:.2f} ₺</td></tr>
                <tr><td>Kredi Kartı Kom. ({cc_rate:.2f}%):</td><td style="text-align: right; color: orange;">-{digital_cc:.2f} ₺</td></tr>
                <tr style="border-top: 2px solid #333;"><td><strong>Üreticiye Net:</strong></td><td style="text-align: right; font-weight: bold; color: green;">{digital_net:.2f} ₺</td></tr>
            </table>
            
            <h3>📈 Oranlar</h3>
            <ul>
                <li><strong>MoldPark Komisyonu:</strong> %{moldpark_rate:.2f}</li>
                <li><strong>Kredi Kartı Komisyonu:</strong> %{cc_rate:.2f}</li>
                <li><strong>KDV Oranı:</strong> %{vat_rate:.1f}</li>
            </ul>
        </div>
        """.format(
            physical_with_vat=summary['physical']['with_vat'],
            physical_without_vat=summary['physical']['without_vat'],
            physical_vat=summary['physical']['vat_amount'],
            physical_moldpark=summary['physical']['moldpark_fee'],
            physical_cc=summary['physical']['credit_card_fee'],
            physical_net=summary['physical']['net_to_producer'],
            digital_with_vat=summary['digital']['with_vat'],
            digital_without_vat=summary['digital']['without_vat'],
            digital_vat=summary['digital']['vat_amount'],
            digital_moldpark=summary['digital']['moldpark_fee'],
            digital_cc=summary['digital']['credit_card_fee'],
            digital_net=summary['digital']['net_to_producer'],
            moldpark_rate=summary['rates']['moldpark_commission'],
            cc_rate=summary['rates']['credit_card_commission'],
            vat_rate=summary['rates']['vat_rate']
        )
        
        return format_html(html)
    pricing_summary_display.short_description = 'Detaylı Hesaplama Özeti'
    
    def activate_pricing(self, request, queryset):
        """Seçilen fiyatlandırmayı aktif yap"""
        if queryset.count() > 1:
            self.message_user(request, 'Sadece bir fiyatlandırma seçebilirsiniz.', level='error')
            return
        
        pricing = queryset.first()
        PricingConfiguration.objects.filter(is_active=True).update(is_active=False)
        pricing.is_active = True
        pricing.save()
        
        self.message_user(request, f'{pricing.name} fiyatlandırması aktif edildi.')
    activate_pricing.short_description = "Seçilen fiyatlandırmayı aktif yap"
    
    def deactivate_pricing(self, request, queryset):
        """Seçilen fiyatlandırmaları pasif yap"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} fiyatlandırma pasif edildi.')
    deactivate_pricing.short_description = "Seçilen fiyatlandırmaları pasif yap"
    
    def save_model(self, request, obj, form, change):
        """Kaydederken oluşturan kullanıcıyı kaydet"""
        if not change:  # Yeni kayıt
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
