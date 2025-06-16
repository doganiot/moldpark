from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from center.models import Center


class Producer(models.Model):
    """Üretici Merkez Modeli - Kalıp üretimi yapan firmalar"""
    
    NOTIFICATION_CHOICES = (
        ('new_order', 'Yeni Sipariş'),
        ('production', 'Üretim'),
        ('shipping', 'Kargo'),
        ('completed', 'Tamamlanan Sipariş'),
        ('urgent', 'Acil Durum'),
        ('system', 'Sistem Bildirimleri'),
    )
    
    PRODUCER_TYPE_CHOICES = (
        ('manufacturer', 'Kalıp Üreticisi'),
        ('laboratory', '3D Laboratuvar'),
        ('hybrid', 'Hibrit (Üretici + Lab)'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='producer')
    company_name = models.CharField('Firma Adı', max_length=150)
    brand_name = models.CharField('Marka Adı', max_length=100, blank=True)
    description = models.TextField('Firma Açıklaması', blank=True)
    producer_type = models.CharField('Üretici Türü', max_length=20, choices=PRODUCER_TYPE_CHOICES, default='manufacturer')
    
    # İletişim Bilgileri
    address = models.TextField('Adres')
    phone = models.CharField('Telefon', max_length=20)
    contact_email = models.EmailField('İletişim E-posta', blank=True)
    website = models.URLField('Web Sitesi', blank=True)
    
    # İş Bilgileri
    tax_number = models.CharField('Vergi Numarası', max_length=20, blank=True)
    trade_registry = models.CharField('Ticaret Sicil No', max_length=30, blank=True)
    established_year = models.IntegerField('Kuruluş Yılı', blank=True, null=True)
    
    # Sistem Ayarları
    mold_limit = models.IntegerField('Kalıp Limiti', validators=[MinValueValidator(0)], default=100)
    monthly_limit = models.IntegerField('Aylık Kalıp Limiti', validators=[MinValueValidator(1)], default=500)
    notification_preferences = models.CharField('Bildirim Tercihleri', max_length=200, default='system')
    
    # Durum ve Kontrol
    is_active = models.BooleanField('Aktif', default=True)
    is_verified = models.BooleanField('Doğrulanmış', default=False)
    verification_date = models.DateTimeField('Doğrulama Tarihi', blank=True, null=True)
    
    # Dosyalar
    logo = models.ImageField('Logo', upload_to='producer_logos/', blank=True, null=True)
    certificate = models.FileField('Sertifika', upload_to='producer_certificates/', blank=True, null=True)
    
    # Tarihler
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)

    class Meta:
        verbose_name = 'Üretici Merkez'
        verbose_name_plural = 'Üretici Merkezler'
        ordering = ['-created_at']

    def __str__(self):
        return self.company_name

    def get_network_centers_count(self):
        """Ağındaki merkez sayısını döndürür"""
        return self.network_centers.filter(status='active').count()

    def get_current_month_orders(self):
        """Bu ayki sipariş sayısını döndürür"""
        from django.utils import timezone
        now = timezone.now()
        return self.orders.filter(
            created_at__year=now.year,
            created_at__month=now.month
        ).count()

    def get_remaining_limit(self):
        """Kalan limit sayısını döndürür"""
        return self.mold_limit - self.get_current_month_orders()


class ProducerNetwork(models.Model):
    """Üretici-Merkez Ağ İlişkisi"""
    
    STATUS_CHOICES = (
        ('pending', 'Beklemede'),
        ('active', 'Aktif'),
        ('suspended', 'Askıya Alınmış'),
        ('terminated', 'Sonlandırılmış'),
    )
    
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE, related_name='network_centers')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='producer_networks')
    status = models.CharField('Durum', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # İzinler ve Limitler
    can_receive_orders = models.BooleanField('Sipariş Alabilir', default=True)
    can_send_messages = models.BooleanField('Mesaj Gönderebilir', default=True)
    priority_level = models.IntegerField('Öncelik Seviyesi', default=1, validators=[MinValueValidator(1)])
    
    # Tarihler
    joined_at = models.DateTimeField('Katılma Tarihi', auto_now_add=True)
    activated_at = models.DateTimeField('Aktifleşme Tarihi', blank=True, null=True)
    last_activity = models.DateTimeField('Son Aktivite', blank=True, null=True)

    class Meta:
        verbose_name = 'Üretici Ağı'
        verbose_name_plural = 'Üretici Ağları'
        unique_together = ('producer', 'center')
        ordering = ['-joined_at']

    def __str__(self):
        return f'{self.producer.company_name} - {self.center.name}'


class ProducerOrder(models.Model):
    """Üretici Siparişleri"""
    
    STATUS_CHOICES = (
        ('received', 'Alındı'),
        ('designing', '3D Tasarım'),
        ('production', 'Üretimde'),
        ('quality_check', 'Kalite Kontrol'),
        ('packaging', 'Paketleme'),
        ('shipping', 'Kargoda'),
        ('delivered', 'Teslim Edildi'),
        ('cancelled', 'İptal Edildi'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Düşük'),
        ('normal', 'Normal'),
        ('high', 'Yüksek'),
        ('urgent', 'Acil'),
    )
    
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE, related_name='orders')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='producer_orders')
    ear_mold = models.ForeignKey('mold.EarMold', on_delete=models.CASCADE, related_name='producer_orders')
    
    # Sipariş Bilgileri
    order_number = models.CharField('Sipariş No', max_length=50, unique=True)
    status = models.CharField('Durum', max_length=20, choices=STATUS_CHOICES, default='received')
    priority = models.CharField('Öncelik', max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Zaman Bilgileri
    estimated_delivery = models.DateTimeField('Tahmini Teslimat', blank=True, null=True)
    actual_delivery = models.DateTimeField('Gerçek Teslimat', blank=True, null=True)
    
    # Kargo Bilgileri
    shipping_company = models.CharField('Kargo Şirketi', max_length=100, blank=True)
    tracking_number = models.CharField('Takip Numarası', max_length=100, blank=True)
    shipping_cost = models.DecimalField('Kargo Ücreti', max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Notlar
    producer_notes = models.TextField('Üretici Notları', blank=True)
    center_notes = models.TextField('Merkez Notları', blank=True)
    
    # Tarihler
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)

    class Meta:
        verbose_name = 'Üretici Siparişi'
        verbose_name_plural = 'Üretici Siparişleri'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order_number} - {self.center.name}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Otomatik sipariş numarası oluştur
            import uuid
            self.order_number = f'PRD-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)

    def get_status_color(self):
        """Durum için Bootstrap renk sınıfı döndürür"""
        color_map = {
            'received': 'info',
            'designing': 'warning',
            'production': 'primary',
            'quality_check': 'secondary',
            'packaging': 'info',
            'shipping': 'warning',
            'delivered': 'success',
            'cancelled': 'danger',
        }
        return color_map.get(self.status, 'light')


