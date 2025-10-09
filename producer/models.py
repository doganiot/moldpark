from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from center.models import Center
from django.utils import timezone
from decimal import Decimal


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
    company_name = models.CharField("Firma Adı", max_length=200)
    brand_name = models.CharField('Marka Adı', max_length=100, blank=True)
    description = models.TextField('Firma Açıklaması', blank=True)
    producer_type = models.CharField('Üretici Türü', max_length=20, choices=PRODUCER_TYPE_CHOICES, default='manufacturer')
    
    # İletişim Bilgileri
    address = models.TextField("Adres")
    phone = models.CharField("Telefon", max_length=20)
    contact_email = models.EmailField('İletişim E-posta', blank=True)
    website = models.URLField("Website", blank=True, null=True)
    
    # İş Bilgileri
    tax_number = models.CharField("Vergi Numarası", max_length=20, unique=True)
    trade_registry = models.CharField('Ticaret Sicil No', max_length=30, blank=True)
    established_year = models.IntegerField('Kuruluş Yılı', blank=True, null=True)
    
    # Sistem Ayarları
    monthly_limit = models.IntegerField('Aylık Kalıp Limiti', validators=[MinValueValidator(1)], default=500)
    notification_preferences = models.CharField('Bildirim Tercihleri', max_length=200, default='system')
    
    # Durum ve Kontrol
    is_active = models.BooleanField("Aktif", default=True)
    is_verified = models.BooleanField("Doğrulanmış", default=False)  # Admin onayı gerekli
    verification_date = models.DateTimeField("Doğrulama Tarihi", blank=True, null=True)
    
    # Dosyalar
    logo = models.ImageField('Logo', upload_to='producer_logos/', blank=True, null=True)
    certificate = models.FileField('Sertifika', upload_to='producer_certificates/', blank=True, null=True)
    
    # Tarihler
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Üretici Merkez"
        verbose_name_plural = "Üretici Merkezler"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name} - {self.tax_number}"

    def save(self, *args, **kwargs):
        """Model kaydederken güvenlik kontrolü"""
        # ÖNEMLİ GÜVENLİK: User'a admin yetkisi verme
        if self.user:
            self.user.is_staff = False
            self.user.is_superuser = False
            self.user.save()
        
        # Aktivite zamanını güncelle
        self.last_activity = timezone.now()
        super().save(*args, **kwargs)

    def get_active_centers(self):
        """Aktif işitme merkezleri"""
        return self.network_centers.filter(status='active')

    def get_current_month_orders(self):
        """Bu ayki sipariş sayısı"""
        now = timezone.now()
        return self.orders.filter(
            created_at__year=now.year,
            created_at__month=now.month
        ).count()

    def get_remaining_limit(self):
        """Kalan kalıp limiti"""
        current_month_orders = self.get_current_month_orders()
        return max(0, self.monthly_limit - current_month_orders)

    def can_accept_order(self):
        """Yeni sipariş alabilir mi?"""
        if not self.is_active or not self.is_verified:
            return False
        return self.get_remaining_limit() > 0

    def is_admin_user(self):
        """Güvenlik kontrolü: Üretici asla admin olamaz"""
        return False
    
    def get_average_rating(self):
        """Ortalama değerlendirme puanını hesaplar"""
        from mold.models import MoldEvaluation
        evaluations = MoldEvaluation.objects.filter(
            mold__producer_orders__producer=self
        ).distinct()
        
        if not evaluations.exists():
            return 0
        
        total_quality = sum(eval.quality_score for eval in evaluations)
        total_speed = sum(eval.speed_score for eval in evaluations)
        total_evaluations = evaluations.count()
        
        avg_quality = total_quality / total_evaluations
        avg_speed = total_speed / total_evaluations
        
        return round((avg_quality + avg_speed) / 2, 1)
    
    def get_quality_rating(self):
        """Ortalama kalite puanını hesaplar"""
        from mold.models import MoldEvaluation
        evaluations = MoldEvaluation.objects.filter(
            mold__producer_orders__producer=self
        ).distinct()
        
        if not evaluations.exists():
            return 0
        
        total_quality = sum(eval.quality_score for eval in evaluations)
        return round(total_quality / evaluations.count(), 1)
    
    def get_speed_rating(self):
        """Ortalama hız puanını hesaplar"""
        from mold.models import MoldEvaluation
        evaluations = MoldEvaluation.objects.filter(
            mold__producer_orders__producer=self
        ).distinct()
        
        if not evaluations.exists():
            return 0
        
        total_speed = sum(eval.speed_score for eval in evaluations)
        return round(total_speed / evaluations.count(), 1)
    
    def get_total_evaluations(self):
        """Toplam değerlendirme sayısını döndürür"""
        from mold.models import MoldEvaluation
        return MoldEvaluation.objects.filter(
            mold__producer_orders__producer=self
        ).distinct().count()
    
    def get_rating_color(self):
        """Puan rengi döndürür"""
        avg_rating = self.get_average_rating()
        if avg_rating >= 8:
            return 'success'
        elif avg_rating >= 6:
            return 'warning'
        elif avg_rating > 0:
            return 'danger'
        else:
            return 'secondary'

    def get_monthly_revenue(self, year=None, month=None):
        """Belirtilen ay için toplam geliri hesapla"""
        from django.db.models import Q
        from decimal import Decimal

        if not year or not month:
            from datetime import date
            current_date = date.today()
            year = current_date.year
            month = current_date.month

        # Ayın başlangıç ve bitiş tarihlerini hesapla
        from datetime import date
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        # Tamamlanan siparişleri al
        completed_orders = self.orders.filter(
            status='delivered',
            actual_delivery__gte=start_date,
            actual_delivery__lt=end_date
        )

        total_revenue = Decimal('0.00')
        for order in completed_orders:
            # Sipariş türüne göre fiyat belirle
            if order.ear_mold.is_physical_shipment:
                total_revenue += Decimal('350.00')  # Fiziksel kalıp
            else:
                total_revenue += Decimal('150.00')  # Dijital tarama

        return total_revenue

    def get_total_earnings(self):
        """Toplam kazançları hesapla"""
        from decimal import Decimal

        total_gross = Decimal('0.00')
        total_completed_orders = 0

        # Tüm tamamlanan siparişler için
        for order in self.orders.filter(status='delivered'):
            if order.ear_mold.is_physical_shipment:
                total_gross += Decimal('350.00')
            else:
                total_gross += Decimal('150.00')
            total_completed_orders += 1

        # Kesintiler
        moldpark_fee = total_gross * Decimal('0.065')  # %6.5
        credit_card_fee = total_gross * Decimal('0.026')  # %2.6
        total_deductions = moldpark_fee + credit_card_fee

        net_earnings = total_gross - total_deductions

        return {
            'total_orders': total_completed_orders,
            'gross_revenue': total_gross,
            'moldpark_fee': moldpark_fee,
            'credit_card_fee': credit_card_fee,
            'total_deductions': total_deductions,
            'net_earnings': net_earnings
        }

    def get_pending_payments(self):
        """Ödenmemiş fatura tutarlarını hesapla"""
        from decimal import Decimal

        pending_invoices = self.invoices.filter(
            status__in=['sent', 'issued']
        )

        total_pending = Decimal('0.00')
        for invoice in pending_invoices:
            total_pending += invoice.net_amount

        return total_pending

    def get_earnings_by_month(self, limit=12):
        """Son X ay için aylık kazançları döndür"""
        from datetime import date, timedelta
        from calendar import monthrange

        earnings = []
        current_date = date.today()

        for i in range(limit):
            target_date = current_date - timedelta(days=30 * i)
            year = target_date.year
            month = target_date.month

            monthly_revenue = self.get_monthly_revenue(year, month)

            # Kesintiler
            moldpark_fee = monthly_revenue * Decimal('0.065')
            credit_card_fee = monthly_revenue * Decimal('0.026')
            net_earnings = monthly_revenue - moldpark_fee - credit_card_fee

            earnings.append({
                'year': year,
                'month': month,
                'month_name': {
                    1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan',
                    5: 'Mayıs', 6: 'Haziran', 7: 'Temmuz', 8: 'Ağustos',
                    9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
                }.get(month, ''),
                'gross_revenue': monthly_revenue,
                'net_earnings': net_earnings,
                'deductions': moldpark_fee + credit_card_fee
            })

        return earnings


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
    terminated_at = models.DateTimeField('Sonlandırılma Tarihi', blank=True, null=True)
    
    # Sonlandırma Bilgileri
    termination_reason = models.TextField('Sonlandırma Nedeni', blank=True)
    auto_assigned = models.BooleanField('Otomatik Atama', default=False)
    assignment_reason = models.TextField('Atama Nedeni', blank=True)

    class Meta:
        verbose_name = 'Üretici Ağı'
        verbose_name_plural = 'Üretici Ağları'
        unique_together = ('producer', 'center')
        ordering = ['-joined_at']

    def __str__(self):
        return f'{self.producer.company_name} - {self.center.name}'
    
    def save(self, *args, **kwargs):
        """Network durumu değiştiğinde otomatik aktivasyon tarihi güncelle"""
        if self.status == 'active' and not self.activated_at:
            from django.utils import timezone
            self.activated_at = timezone.now()
        super().save(*args, **kwargs)
    
    def is_active_and_healthy(self):
        """Network'ün aktif ve sağlıklı olup olmadığını kontrol et"""
        return self.status == 'active' and self.can_receive_orders
    
    def update_activity(self):
        """Network aktivitesini güncelle"""
        from django.utils import timezone
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    def get_status_color(self):
        """Bootstrap renk sınıfı döndür"""
        color_map = {
            'pending': 'warning',
            'active': 'success',
            'suspended': 'warning',
            'terminated': 'danger',
        }
        return color_map.get(self.status, 'secondary')


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

    # Fiyat Bilgileri
    price = models.DecimalField('Sipariş Tutarı', max_digits=10, decimal_places=2, default=0.00, help_text='Bu sipariş için üreticiye ödenecek toplam tutar')

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

    def calculate_price(self):
        """Sipariş fiyatını hesapla"""
        from core.models import PricingPlan

        # Aktif fiyatlandırma planını al
        try:
            pricing_plan = PricingPlan.objects.filter(is_active=True).first()
            if not pricing_plan:
                # Varsayılan fiyatlar
                return 450.00 if self.ear_mold.is_physical_shipment else 50.00
        except PricingPlan.DoesNotExist:
            # Varsayılan fiyatlar
            return 450.00 if self.ear_mold.is_physical_shipment else 50.00

        # Fiziksel gönderim için per_mold_price_try, dijital için modeling_service_fee_try
        if self.ear_mold.is_physical_shipment:
            return pricing_plan.per_mold_price_try
        else:
            return pricing_plan.modeling_service_fee_try

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Otomatik sipariş numarası oluştur
            import uuid
            self.order_number = f'PRD-{uuid.uuid4().hex[:8].upper()}'

        # Eğer price 0 ise hesapla
        if self.price == 0:
            self.price = self.calculate_price()

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


# ProducerMessage modeli kaldırıldı - Merkezi mesajlaşma sistemi kullanılıyor


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
