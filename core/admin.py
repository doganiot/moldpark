from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ContactMessage, Message, PricingPlan, UserSubscription, PaymentHistory,
    SimpleNotification, SubscriptionRequest, PricingConfiguration,
    BankTransferConfiguration, PaymentMethod, Payment,
    CargoCompany, CargoShipment, CargoTracking, CargoIntegration, CargoLabel
)

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
            'description': 'Komisyon oranları yüzde (%) olarak girilmelidir. Örn: 7.50 = %7.5'
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


@admin.register(BankTransferConfiguration)
class BankTransferConfigurationAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_holder', 'iban', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('bank_name', 'account_holder', 'iban')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Banka Bilgileri', {
            'fields': ('bank_name', 'account_holder', 'is_active')
        }),
        ('Hesap Detayları', {
            'fields': ('iban', 'swift_code', 'branch_code', 'account_number')
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'method_type', 'is_active', 'is_default', 'order')
    list_filter = ('method_type', 'is_active')
    search_fields = ('name', 'description')
    ordering = ['order']
    
    fieldsets = (
        ('Ödeme Yöntemi Bilgileri', {
            'fields': ('name', 'method_type', 'description', 'order')
        }),
        ('Durum', {
            'fields': ('is_active', 'is_default')
        }),
        ('Havale Yapılandırması', {
            'fields': ('bank_transfer_config',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'user_display', 'amount', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method__method_type', 'created_at')
    search_fields = ('invoice__invoice_number', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'confirmed_at')
    
    fieldsets = (
        ('Ödeme Bilgileri', {
            'fields': ('invoice', 'user', 'payment_method', 'amount', 'currency')
        }),
        ('Ödeme Durumu', {
            'fields': ('status', 'created_at', 'updated_at', 'confirmed_at')
        }),
        ('Havale Detayları', {
            'fields': ('bank_confirmation_number', 'receipt_file', 'payment_date'),
            'classes': ('collapse',)
        }),
        ('Kredi Kartı Detayları', {
            'fields': ('last_four_digits', 'transaction_id'),
            'classes': ('collapse',)
        }),
        ('Notlar', {
            'fields': ('notes', 'admin_notes'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['confirm_payments', 'complete_payments']
    
    def user_display(self, obj):
        return f"{obj.user.get_full_name()} ({obj.user.username})"
    user_display.short_description = 'Kullanıcı'
    
    def confirm_payments(self, request, queryset):
        """Seçilen ödemeleri onaylı duruma getir"""
        count = 0
        for payment in queryset.filter(status='pending'):
            payment.confirm_payment()
            count += 1
        self.message_user(request, f'{count} ödeme onaylandı.')
    confirm_payments.short_description = "Ödemeleri onayla"
    
    def complete_payments(self, request, queryset):
        """Seçilen ödemeleri tamamlandı duruma getir"""
        count = 0
        for payment in queryset.filter(status='confirmed'):
            payment.complete_payment()
            count += 1
        self.message_user(request, f'{count} ödeme tamamlandı.')
    complete_payments.short_description = "Ödemeleri tamamla"


# ========================================
# KARGO SİSTEMİ ADMIN
# ========================================

@admin.register(CargoCompany)
class CargoCompanyAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'is_active', 'is_default', 'base_price', 'kg_price', 'estimated_delivery_days')
    list_filter = ('is_active', 'is_default', 'name')
    search_fields = ('display_name', 'name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'display_name', 'logo_url', 'website', 'is_active', 'is_default')
        }),
        ('Ücretlendirme', {
            'fields': ('base_price', 'kg_price', 'estimated_delivery_days')
        }),
        ('API Entegrasyonu', {
            'fields': ('api_enabled', 'api_key', 'api_secret', 'api_base_url'),
            'classes': ('collapse',)
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_companies', 'deactivate_companies', 'set_as_default']

    def activate_companies(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} kargo firması aktifleştirildi.')
    activate_companies.short_description = "Firmaları aktifleştir"

    def deactivate_companies(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} kargo firması devre dışı bırakıldı.')
    deactivate_companies.short_description = "Firmaları devre dışı bırak"

    def set_as_default(self, request, queryset):
        # Önce tümünü varsayılan dışı yap
        CargoCompany.objects.filter(is_default=True).update(is_default=False)
        # Seçilenleri varsayılan yap
        queryset.update(is_default=True)
        self.message_user(request, f'{queryset.count()} kargo firması varsayılan olarak ayarlandı.')
    set_as_default.short_description = "Varsayılan olarak ayarla"


@admin.register(CargoShipment)
class CargoShipmentAdmin(admin.ModelAdmin):
    list_display = ('tracking_number', 'cargo_company', 'invoice', 'status', 'weight_kg', 'shipping_cost', 'created_at')
    list_filter = ('status', 'cargo_company', 'created_at', 'shipped_at', 'delivered_at')
    search_fields = ('tracking_number', 'invoice__invoice_number', 'recipient_name', 'sender_name')
    readonly_fields = ('created_at', 'shipped_at', 'delivered_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Gönderi Bilgileri', {
            'fields': ('invoice', 'cargo_company', 'tracking_number', 'status', 'status_description')
        }),
        ('Gönderen Bilgileri', {
            'fields': ('sender_name', 'sender_address', 'sender_phone'),
            'classes': ('collapse',)
        }),
        ('Alıcı Bilgileri', {
            'fields': ('recipient_name', 'recipient_address', 'recipient_phone'),
            'classes': ('collapse',)
        }),
        ('Paket Bilgileri', {
            'fields': ('weight_kg', 'package_count', 'description', 'declared_value')
        }),
        ('Maliyet ve Tarihler', {
            'fields': ('shipping_cost', 'created_at', 'shipped_at', 'delivered_at', 'estimated_delivery'),
            'classes': ('collapse',)
        }),
        ('Ek Bilgiler', {
            'fields': ('notes', 'api_response'),
            'classes': ('collapse',)
        }),
    )

    actions = ['update_status_picked_up', 'update_status_in_transit', 'update_status_delivered']

    def update_status_picked_up(self, request, queryset):
        updated = 0
        for shipment in queryset.filter(status='pending'):
            shipment.update_status('picked_up', 'Gönderi kargo firması tarafından alındı')
            updated += 1
        self.message_user(request, f'{updated} gönderi "Alındı" durumuna güncellendi.')
    update_status_picked_up.short_description = "Gönderileri alındı olarak işaretle"

    def update_status_in_transit(self, request, queryset):
        updated = 0
        for shipment in queryset.filter(status='picked_up'):
            shipment.update_status('in_transit', 'Gönderi dağıtım merkezine ulaştı')
            updated += 1
        self.message_user(request, f'{updated} gönderi "Yolda" durumuna güncellendi.')
    update_status_in_transit.short_description = "Gönderileri yolda olarak işaretle"

    def update_status_delivered(self, request, queryset):
        updated = 0
        for shipment in queryset.filter(status__in=['in_transit', 'out_for_delivery']):
            shipment.update_status('delivered', 'Gönderi başarıyla teslim edildi')
            updated += 1
        self.message_user(request, f'{updated} gönderi "Teslim Edildi" durumuna güncellendi.')
    update_status_delivered.short_description = "Gönderileri teslim edildi olarak işaretle"


@admin.register(CargoTracking)
class CargoTrackingAdmin(admin.ModelAdmin):
    list_display = ('shipment', 'status', 'description', 'location', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('shipment__tracking_number', 'description', 'location')
    readonly_fields = ('timestamp', 'raw_data')
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('shipment', 'status', 'description', 'location', 'timestamp')
        }),
        ('API Verileri', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
    )


@admin.register(CargoIntegration)
class CargoIntegrationAdmin(admin.ModelAdmin):
    list_display = ('cargo_company', 'integration_type', 'test_mode', 'last_sync', 'total_shipments', 'success_rate')
    list_filter = ('integration_type', 'test_mode')
    search_fields = ('cargo_company__display_name',)
    readonly_fields = ('last_sync', 'total_shipments', 'success_rate', 'created_at', 'updated_at')

    fieldsets = (
        ('Firma Bilgileri', {
            'fields': ('cargo_company', 'integration_type', 'test_mode')
        }),
        ('Webhook Ayarları', {
            'fields': ('webhook_url', 'webhook_secret'),
            'classes': ('collapse',)
        }),
        ('API Ayarları', {
            'fields': ('auth_type', 'api_key', 'api_secret'),
            'classes': ('collapse',)
        }),
        ('İstatistikler', {
            'fields': ('last_sync', 'total_shipments', 'success_rate', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CargoLabel)
class CargoLabelAdmin(admin.ModelAdmin):
    list_display = ('name', 'size_preset', 'is_default', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_default', 'size_preset')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'description', 'is_default', 'is_active')
        }),
        ('Boyut ve Tasarım', {
            'fields': ('width_mm', 'height_mm', 'size_preset', 'background_color', 'text_color', 'border_color')
        }),
        ('İçerik Ayarları', {
            'fields': ('include_logo', 'include_qr', 'include_barcode', 'sender_info', 'recipient_info', 'package_info', 'tracking_info')
        }),
        ('Font Ayarları', {
            'fields': ('font_size_small', 'font_size_medium', 'font_size_large')
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['set_as_default', 'activate_labels', 'deactivate_labels']

    def set_as_default(self, request, queryset):
        # Önce tümünü varsayılan dışı yap
        CargoLabel.objects.filter(is_default=True).update(is_default=False)
        # Seçilenleri varsayılan yap
        queryset.update(is_default=True)
        self.message_user(request, f'{queryset.count()} etiket şablonu varsayılan olarak ayarlandı.')
    set_as_default.short_description = "Varsayılan olarak ayarla"

    def activate_labels(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} etiket şablonu aktifleştirildi.')
    activate_labels.short_description = "Şablonları aktifleştir"

    def deactivate_labels(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} etiket şablonu devre dışı bırakıldı.')
    deactivate_labels.short_description = "Şablonları devre dışı bırak"