class ProducerMessage(models.Model):
    """Üretici-Merkez Mesajlaşma Sistemi"""
    
    MESSAGE_TYPE_CHOICES = (
        ('order', 'Sipariş'),
        ('technical', 'Teknik'),
        ('administrative', 'İdari'),
        ('complaint', 'Şikayet'),
        ('general', 'Genel'),
    )
    
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE, related_name='messages')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='producer_messages')
    sender_is_producer = models.BooleanField('Gönderen Üretici mi?', default=True)
    
    # Mesaj Bilgileri
    message_type = models.CharField('Mesaj Türü', max_length=20, choices=MESSAGE_TYPE_CHOICES, default='general')
    subject = models.CharField('Konu', max_length=200)
    message = models.TextField('Mesaj')
    
    # Durum Bilgileri
    is_read = models.BooleanField('Okundu', default=False)
    is_archived = models.BooleanField('Arşivlendi', default=False)
    is_urgent = models.BooleanField('Acil', default=False)
    
    # Ek Dosyalar
    attachment = models.FileField('Ek Dosya', upload_to='producer_messages/', blank=True, null=True)
    
    # İlişkili Sipariş
    related_order = models.ForeignKey(ProducerOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    
    # Tarihler
    created_at = models.DateTimeField('Gönderilme Tarihi', auto_now_add=True)
    read_at = models.DateTimeField('Okunma Tarihi', blank=True, null=True)

    class Meta:
        verbose_name = 'Üretici Mesajı'
        verbose_name_plural = 'Üretici Mesajları'
        ordering = ['-created_at']

    def __str__(self):
        sender = self.producer.company_name if self.sender_is_producer else self.center.name
        receiver = self.center.name if self.sender_is_producer else self.producer.company_name
        return f'{sender} -> {receiver}: {self.subject}'


class ProducerProductionLog(models.Model):
    """Üretim Süreci Takip Logu"""
    
    STAGE_CHOICES = (
        ('design_start', 'Tasarım Başladı'),
        ('design_complete', 'Tasarım Tamamlandı'),
        ('production_start', 'Üretim Başladı'),
        ('production_complete', 'Üretim Tamamlandı'),
        ('quality_start', 'Kalite Kontrol Başladı'),
        ('quality_complete', 'Kalite Kontrol Tamamlandı'),
        ('packaging_complete', 'Paketleme Tamamlandı'),
        ('shipping_start', 'Kargo Hazırlık'),
        ('shipped', 'Kargoya Verildi'),
        ('delivered', 'Teslim Edildi'),
    )
    
    order = models.ForeignKey(ProducerOrder, on_delete=models.CASCADE, related_name='production_logs')
    stage = models.CharField('Aşama', max_length=30, choices=STAGE_CHOICES)
    description = models.TextField('Açıklama', blank=True)
    operator = models.CharField('Operatör', max_length=100, blank=True)
    duration_minutes = models.IntegerField('Süre (Dakika)', blank=True, null=True)
    
    # Ek Bilgiler
    photo = models.ImageField('Fotoğraf', upload_to='production_logs/', blank=True, null=True)
    notes = models.TextField('Notlar', blank=True)
    
    # Tarih
    created_at = models.DateTimeField('Kayıt Tarihi', auto_now_add=True)

    class Meta:
        verbose_name = 'Üretim Logu'
        verbose_name_plural = 'Üretim Logları'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order.order_number} - {self.get_stage_display()}'
