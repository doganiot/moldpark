from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from .models import Producer, ProducerOrder, ProducerMessage, ProducerNetwork, ProducerProductionLog


@admin.register(Producer)
class ProducerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'tax_number', 'phone', 'is_active', 'is_verified', 'get_orders_count', 'created_at')
    list_filter = ('is_active', 'is_verified', 'producer_type', 'created_at')
    search_fields = ('company_name', 'tax_number', 'contact_email', 'brand_name')
    readonly_fields = ('created_at', 'updated_at', 'last_activity', 'get_orders_count', 'get_network_centers_count')
    
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
            'fields': ('is_active', 'is_verified')
        }),
        ('Dosyalar', {
            'fields': ('logo', 'certificate')
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at', 'last_activity'),
            'classes': ('collapse',)
        }),
        ('İstatistikler', {
            'fields': ('get_orders_count', 'get_network_centers_count'),
            'classes': ('collapse',)
        })
    )
    
    def get_orders_count(self, obj):
        """Toplam sipariş sayısı"""
        count = obj.orders.count()
        return format_html(
            '<a href="{}?producer={}">{} sipariş</a>',
            reverse('admin:producer_producerorder_changelist'),
            obj.pk,
            count
        )
    get_orders_count.short_description = 'Siparişler'
    
    def get_network_centers_count(self, obj):
        """Ağdaki merkez sayısı"""
        count = obj.network_centers.filter(status='active').count()
        return format_html(
            '<span class="badge bg-success">{} aktif merkez</span>',
            count
        )
    get_network_centers_count.short_description = 'Ağ Merkezleri'
    
    def save_model(self, request, obj, form, change):
        """Model kaydederken güvenlik kontrolü"""
        # Üretici user'ınının admin yetkilerini kaldır
        if obj.user:
            obj.user.is_staff = False
            obj.user.is_superuser = False
            obj.user.save()
        super().save_model(request, obj, form, change)


@admin.register(ProducerOrder)
class ProducerOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'producer', 'center', 'ear_mold', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('order_number', 'producer__company_name', 'center__name', 'ear_mold__patient_name')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Sipariş Bilgileri', {
            'fields': ('order_number', 'producer', 'center', 'ear_mold')
        }),
        ('Sipariş Detayları', {
            'fields': ('status', 'priority')
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
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ProducerMessage)
class ProducerMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'producer', 'center', 'sender_is_producer', 'message_type', 'is_read', 'created_at')
    list_filter = ('message_type', 'sender_is_producer', 'is_read', 'is_urgent', 'created_at')
    search_fields = ('subject', 'message', 'producer__company_name', 'center__name')
    readonly_fields = ('created_at', 'read_at')


@admin.register(ProducerNetwork)
class ProducerNetworkAdmin(admin.ModelAdmin):
    list_display = ('producer', 'center', 'status', 'can_receive_orders', 'priority_level', 'joined_at')
    list_filter = ('status', 'can_receive_orders', 'can_send_messages', 'joined_at')
    search_fields = ('producer__company_name', 'center__name')
    readonly_fields = ('joined_at', 'activated_at', 'last_activity')


@admin.register(ProducerProductionLog)
class ProducerProductionLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'stage', 'operator', 'duration_minutes', 'created_at')
    list_filter = ('stage', 'created_at')
    search_fields = ('order__order_number', 'operator', 'description')
    readonly_fields = ('created_at',)
