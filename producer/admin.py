from django.contrib import admin
from .models import Producer, ProducerNetwork, ProducerOrder, ProducerMessage, ProducerProductionLog


@admin.register(Producer)
class ProducerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'producer_type', 'is_active', 'is_verified', 'get_network_centers_count', 'created_at')
    list_filter = ('producer_type', 'is_active', 'is_verified', 'created_at')
    search_fields = ('company_name', 'brand_name', 'contact_email', 'phone')
    readonly_fields = ('created_at', 'updated_at', 'verification_date')
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('user', 'company_name', 'brand_name', 'description', 'producer_type')
        }),
        ('İletişim Bilgileri', {
            'fields': ('address', 'phone', 'contact_email', 'website')
        }),
        ('İş Bilgileri', {
            'fields': ('tax_number', 'trade_registry', 'established_year')
        }),
        ('Sistem Ayarları', {
            'fields': ('mold_limit', 'monthly_limit', 'notification_preferences')
        }),
        ('Durum ve Kontrol', {
            'fields': ('is_active', 'is_verified', 'verification_date')
        }),
        ('Dosyalar', {
            'fields': ('logo', 'certificate')
        }),
        ('Tarihler', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_network_centers_count(self, obj):
        return obj.get_network_centers_count()
    get_network_centers_count.short_description = 'Ağdaki Merkez Sayısı'


@admin.register(ProducerNetwork)
class ProducerNetworkAdmin(admin.ModelAdmin):
    list_display = ('producer', 'center', 'status', 'can_receive_orders', 'priority_level', 'joined_at')
    list_filter = ('status', 'can_receive_orders', 'can_send_messages', 'joined_at')
    search_fields = ('producer__company_name', 'center__name')
    readonly_fields = ('joined_at', 'activated_at', 'last_activity')
    
    fieldsets = (
        ('İlişki', {
            'fields': ('producer', 'center', 'status')
        }),
        ('İzinler', {
            'fields': ('can_receive_orders', 'can_send_messages', 'priority_level')
        }),
        ('Tarihler', {
            'fields': ('joined_at', 'activated_at', 'last_activity'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProducerOrder)
class ProducerOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'producer', 'center', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'created_at', 'shipping_company')
    search_fields = ('order_number', 'producer__company_name', 'center__name', 'tracking_number')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Sipariş Bilgileri', {
            'fields': ('order_number', 'producer', 'center', 'ear_mold', 'status', 'priority')
        }),
        ('Zaman Bilgileri', {
            'fields': ('estimated_delivery', 'actual_delivery')
        }),
        ('Kargo Bilgileri', {
            'fields': ('shipping_company', 'tracking_number', 'shipping_cost')
        }),
        ('Notlar', {
            'fields': ('producer_notes', 'center_notes')
        }),
        ('Tarihler', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProducerMessage)
class ProducerMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'producer', 'center', 'sender_is_producer', 'message_type', 'is_read', 'created_at')
    list_filter = ('message_type', 'is_read', 'is_archived', 'is_urgent', 'sender_is_producer', 'created_at')
    search_fields = ('subject', 'message', 'producer__company_name', 'center__name')
    readonly_fields = ('created_at', 'read_at')
    
    fieldsets = (
        ('Mesaj Bilgileri', {
            'fields': ('producer', 'center', 'sender_is_producer', 'message_type', 'subject', 'message')
        }),
        ('Ek Bilgiler', {
            'fields': ('attachment', 'related_order')
        }),
        ('Durum', {
            'fields': ('is_read', 'is_archived', 'is_urgent')
        }),
        ('Tarihler', {
            'fields': ('created_at', 'read_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProducerProductionLog)
class ProducerProductionLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'stage', 'operator', 'duration_minutes', 'created_at')
    list_filter = ('stage', 'created_at')
    search_fields = ('order__order_number', 'operator', 'description')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('order', 'stage', 'description', 'operator', 'duration_minutes')
        }),
        ('Ek Bilgiler', {
            'fields': ('photo', 'notes')
        }),
        ('Tarih', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
