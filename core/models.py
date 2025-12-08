from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from notifications.signals import notify
from django.utils import timezone

class ContactMessage(models.Model):
    name = models.CharField('İsim', max_length=100)
    email = models.EmailField('E-posta')
    subject = models.CharField('Konu', max_length=200)
    message = models.TextField('Mesaj')
    created_at = models.DateTimeField('Gönderilme Tarihi', auto_now_add=True)
    is_read = models.BooleanField('Okundu', default=False)

    def __str__(self):
        return f"{self.name} - {self.subject}"

    class Meta:
        verbose_name = 'İletişim Mesajı'
        verbose_name_plural = 'İletişim Mesajları'
        ordering = ['-created_at']

@receiver(post_save, sender=ContactMessage)
def notify_admin_new_contact(sender, instance, created, **kwargs):
    if created:
        admin_users = User.objects.filter(is_superuser=True)
        for admin in admin_users:
            notify.send(
                sender=instance,
                recipient=admin,
                verb='yeni bir iletişim mesajı gönderdi',
                action_object=instance,
                description=instance.message[:100] + '...' if len(instance.message) > 100 else instance.message
            )

class Message(models.Model):
    """Merkezi Mesajlaşma Sistemi"""
    
    MESSAGE_TYPE_CHOICES = (
        ('center_to_admin', 'Merkez → Admin'),
        ('producer_to_admin', 'Üretici → Admin'),
        ('admin_to_center', 'Admin → Merkez'),
        ('admin_to_producer', 'Admin → Üretici'),
        ('admin_broadcast', 'Admin → Toplu Duyuru'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Düşük'),
        ('normal', 'Normal'),
        ('high', 'Yüksek'),
        ('urgent', 'Acil'),
    )
    
    # Gönderen ve Alıcı
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='Gönderen')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', verbose_name='Alıcı', null=True, blank=True)
    
    # Mesaj İçeriği
    message_type = models.CharField('Mesaj Türü', max_length=20, choices=MESSAGE_TYPE_CHOICES)
    subject = models.CharField('Konu', max_length=200)
    content = models.TextField('Mesaj İçeriği')
    priority = models.CharField('Öncelik', max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Toplu Mesaj için
    is_broadcast = models.BooleanField('Toplu Mesaj', default=False)
    broadcast_to_centers = models.BooleanField('İşitme Merkezlerine', default=False)
    broadcast_to_producers = models.BooleanField('Üretici Merkezlere', default=False)
    
    # Durum Bilgileri
    is_read = models.BooleanField('Okundu', default=False)
    is_archived = models.BooleanField('Arşivlendi', default=False)
    is_replied = models.BooleanField('Cevaplandı', default=False)
    
    # Dosya Eki
    attachment = models.FileField('Ek Dosya', upload_to='message_attachments/', blank=True, null=True)
    
    # Tarihler
    created_at = models.DateTimeField('Gönderilme Tarihi', auto_now_add=True)
    read_at = models.DateTimeField('Okunma Tarihi', blank=True, null=True)
    replied_at = models.DateTimeField('Cevaplandığı Tarih', blank=True, null=True)
    
    # Cevap İlişkisi
    reply_to = models.ForeignKey('self', on_delete=models.CASCADE, related_name='replies', blank=True, null=True, verbose_name='Cevaplanan Mesaj')

    class Meta:
        verbose_name = 'Mesaj'
        verbose_name_plural = 'Mesajlar'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['message_type', 'created_at']),
        ]

    def __str__(self):
        sender_name = self.sender.get_full_name() if self.sender else 'Silinmiş Kullanıcı'
        
        if self.is_broadcast:
            return f'[TOPLU] {self.subject} - {sender_name}'
        
        recipient_name = 'Toplu'
        if self.recipient:
            recipient_name = self.recipient.get_full_name() if self.recipient.get_full_name() else self.recipient.username
        
        return f'{self.subject} - {sender_name} → {recipient_name}'

    def mark_as_read(self):
        """Mesajı okundu olarak işaretle"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_as_replied(self):
        """Mesajı cevaplandı olarak işaretle"""
        if not self.is_replied:
            self.is_replied = True
            self.replied_at = timezone.now()
            self.save(update_fields=['is_replied', 'replied_at'])

    def get_sender_type(self):
        """Gönderenin tipini döndür"""
        if not self.sender:
            return 'deleted'
        if self.sender.is_superuser:
            return 'admin'
        elif hasattr(self.sender, 'center'):
            return 'center'
        elif hasattr(self.sender, 'producer'):
            return 'producer'
        return 'unknown'

    def get_recipient_type(self):
        """Alıcının tipini döndür"""
        if not self.recipient:
            return 'broadcast'
        elif self.recipient.is_superuser:
            return 'admin'
        elif hasattr(self.recipient, 'center'):
            return 'center'
        elif hasattr(self.recipient, 'producer'):
            return 'producer'
        return 'unknown'

    def can_reply(self, user):
        """Kullanıcının bu mesaja cevap verip veremeyeceğini kontrol et"""
        # Sadece admin cevap verebilir
        if user.is_superuser:
            return True
        
        # Merkez ve üreticiler sadece admin'e mesaj gönderebilir
        if (hasattr(user, 'center') or hasattr(user, 'producer')) and self.sender and self.sender.is_superuser:
            return True
            
        return False


class PricingPlan(models.Model):
    """Fiyatlandırma Planları - Basitleştirilmiş Sistem"""
    
    PLAN_TYPE_CHOICES = [
        ('standard', 'Standart Paket'),  # Tek paket sistemi
        ('package', 'Kalıp Paketi'),  # Kalıp paketleri
        ('single', 'Tek Kalıp'),  # Tek kalıp seçeneği
    ]
    
    name = models.CharField('Plan Adı', max_length=100)
    plan_type = models.CharField('Plan Türü', max_length=20, choices=PLAN_TYPE_CHOICES, default='standard')
    description = models.TextField('Açıklama')
    
    # Fiyatlar - Sistem kullanım bedeli (aylık)
    monthly_fee_try = models.DecimalField('Aylık Sistem Kullanım Bedeli (TL)', max_digits=10, decimal_places=2, default=100.00)
    
    # Fiziksel kalıp gönderme ücreti
    per_mold_price_try = models.DecimalField('Fiziksel Kalıp Gönderme Ücreti (TL)', max_digits=10, decimal_places=2, default=450.00)
    
    # Digital tarama hizmeti ücreti
    modeling_service_fee_try = models.DecimalField('Digital Tarama Hizmeti Ücreti (TL)', max_digits=10, decimal_places=2, default=50.00)
    
    # Özellikler
    features = models.JSONField('Özellikler', default=list, blank=True)
    
    # Durum
    is_active = models.BooleanField('Aktif', default=True)
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)
    
    # Eski alanları koruyalım (geriye dönük uyumluluk için)
    price_usd = models.DecimalField('Fiyat (USD)', max_digits=10, decimal_places=2, default=0)
    price_try = models.DecimalField('Fiyat (TL)', max_digits=10, decimal_places=2, default=100.00)
    monthly_model_limit = models.IntegerField('Aylık Model Limiti', null=True, blank=True, help_text='Null ise sınırsız')
    is_monthly = models.BooleanField('Aylık Plan', default=True)
    trial_days = models.IntegerField('Deneme Süresi (Gün)', default=0, help_text='0 ise deneme süresi yok')
    badge_text = models.CharField('Rozet Metni', max_length=50, blank=True, null=True, help_text='Örn: YENİ, POPÜLER')
    is_featured = models.BooleanField('Öne Çıkan', default=False)
    order = models.IntegerField('Sıralama', default=0, help_text='Küçük değer önce gösterilir')
    
    class Meta:
        verbose_name = 'Fiyatlandırma Planı'
        verbose_name_plural = 'Fiyatlandırma Planları'
        ordering = ['order', 'price_usd']
    
    def __str__(self):
        return f'{self.name} - ₺{self.monthly_fee_try}/ay + ₺{self.per_mold_price_try}/fiziksel kalıp + ₺{self.modeling_service_fee_try}/tarama'
    
    def get_price_display(self):
        """Fiyat görüntüleme"""
        return f'₺{self.monthly_fee_try}/ay (sistem) + ₺{self.per_mold_price_try}/fiziksel kalıp + ₺{self.modeling_service_fee_try}/digital tarama'
    
    def get_limit_display(self):
        """Limit görüntüleme - Artık sınırsız"""
        return 'Sınırsız (kullandıkça öde)'
    
    def calculate_total_cost(self, physical_mold_count=0, digital_scan_count=0):
        """Toplam maliyet hesaplama
        
        Args:
            physical_mold_count: Fiziksel kalıp gönderme sayısı
            digital_scan_count: Digital tarama hizmeti sayısı
        """
        physical_cost = self.per_mold_price_try * physical_mold_count
        digital_cost = self.modeling_service_fee_try * digital_scan_count
        return self.monthly_fee_try + physical_cost + digital_cost
    
    def calculate_per_order_cost(self, has_physical=True, has_digital=True):
        """Sipariş başına maliyet
        
        Args:
            has_physical: Fiziksel kalıp var mı?
            has_digital: Digital tarama var mı?
        """
        cost = 0
        if has_physical:
            cost += self.per_mold_price_try
        if has_digital:
            cost += self.modeling_service_fee_try
        return cost


class UserSubscription(models.Model):
    """Kullanıcı Abonelikleri - Kullandıkça Öde Sistemi"""
    
    STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('expired', 'Süresi Dolmuş'),
        ('cancelled', 'İptal Edilmiş'),
        ('pending', 'Beklemede'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(PricingPlan, on_delete=models.CASCADE, related_name='subscriptions')
    
    # Abonelik Bilgileri
    start_date = models.DateTimeField('Başlangıç Tarihi', default=timezone.now)
    end_date = models.DateTimeField('Bitiş Tarihi', null=True, blank=True)
    status = models.CharField('Durum', max_length=10, choices=STATUS_CHOICES, default='active')
    
    # Kullanım İstatistikleri (Artık limit yok, sadece sayaç)
    models_used_this_month = models.IntegerField('Bu Ay Kullanılan Model Sayısı', default=0)
    models_used_total = models.IntegerField('Toplam Kullanılan Model Sayısı', default=0)
    digital_scans_this_month = models.IntegerField('Bu Ay Digital Tarama Sayısı', default=0)
    last_reset_date = models.DateTimeField('Son Sıfırlama Tarihi', default=timezone.now)
    
    # Ödeme Bilgileri
    monthly_fee_paid = models.BooleanField('Bu Ay Aylık Ücret Ödendi', default=False)
    total_mold_cost_this_month = models.DecimalField('Bu Ay Kalıp Maliyeti', max_digits=10, decimal_places=2, default=0)
    last_payment_date = models.DateTimeField('Son Ödeme Tarihi', null=True, blank=True)
    currency = models.CharField('Para Birimi', max_length=3, choices=[('USD', 'USD'), ('TRY', 'TRY')], default='TRY')
    
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)
    
    # Geriye dönük uyumluluk
    amount_paid = models.DecimalField('Ödenen Tutar', max_digits=10, decimal_places=2, default=0)
    
    # Paket Kullanım Hakları (Paket satın alındığında verilen haklar)
    package_credits = models.IntegerField('Paket Kullanım Hakları', default=0, help_text='Satın alınan paketten kalan kullanım hakları')
    used_credits = models.IntegerField('Kullanılan Haklar', default=0, help_text='Paket haklarından kullanılan miktar')
    
    class Meta:
        verbose_name = 'Kullanıcı Aboneliği'
        verbose_name_plural = 'Kullanıcı Abonelikleri'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.plan.name} ({self.status})'
    
    def is_valid(self):
        """Abonelik geçerli mi?"""
        if self.status != 'active':
            return False
        if self.end_date and timezone.now() > self.end_date:
            return False
        return True
    
    def can_create_model(self):
        """Model oluşturabilir mi? - Her zaman True (paket hakkı varsa ücretsiz, yoksa tek kalıp ücreti alınır)"""
        if not self.is_valid():
            return False
        # Paket hakları bitse bile tek kalıp satın alarak devam edebilir
        return True
    
    def get_remaining_credits(self):
        """Kalan paket haklarını döndür"""
        if self.plan.plan_type == 'package':
            return max(0, self.package_credits - self.used_credits)
        return 0
    
    def add_mold_usage(self, ear_mold=None):
        """Kalıp kullanımı ekle ve maliyeti hesapla

        Args:
            ear_mold: EarMold nesnesi (ücret hesaplaması için)

        Returns:
            float: Toplam maliyet (fiziksel + dijital)
        """
        self.reset_monthly_usage_if_needed()

        physical_cost = 0
        digital_cost = 0

        if ear_mold:
            # Fiziksel kalıp gönderimi varsa
            if ear_mold.is_physical_shipment:
                # Paket planıysa ve hak varsa hak kullan, yoksa tek kalıp ücreti al
                if self.plan.plan_type == 'package' and self.package_credits > self.used_credits:
                    # Paket hakkından kullan
                    self.used_credits += 1
                    physical_cost = 0  # Paket hakkından kullanıldığı için ücret yok
                else:
                    # Paket hakkı yoksa tek kalıp ücreti al
                    physical_cost = self.plan.per_mold_price_try  # 450 TL
                
                self.models_used_this_month += 1

            # Dijital tarama seçildiyse (3D Modelleme Hizmeti) ücret al
            if not ear_mold.is_physical_shipment:
                digital_cost = self.plan.modeling_service_fee_try  # 19 TL
                self.digital_scans_this_month += 1
        else:
            # Geriye uyumluluk için eski davranış
            if self.plan.plan_type == 'package' and self.package_credits > self.used_credits:
                self.used_credits += 1
                physical_cost = 0
            else:
                physical_cost = self.plan.per_mold_price_try
            self.models_used_this_month += 1

        total_cost = physical_cost + digital_cost
        self.total_mold_cost_this_month += total_cost
        self.models_used_total += 1

        self.save()
        return total_cost
    
    def reset_monthly_usage_if_needed(self):
        """Gerekirse aylık kullanımı sıfırla (paket hakları sıfırlanmaz)"""
        now = timezone.now()
        if (now.year != self.last_reset_date.year or
            now.month != self.last_reset_date.month):
            self.models_used_this_month = 0
            self.digital_scans_this_month = 0
            self.total_mold_cost_this_month = 0
            self.monthly_fee_paid = False
            self.last_reset_date = now
            # NOT: used_credits ve package_credits sıfırlanmaz çünkü paket hakları aylık değil
            self.save()
    
    def get_remaining_models(self):
        """Kalan model sayısı - Artık sınırsız"""
        return None  # Sınırsız
    
    def get_current_month_total(self):
        """Bu ay toplam maliyet"""
        self.reset_monthly_usage_if_needed()
        monthly_fee = self.plan.monthly_fee_try if not self.monthly_fee_paid else 0
        return monthly_fee + self.total_mold_cost_this_month
    
    # Geriye dönük uyumluluk için eski methodlar
    def use_model_quota(self):
        """Eski method - yeni sisteme yönlendir"""
        return self.add_mold_usage()


class PaymentHistory(models.Model):
    """Ödeme Geçmişi"""
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Beklemede'),
        ('completed', 'Tamamlandı'),
        ('failed', 'Başarısız'),
        ('refunded', 'İade Edildi'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('subscription', 'Abonelik'),
        ('pay_per_use', 'Kullandıkça Öde'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    
    # Ödeme Bilgileri
    amount = models.DecimalField('Tutar', max_digits=10, decimal_places=2)
    currency = models.CharField('Para Birimi', max_length=3, choices=[('USD', 'USD'), ('TRY', 'TRY')])
    payment_type = models.CharField('Ödeme Türü', max_length=15, choices=PAYMENT_TYPE_CHOICES)
    status = models.CharField('Durum', max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Ödeme Detayları
    payment_method = models.CharField('Ödeme Yöntemi', max_length=50, blank=True)
    transaction_id = models.CharField('İşlem ID', max_length=100, blank=True)
    notes = models.TextField('Notlar', blank=True)
    
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)
    
    class Meta:
        verbose_name = 'Ödeme Geçmişi'
        verbose_name_plural = 'Ödeme Geçmişleri'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.get_full_name()} - {self.amount} {self.currency} - {self.get_status_display()}'


class SubscriptionRequest(models.Model):
    """Abonelik Talepleri"""
    
    STATUS_CHOICES = [
        ('pending', 'Beklemede'),
        ('approved', 'Onaylandı'),
        ('rejected', 'Reddedildi'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscription_requests', verbose_name='Kullanıcı')
    plan = models.ForeignKey(PricingPlan, on_delete=models.CASCADE, related_name='requests', verbose_name='Talep Edilen Plan')
    
    # Talep Bilgileri
    status = models.CharField('Durum', max_length=10, choices=STATUS_CHOICES, default='pending')
    user_notes = models.TextField('Kullanıcı Notları', blank=True, help_text='Talep ile ilgili özel notlarınız')
    admin_notes = models.TextField('Admin Notları', blank=True, help_text='Admin tarafından eklenen notlar')
    
    # Tarihler
    created_at = models.DateTimeField('Talep Tarihi', auto_now_add=True)
    processed_at = models.DateTimeField('İşlenme Tarihi', null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_subscription_requests', verbose_name='İşleyen Admin')
    
    class Meta:
        verbose_name = 'Abonelik Talebi'
        verbose_name_plural = 'Abonelik Talepleri'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.get_full_name()} - {self.plan.name} - {self.get_status_display()}'
    
    def approve(self, admin_user, admin_notes=''):
        """Talebi onayla ve abonelik oluştur"""
        if self.status != 'pending':
            return False
            
        self.status = 'approved'
        self.processed_at = timezone.now()
        self.processed_by = admin_user
        if admin_notes:
            self.admin_notes = admin_notes
        self.save()
        
        # Mevcut aboneliği güncelle veya yeni oluştur
        try:
            existing_subscription = UserSubscription.objects.get(user=self.user)
            # Mevcut aboneliği güncelle
            existing_subscription.plan = self.plan
            existing_subscription.start_date = timezone.now()
            existing_subscription.status = 'active'
            existing_subscription.models_used_this_month = 0  # Aylık kullanımı sıfırla
            existing_subscription.last_reset_date = timezone.now()
            existing_subscription.save()
            subscription = existing_subscription
        except UserSubscription.DoesNotExist:
            # Yeni abonelik oluştur
            subscription = UserSubscription.objects.create(
                user=self.user,
                plan=self.plan,
                start_date=timezone.now(),
                status='active'
            )
        
        # Kullanıcıya bildirim gönder
        SimpleNotification.objects.create(
            user=self.user,
            title='Abonelik Talebi Onaylandı',
            message=f'{self.plan.name} planı talebiniz onaylandı. Artık platforma erişim sağlayabilirsiniz.',
            notification_type='success',
            related_url='/subscription/'
        )
        
        return subscription
    
    def reject(self, admin_user, admin_notes=''):
        """Talebi reddet"""
        if self.status != 'pending':
            return False
            
        self.status = 'rejected'
        self.processed_at = timezone.now()
        self.processed_by = admin_user
        if admin_notes:
            self.admin_notes = admin_notes
        self.save()
        
        # Kullanıcıya bildirim gönder
        SimpleNotification.objects.create(
            user=self.user,
            title='Abonelik Talebi Reddedildi',
            message=f'{self.plan.name} planı talebiniz reddedildi. Detaylar için iletişime geçebilirsiniz.',
            notification_type='warning',
            related_url='/contact/'
        )
        
        return True


# Basit Bildirim Sistemi
class SimpleNotification(models.Model):
    NOTIFICATION_TYPES = (
        ('info', 'Bilgi'),
        ('success', 'Başarılı'),
        ('warning', 'Uyarı'),
        ('error', 'Hata'),
        ('system', 'Sistem'),
        ('order', 'Sipariş'),
        ('message', 'Mesaj'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='simple_notifications', verbose_name='Kullanıcı')
    title = models.CharField('Başlık', max_length=100)
    message = models.TextField('Mesaj', max_length=500)
    notification_type = models.CharField('Tür', max_length=20, choices=NOTIFICATION_TYPES, default='info')
    is_read = models.BooleanField('Okundu', default=False)
    created_at = models.DateTimeField('Oluşturulma', auto_now_add=True)
    read_at = models.DateTimeField('Okunma Tarihi', blank=True, null=True)
    
    # İsteğe bağlı referanslar
    related_url = models.URLField('İlgili Link', blank=True, null=True)
    related_object_id = models.PositiveIntegerField('İlgili Obje ID', blank=True, null=True)
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def get_icon(self):
        icons = {
            'info': 'fas fa-info-circle',
            'success': 'fas fa-check-circle', 
            'warning': 'fas fa-exclamation-triangle',
            'error': 'fas fa-times-circle',
            'system': 'fas fa-cog',
            'order': 'fas fa-shopping-cart',
            'message': 'fas fa-envelope',
        }
        return icons.get(self.notification_type, 'fas fa-bell')
    
    def get_color(self):
        colors = {
            'info': 'primary',
            'success': 'success',
            'warning': 'warning', 
            'error': 'danger',
            'system': 'secondary',
            'order': 'info',
            'message': 'primary',
        }
        return colors.get(self.notification_type, 'primary')
    
    class Meta:
        verbose_name = 'Basit Bildirim'
        verbose_name_plural = 'Basit Bildirimler'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"


# ---------------------------------------------
# Signals
# ---------------------------------------------

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings


@receiver(post_save, sender=SimpleNotification)
def send_notification_email(sender, instance, created, **kwargs):
    """Yeni oluşturulan bildirimleri kullanıcıya e-posta ile gönderir."""
    if not created:
        return  # Yalnızca yeni bildirimler

    user = instance.user

    # Kullanıcının e-posta adresi yoksa çık.
    if not getattr(user, "email", None):
        return

    try:
        email_subject = instance.title
        email_message = instance.message

        # İlgili URL varsa e-posta gövdesine ekleyelim.
        if instance.related_url:
            email_message += f"\n\nDetaylı bilgi: {instance.related_url}"

        send_mail(
            subject=email_subject,
            message=email_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as e:
        # Log hatayı; uygulama akışını kesme.
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Bildirim e-posta gönderim hatası: {e}")


# ============================================
# FATURA VE MALİ YÖNETİM MODELLERİ
# ============================================

class Commission(models.Model):
    """Komisyon ve Kazanç Takibi"""

    COMMISSION_TYPE_CHOICES = [
        ('moldpark_fee', 'MoldPark Sistem Ücreti (%7.5)'),
        ('credit_card', 'Kredi Kartı Komisyonu (%2.6)'),
        ('producer_commission', 'Üretici Komisyonu'),
    ]

    # İlişkiler
    invoice = models.ForeignKey('Invoice', on_delete=models.CASCADE, related_name='commissions', verbose_name='Fatura')
    producer = models.ForeignKey('producer.Producer', on_delete=models.CASCADE, null=True, blank=True, related_name='commissions', verbose_name='Üretici')

    # Komisyon Bilgileri
    commission_type = models.CharField('Komisyon Türü', max_length=20, choices=COMMISSION_TYPE_CHOICES)
    amount = models.DecimalField('Tutar', max_digits=10, decimal_places=2)
    percentage = models.DecimalField('Yüzde', max_digits=5, decimal_places=2, default=0)

    # Açıklama
    description = models.CharField('Açıklama', max_length=200, blank=True)

    # Tarihler
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)

    class Meta:
        verbose_name = 'Komisyon'
        verbose_name_plural = 'Komisyonlar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_commission_type_display()} - ₺{self.amount}'


class Transaction(models.Model):
    """Merkezi İşlem Takibi - Tüm finansal hareketler"""

    TRANSACTION_TYPE_CHOICES = [
        # Center işlemleri
        ('center_monthly_fee', 'İşitme Merkezi - Aylık Sistem Ücreti'),
        ('center_physical_mold', 'İşitme Merkezi - Fiziksel Kalıp'),
        ('center_digital_scan', 'İşitme Merkezi - Dijital Tarama'),
        ('center_invoice_payment', 'İşitme Merkezi - Fatura Ödemesi'),

        # Producer işlemleri
        ('producer_payment', 'Üretici - Ödeme Alımı'),
        ('producer_commission', 'Üretici - Komisyon Kesintisi'),
        ('producer_invoice_payment', 'Üretici - Fatura Ödemesi'),

        # MoldPark işlemleri
        ('moldpark_commission', 'MoldPark - Sistem Komisyonu'),
        ('moldpark_credit_card_fee', 'MoldPark - KK Komisyonu'),
        ('moldpark_collection', 'MoldPark - Tahsilat'),
        ('moldpark_payment', 'MoldPark - Ödeme'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Beklemede'),
        ('completed', 'Tamamlandı'),
        ('failed', 'Başarısız'),
        ('cancelled', 'İptal Edildi'),
    ]

    # İlişkiler
    invoice = models.ForeignKey('Invoice', on_delete=models.CASCADE, null=True, blank=True, related_name='transactions', verbose_name='İlgili Fatura')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions', verbose_name='Kullanıcı')
    producer = models.ForeignKey('producer.Producer', on_delete=models.CASCADE, null=True, blank=True, related_name='transactions', verbose_name='Üretici')

    # İşlem Bilgileri
    transaction_type = models.CharField('İşlem Türü', max_length=25, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField('Tutar', max_digits=10, decimal_places=2)
    currency = models.CharField('Para Birimi', max_length=3, choices=[('TRY', 'TRY'), ('USD', 'USD')], default='TRY')
    status = models.CharField('Durum', max_length=10, choices=STATUS_CHOICES, default='pending')

    # Detaylar
    description = models.TextField('Açıklama', blank=True)
    reference_id = models.CharField('Referans ID', max_length=100, blank=True, help_text='Sipariş ID, kalıp ID vb.')
    payment_method = models.CharField('Ödeme Yöntemi', max_length=50, blank=True)

    # Kaynak ve Hizmet Takibi (Yeni Sistem)
    service_provider = models.CharField('Hizmet Veren', max_length=100, blank=True, help_text='Hangi kurum/kişi hizmeti verdi')
    service_type = models.CharField('Hizmet Türü', max_length=100, blank=True, help_text='Hizmet kategorisi')
    amount_source = models.CharField('Tutar Kaynağı', max_length=200, blank=True, help_text='Bu tutarın nereden geldiği')
    amount_destination = models.CharField('Tutar Hedefi', max_length=200, blank=True, help_text='Bu tutarın nereye gideceği')
    moldpark_fee_amount = models.DecimalField('MoldPark Ücreti', max_digits=10, decimal_places=2, default=0, help_text='Bu işlemden MoldPark\'ın aldığı ücret')
    credit_card_fee_amount = models.DecimalField('KK Komisyonu', max_digits=10, decimal_places=2, default=0, help_text='Bu işlemden kesilen KK komisyonu')

    # İlişkili Nesneler
    ear_mold = models.ForeignKey('mold.EarMold', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name='İlgili Kalıp')
    center = models.ForeignKey('center.Center', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name='İlgili Merkez')

    # Tarihler
    transaction_date = models.DateTimeField('İşlem Tarihi', default=timezone.now)
    created_at = models.DateTimeField('Kayıt Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)

    class Meta:
        verbose_name = 'İşlem'
        verbose_name_plural = 'İşlemler'
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['transaction_type', 'status']),
            models.Index(fields=['user', 'transaction_date']),
            models.Index(fields=['producer', 'transaction_date']),
        ]

    def __str__(self):
        return f'{self.user.get_full_name()} - {self.get_transaction_type_display()} - ₺{self.amount}'


class Invoice(models.Model):
    """Merkezileştirilmiş Fatura Modeli - İşitme Merkezi ve Üretici için"""

    INVOICE_TYPE_CHOICES = [
        ('center_admin_invoice', 'İşitme Merkezi - Kalıp Gönderim Faturası'),
        ('producer_invoice', 'Üretici - Hizmet Bedeli Faturası'),
        ('center_monthly', 'İşitme Merkezi - Aylık Sistem Faturası'),
        ('producer_monthly', 'Üretici - Aylık Kazanç Faturası'),
        ('producer_payment', 'Üretici - Ödeme Faturası'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Taslak'),
        ('issued', 'Kesildi'),
        ('sent', 'Gönderildi'),
        ('paid', 'Ödendi'),
        ('overdue', 'Vadesi Geçmiş'),
        ('cancelled', 'İptal Edildi'),
        ('refunded', 'İade Edildi'),
    ]
    
    # Temel Bilgiler
    invoice_number = models.CharField('Fatura No', max_length=50, unique=True)
    invoice_type = models.CharField('Fatura Türü', max_length=20, choices=INVOICE_TYPE_CHOICES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices', verbose_name='Kullanıcı')

    # İlişkiler
    producer = models.ForeignKey('producer.Producer', on_delete=models.CASCADE, null=True, blank=True, related_name='invoices', verbose_name='Üretici')
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_invoices', verbose_name='Faturayı Kesén')

    # Yetkilendirme ve Rol Bilgileri
    issued_by_center = models.ForeignKey('center.Center', on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_invoices', verbose_name='Faturayı Kesén Merkez')
    issued_by_producer = models.ForeignKey('producer.Producer', on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_invoices', verbose_name='Faturayı Kesén Üretici')

    # Tarih Bilgileri
    issue_date = models.DateField('Kesim Tarihi', default=timezone.now)
    due_date = models.DateField('Vade Tarihi')
    payment_date = models.DateField('Ödeme Tarihi', null=True, blank=True)
    sent_date = models.DateTimeField('Gönderilme Tarihi', null=True, blank=True)
    
    # Mali Bilgiler
    subtotal = models.DecimalField('Ara Toplam', max_digits=10, decimal_places=2, default=0)
    
    # İşitme Merkezi için
    monthly_fee = models.DecimalField('Aylık Sistem Ücreti', max_digits=10, decimal_places=2, default=0)
    physical_mold_count = models.IntegerField('Fiziksel Kalıp Sayısı', default=0)
    physical_mold_unit_price = models.DecimalField('Fiziksel Kalıp Birim Fiyat', max_digits=10, decimal_places=2, default=450.00)
    physical_mold_cost = models.DecimalField('Fiziksel Kalıp Maliyeti', max_digits=10, decimal_places=2, default=0)
    digital_scan_count = models.IntegerField('Digital Tarama Sayısı', default=0)
    digital_scan_cost = models.DecimalField('Digital Tarama Maliyeti', max_digits=10, decimal_places=2, default=0)

    # Yeni Hesaplama Alanları (Merkezileştirilmiş Sistem)
    moldpark_service_fee_rate = models.DecimalField('MoldPark Hizmet Bedeli Oranı (%)', max_digits=5, decimal_places=2, default=7.50)
    credit_card_fee_rate = models.DecimalField('Kredi Kartı Komisyonu Oranı (%)', max_digits=5, decimal_places=2, default=3.00)
    moldpark_service_fee = models.DecimalField('MoldPark Hizmet Bedeli', max_digits=10, decimal_places=2, default=0)
    credit_card_fee = models.DecimalField('Kredi Kartı Komisyonu', max_digits=10, decimal_places=2, default=0)
    
    # Geriye dönük uyumluluk için eski alanlar
    mold_count = models.IntegerField('Kalıp Sayısı (Eski)', default=0)
    mold_cost = models.DecimalField('Kalıp Maliyeti (Eski)', max_digits=10, decimal_places=2, default=0)
    modeling_count = models.IntegerField('Modeleme Sayısı (Eski)', default=0)
    modeling_cost = models.DecimalField('Modeleme Maliyeti (Eski)', max_digits=10, decimal_places=2, default=0)
    
    # Üretici için detaylı kazanç bilgileri
    producer_order_count = models.IntegerField('Tamamlanan Sipariş Sayısı', default=0)
    producer_gross_revenue = models.DecimalField('Üretici Brüt Geliri', max_digits=10, decimal_places=2, default=0)
    producer_net_revenue = models.DecimalField('Üretici Net Geliri', max_digits=10, decimal_places=2, default=0)

    # Komisyonlar ve Kesintiler (ayrıntılı)
    moldpark_system_fee = models.DecimalField('MoldPark Sistem Ücreti (%7.5)', max_digits=10, decimal_places=2, default=0)
    credit_card_fee = models.DecimalField('Kredi Kartı Komisyonu (%2.6)', max_digits=10, decimal_places=2, default=0)
    producer_commission_amount = models.DecimalField('Üretici Komisyonu Kesintisi', max_digits=10, decimal_places=2, default=0)

    # Toplamlar
    total_amount = models.DecimalField('Toplam Tutar', max_digits=10, decimal_places=2, default=0)
    total_deductions = models.DecimalField('Toplam Kesintiler', max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField('Net Ödenecek Tutar', max_digits=10, decimal_places=2, default=0)
    
    # KDV Bilgileri
    subtotal_without_vat = models.DecimalField('KDV Hariç Tutar', max_digits=10, decimal_places=2, default=0,
        help_text='KDV hesaplanmadan önceki tutar')
    vat_rate = models.DecimalField('KDV Oranı (%)', max_digits=5, decimal_places=2, default=20.00,
        help_text='Uygulanan KDV oranı (varsayılan %20)')
    vat_amount = models.DecimalField('KDV Tutarı', max_digits=10, decimal_places=2, default=0,
        help_text='Hesaplanan KDV tutarı')
    total_with_vat = models.DecimalField('KDV Dahil Toplam', max_digits=10, decimal_places=2, default=0,
        help_text='KDV dahil toplam tutar')

    # Detaylı işlem kırılımları
    breakdown_data = models.JSONField('İşlem Kırılımları', default=dict, blank=True,
        help_text='Faturadaki her işlem için detaylı kırılım bilgileri')
    
    # Durum
    status = models.CharField('Durum', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Notlar
    notes = models.TextField('Notlar', blank=True)
    
    # Tarihler
    created_at = models.DateTimeField('Oluşturulma', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme', auto_now=True)
    
    class Meta:
        verbose_name = 'Fatura'
        verbose_name_plural = 'Faturalar'
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['issue_date']),
        ]
    
    def __str__(self):
        return f'{self.invoice_number} - {self.user.get_full_name()} - ₺{self.total_amount}'
    
    def calculate_center_invoice(self, subscription, period_start=None, period_end=None):
        """İşitme merkezi faturası hesapla

        Args:
            subscription: Kullanıcı aboneliği
            period_start: Dönem başlangıcı (None ise aylık hesaplama)
            period_end: Dönem sonu (None ise aylık hesaplama)
        """
        from decimal import Decimal
        from django.db.models import Q

        self.invoice_type = 'center_monthly'
        self.monthly_fee = subscription.plan.monthly_fee_try

        # Dönem belirleme
        if not period_start or not period_end:
            # Aylık fatura için mevcut ay
            from datetime import date
            current_date = date.today()
            period_start = date(current_date.year, current_date.month, 1)
            if current_date.month == 12:
                period_end = date(current_date.year + 1, 1, 1)
            else:
                period_end = date(current_date.year, current_date.month + 1, 1)

        # Bu dönemde tamamlanan kalıpları al
        completed_molds = subscription.user.molds.filter(
            Q(status='delivered') | Q(status='completed'),
            created_at__gte=period_start,
            created_at__lt=period_end
        )

        # Kullanım sayılarını hesapla
        self.physical_mold_count = completed_molds.filter(is_physical_shipment=True).count()
        self.digital_scan_count = completed_molds.filter(is_physical_shipment=False).count()

        # Maliyet hesapla
        self.physical_mold_cost = subscription.plan.per_mold_price_try * self.physical_mold_count
        self.digital_scan_cost = subscription.plan.modeling_service_fee_try * self.digital_scan_count

        # Ara toplam
        self.subtotal = self.monthly_fee + self.physical_mold_cost + self.digital_scan_cost

        # KK komisyonu (varsa)
        if self.invoice_type == 'center_pay_per_use':
            self.credit_card_fee = self.subtotal * Decimal('0.026')  # %2.6

        # Toplam
        self.total_amount = self.subtotal + self.credit_card_fee
        self.net_amount = self.total_amount  # Center için kesinti yok

        # İşlem kırılımlarını kaydet
        self.breakdown_data = {
            'monthly_fee': float(self.monthly_fee),
            'physical_molds': {
                'count': self.physical_mold_count,
                'unit_price': float(subscription.plan.per_mold_price_try),
                'total': float(self.physical_mold_cost)
            },
            'digital_scans': {
                'count': self.digital_scan_count,
                'unit_price': float(subscription.plan.modeling_service_fee_try),
                'total': float(self.digital_scan_cost)
            },
            'credit_card_fee': float(self.credit_card_fee),
            'period': {
                'start': period_start.isoformat(),
                'end': period_end.isoformat()
            }
        }

        # Geriye dönük uyumluluk
        self.mold_count = self.physical_mold_count
        self.mold_cost = self.physical_mold_cost
        self.modeling_count = self.digital_scan_count
        self.modeling_cost = self.digital_scan_cost

        # MoldPark sistem komisyonu %7.5 (KDV DAHİL brüt tutar üzerinden)
        # subtotal zaten KDV dahil olduğu için doğrudan hesaplayabiliriz
        self.moldpark_system_fee = self.subtotal * Decimal('0.075')

        # Kredi kartı komisyonu %2.6 (KDV dahil tutar üzerinden)
        self.credit_card_fee = self.subtotal * Decimal('0.026')

        # Toplam kesintiler
        self.total_deductions = self.moldpark_system_fee + self.credit_card_fee

        # Net tutar (ödenecek tutar)
        self.net_amount = self.subtotal - self.total_deductions

        # Toplam (fatura tutarı)
        self.total_amount = self.subtotal

        return self.total_amount

    def calculate_center_admin_invoice(self, ear_mold, issued_by_center):
        """İşitme merkezi admin faturası hesapla - Kalıp gönderimi için

        Args:
            ear_mold: Kalıp nesnesi
            issued_by_center: Faturayı kesen merkez

        Returns:
            float: Toplam fatura tutarı
        """
        from decimal import Decimal

        self.invoice_type = 'center_admin_invoice'
        self.issued_by_center = issued_by_center
        
        # Aktif fiyatlandırmayı al
        pricing = PricingConfiguration.get_active()
        
        # Fiziksel kalıp - Kalıp için kaydedilmiş fiyatı kullan
        self.physical_mold_count = 1  # Her fatura bir kalıp için
        if ear_mold.unit_price is not None:
            self.physical_mold_unit_price = ear_mold.unit_price  # Kalıp için kaydedilmiş dinamik fiyat
        else:
            self.physical_mold_unit_price = pricing.physical_mold_price  # Eski kalıplar için varsayılan
        self.physical_mold_cost = self.physical_mold_unit_price
        
        # 3D Modelleme hizmeti kontrolü
        # Eğer bu kalıp için ModeledMold kaydı varsa, 3D modelleme yapılmış demektir
        has_digital_modeling = ear_mold.modeled_files.exists()
        self.digital_scan_count = 1 if has_digital_modeling else 0
        if has_digital_modeling:
            if ear_mold.digital_modeling_price is not None:
                self.digital_scan_cost = ear_mold.digital_modeling_price  # Kalıp için kaydedilmiş dinamik fiyat
            else:
                self.digital_scan_cost = pricing.digital_modeling_price  # Eski kalıplar için varsayılan
        else:
            self.digital_scan_cost = Decimal('0.00')
        
        # Aylık sistem ücreti (dinamik)
        self.monthly_fee = pricing.monthly_system_fee

        # Toplam tutar hesapla (KDV dahil)
        self.total_amount = self.monthly_fee + self.physical_mold_cost + self.digital_scan_cost
        
        # KDV'siz tutar hesapla (Toplam / 1.20)
        self.subtotal_without_vat = (self.total_amount / Decimal('1.20')).quantize(Decimal('0.01'))
        
        # KDV tutarı
        self.vat_amount = (self.total_amount - self.subtotal_without_vat).quantize(Decimal('0.01'))
        
        # Ara toplam (KDV dahil) - geriye dönük uyumluluk için
        self.subtotal = self.total_amount

        # İşitme merkezlerinden komisyon alınmıyor
        self.moldpark_service_fee = Decimal('0.00')
        self.credit_card_fee = Decimal('0.00')
        self.total_deductions = Decimal('0.00')
        
        # Net tutar (KDV dahil toplam)
        self.net_amount = self.total_amount

        # İşlem kırılımlarını kaydet
        self.breakdown_data = {
            'service_type': 'physical_mold_shipment_with_digital_modeling',
            'description': 'Fiziksel kalıp gönderimi, üretimi ve 3D modelleme hizmeti',
            'mold_details': {
                'mold_id': ear_mold.id,
                'patient_name': ear_mold.patient_name,
                'mold_type': ear_mold.get_mold_type_display(),
                'physical_unit_price': float(self.physical_mold_unit_price),
                'physical_quantity': 1,
                'physical_cost': float(self.physical_mold_cost),
                'digital_modeling': has_digital_modeling,
                'digital_unit_price': float(self.digital_scan_cost / self.digital_scan_count) if self.digital_scan_count > 0 else 19.00,
                'digital_quantity': self.digital_scan_count,
                'digital_cost': float(self.digital_scan_cost)
            },
            'fees': {
                'monthly_fee': {
                    'amount': float(self.monthly_fee),
                    'description': 'Aylık sistem kullanım ücreti'
                },
                'moldpark_service_fee': {
                    'rate': float(self.moldpark_service_fee_rate),
                    'amount': float(self.moldpark_service_fee),
                    'description': 'MoldPark platform hizmet bedeli (işitme merkezlerinden alınmaz)'
                },
                'credit_card_fee': {
                    'rate': float(self.credit_card_fee_rate),
                    'amount': float(self.credit_card_fee),
                    'description': 'Kredi kartı komisyonu (işitme merkezlerinden alınmaz)'
                }
            },
            'vat_details': {
                'subtotal_without_vat': float(self.subtotal_without_vat),
                'vat_rate': 20.0,
                'vat_amount': float(self.vat_amount),
                'total_with_vat': float(self.total_amount)
            },
            'summary': {
                'subtotal': float(self.subtotal),
                'total_fees': float(self.total_deductions),
                'total_amount': float(self.total_amount),
                'net_amount': float(self.net_amount)
            },
            'issued_by': {
                'center_name': issued_by_center.name,
                'center_id': issued_by_center.id
            }
        }

        return self.total_amount

    def calculate_producer_invoice(self, ear_mold, issued_by_producer):
        """Üretici faturası hesapla - Hizmet bedeli için

        Args:
            ear_mold: Kalıp nesnesi
            issued_by_producer: Faturayı kesen üretici

        Returns:
            float: Üreticinin alacağı tutar
        """
        from decimal import Decimal

        self.invoice_type = 'producer_invoice'
        self.issued_by_producer = issued_by_producer
        
        # Aktif fiyatlandırmayı al
        pricing = PricingConfiguration.get_active()
        
        # Kalıp için gerçek fiyatı belirle
        # Üretici her zaman gerçek kalıp fiyatını almalı (paket hakkından kullanılsa bile)
        if ear_mold.unit_price is not None and ear_mold.unit_price > 0:
            # Normal kullanım - dinamik fiyat
            physical_unit_price = ear_mold.unit_price
        else:
            # Paket hakkından kullanıldı veya fiyat kaydedilmemiş - gerçek kalıp fiyatını kullan
            # Kalıbın oluşturulduğu tarihteki subscription plan fiyatını bul
            try:
                subscription_at_time = UserSubscription.objects.filter(
                    user=ear_mold.center.user,
                    start_date__lte=ear_mold.created_at
                ).order_by('-start_date').first()
                
                if subscription_at_time and subscription_at_time.plan.per_mold_price_try:
                    physical_unit_price = subscription_at_time.plan.per_mold_price_try
                else:
                    # Fallback: Sistem fiyatı
                    physical_unit_price = pricing.physical_mold_price
            except:
                # Hata durumunda sistem fiyatı
                physical_unit_price = pricing.physical_mold_price
        
        self.physical_mold_count = 1
        self.physical_mold_unit_price = physical_unit_price
        self.physical_mold_cost = self.physical_mold_unit_price

        # Ara toplam (üreticinin kazandığı tutar)
        self.subtotal = self.physical_mold_cost

        # MoldPark hizmet bedeli kesintisi (%7.5)
        self.moldpark_service_fee = self.subtotal * (self.moldpark_service_fee_rate / Decimal('100'))

        # Kredi kartı komisyonu kesintisi (%3)
        self.credit_card_fee = self.subtotal * (self.credit_card_fee_rate / Decimal('100'))

        # Toplam kesintiler
        self.total_deductions = self.moldpark_service_fee + self.credit_card_fee

        # Net tutar (üreticinin alacağı tutar)
        self.net_amount = self.subtotal - self.total_deductions

        # Toplam fatura tutarı (ödenecek tutar)
        self.total_amount = self.net_amount

        # İşlem kırılımlarını kaydet
        self.breakdown_data = {
            'service_type': 'physical_mold_production',
            'description': 'Fiziksel kalıp üretimi ve teslimatı',
            'mold_details': {
                'mold_id': ear_mold.id,
                'patient_name': ear_mold.patient_name,
                'mold_type': ear_mold.get_mold_type_display(),
                'service_fee': float(self.physical_mold_cost),
                'center_name': ear_mold.center.name if ear_mold.center else 'N/A'
            },
            'deductions': {
                'moldpark_service_fee': {
                    'rate': float(self.moldpark_service_fee_rate),
                    'amount': float(self.moldpark_service_fee),
                    'description': 'MoldPark platform ve koordinasyon ücreti'
                },
                'credit_card_fee': {
                    'rate': float(self.credit_card_fee_rate),
                    'amount': float(self.credit_card_fee),
                    'description': 'Kredi kartı işlem komisyonu'
                }
            },
            'summary': {
                'gross_amount': float(self.subtotal),
                'total_deductions': float(self.total_deductions),
                'net_amount': float(self.net_amount),
                'moldpark_receives': float(self.total_deductions)
            },
            'issued_by': {
                'producer_name': issued_by_producer.name,
                'producer_id': issued_by_producer.id
            }
        }

        return self.net_amount

    def calculate_producer_invoice_old(self, producer, period_start=None, period_end=None):
        """Üretici kazanç faturası hesapla

        Args:
            producer: Producer nesnesi
            period_start: Dönem başlangıcı
            period_end: Dönem sonu
        """
        from decimal import Decimal
        from django.db.models import Q

        self.invoice_type = 'producer_monthly'
        self.producer = producer

        # Dönem belirleme
        if not period_start or not period_end:
            from datetime import date
            current_date = date.today()
            period_start = date(current_date.year, current_date.month, 1)
            if current_date.month == 12:
                period_end = date(current_date.year + 1, 1, 1)
            else:
                period_end = date(current_date.year, current_date.month + 1, 1)

        # Bu dönemde tamamlanan siparişleri al
        completed_orders = producer.orders.filter(
            status='delivered',
            actual_delivery__gte=period_start,
            actual_delivery__lt=period_end
        )

        self.producer_order_count = completed_orders.count()

        # Brüt geliri hesapla (tamamlanan siparişlerin toplam tutarı)
        # Not: Gerçek uygulamada siparişlerde birim fiyat bilgisi olması gerekiyor
        total_gross = 0
        order_details = []

        for order in completed_orders:
            # Sipariş başına kazanç hesapla (farklı sipariş türleri için farklı fiyatlar)
            if order.ear_mold.is_physical_shipment:
                order_revenue = Decimal('350.00')  # Fiziksel kalıp için 350 TL
            else:
                order_revenue = Decimal('150.00')  # Dijital tarama için 150 TL

            total_gross += order_revenue
            order_details.append({
                'order_id': order.id,
                'order_number': order.order_number,
                'mold_type': 'Fiziksel Kalıp' if order.ear_mold.is_physical_shipment else 'Dijital Tarama',
                'revenue': float(order_revenue),
                'completed_at': order.completed_at.isoformat() if order.completed_at else None
            })

        self.producer_gross_revenue = total_gross
        self.subtotal = total_gross

        # Komisyon kesintileri
        self.moldpark_system_fee = self.subtotal * Decimal('0.075')  # %7.5 MoldPark sistem ücreti
        self.credit_card_fee = self.subtotal * Decimal('0.026')  # %2.6 KK komisyonu

        # Toplam kesintiler
        self.total_deductions = self.moldpark_system_fee + self.credit_card_fee
        self.net_amount = self.subtotal - self.total_deductions

        # Toplam (ödenecek tutar)
        self.total_amount = self.net_amount

        # Kırılım verilerini kaydet
        self.breakdown_data = {
            'gross_revenue': float(self.producer_gross_revenue),
            'orders': order_details,
            'deductions': {
                'moldpark_system_fee': float(self.moldpark_system_fee),
                'credit_card_fee': float(self.credit_card_fee),
                'total_deductions': float(self.total_deductions)
            },
            'net_amount': float(self.net_amount),
            'period': {
                'start': period_start.isoformat(),
                'end': period_end.isoformat()
            }
        }
    
    def mark_as_sent(self, issued_by_user):
        """Faturayı gönderildi olarak işaretle"""
        if self.status in ['issued', 'draft']:
            self.status = 'sent'
            self.sent_date = timezone.now()
            self.issued_by = issued_by_user

            # Faturayı kesen kişinin rolüne göre ilişkili alanları doldur
            if hasattr(issued_by_user, 'center'):
                self.issued_by_center = issued_by_user.center
            elif hasattr(issued_by_user, 'producer'):
                self.issued_by_producer = issued_by_user.producer

            self.save()

            # Transaction oluştur (yeni sistem)
            if self.invoice_type == 'center_admin_invoice':
                # İşitme merkezi faturası - müşteri ödemesi bekleniyor
                Transaction.objects.create(
                    user=self.user,
                    center=self.issued_by_center,
                    invoice=self,
                    ear_mold=self.user.molds.filter(id=self.breakdown_data.get('mold_details', {}).get('mold_id')).first(),
                    transaction_type='center_invoice_payment',
                    amount=self.total_amount,
                    description=f'Kalıp gönderimi faturası: {self.invoice_number}',
                    reference_id=self.invoice_number,
                    service_provider=self.issued_by_center.name if self.issued_by_center else 'İşitme Merkezi',
                    service_type='Fiziksel Kalıp Üretimi',
                    amount_source=f'Müşteri: {self.user.get_full_name()}',
                    amount_destination=f'MoldPark (Tahsilat) + Üretici ({self.breakdown_data.get("summary", {}).get("producer_receives", 0)} TL)',
                    moldpark_fee_amount=self.moldpark_service_fee,
                    credit_card_fee_amount=self.credit_card_fee,
                    status='pending'
                )
            elif self.invoice_type == 'producer_invoice':
                # Üretici faturası - MoldPark ödemesi yapacak
                Transaction.objects.create(
                    user=self.user,
                    producer=self.issued_by_producer,
                    invoice=self,
                    ear_mold=self.user.molds.filter(id=self.breakdown_data.get('mold_details', {}).get('mold_id')).first(),
                    transaction_type='producer_invoice_payment',
                    amount=self.net_amount,
                    description=f'Hizmet bedeli ödemesi: {self.invoice_number}',
                    reference_id=self.invoice_number,
                    service_provider=self.issued_by_producer.name if self.issued_by_producer else 'Üretici',
                    service_type='Kalıp Üretimi',
                    amount_source='MoldPark Tahsilatı',
                    amount_destination=f'Üretici: {self.issued_by_producer.name if self.issued_by_producer else "Üretici"}',
                    moldpark_fee_amount=self.moldpark_service_fee,
                    credit_card_fee_amount=self.credit_card_fee,
                    status='pending'
                )
            else:
                # Eski sistem faturaları için
                Transaction.objects.create(
                    user=self.user,
                    producer=self.producer,
                    invoice=self,
                    transaction_type='center_monthly_fee' if 'center' in self.invoice_type else 'producer_payment',
                    amount=self.total_amount,
                    description=f'Fatura gönderildi: {self.invoice_number}',
                    reference_id=self.invoice_number,
                    status='pending'
                )

    def mark_as_paid(self, payment_method='', transaction_id=''):
        """Faturayı ödendi olarak işaretle"""
        if self.status in ['sent', 'issued']:
            self.status = 'paid'
            self.payment_date = timezone.now().date()
            self.save()

            # Transaction'ı güncelle
            transaction = self.transactions.filter(status='pending').first()
            if transaction:
                transaction.status = 'completed'
                transaction.payment_method = payment_method
                transaction.reference_id = transaction_id or self.invoice_number

                if self.invoice_type == 'center_admin_invoice':
                    transaction.description = f'Kalıp gönderimi faturası ödendi: {self.invoice_number}'
                    # MoldPark tahsilat transaction'ı oluştur
                    Transaction.objects.create(
                        user=self.user,
                        center=self.issued_by_center,
                        invoice=self,
                        ear_mold=transaction.ear_mold,
                        transaction_type='moldpark_collection',
                        amount=self.total_amount,
                        description=f'MoldPark tahsilatı - Kalıp gönderimi: {self.invoice_number}',
                        reference_id=self.invoice_number,
                        service_provider='MoldPark',
                        service_type='Tahsilat',
                        amount_source=f'Müşteri: {self.user.get_full_name()}',
                        amount_destination='MoldPark Hesabı',
                        moldpark_fee_amount=self.moldpark_service_fee,
                        credit_card_fee_amount=self.credit_card_fee,
                        status='completed'
                    )
                    # Üreticiye ödeme transaction'ı oluştur
                    producer_amount = self.breakdown_data.get('summary', {}).get('producer_receives', 0)
                    if producer_amount > 0:
                        Transaction.objects.create(
                            user=self.user,
                            center=self.issued_by_center,
                            invoice=self,
                            ear_mold=transaction.ear_mold,
                            transaction_type='moldpark_payment',
                            amount=producer_amount,
                            description=f'Üreticiye ödeme - Kalıp üretimi: {self.invoice_number}',
                            reference_id=self.invoice_number,
                            service_provider='MoldPark',
                            service_type='Ödeme',
                            amount_source='MoldPark Tahsilatı',
                            amount_destination=f'Üretici ({producer_amount} TL)',
                            status='pending'  # Üreticiye ödenene kadar pending
                        )
                elif self.invoice_type == 'producer_invoice':
                    transaction.description = f'Hizmet bedeli ödendi: {self.invoice_number}'
                else:
                    transaction.description = f'Fatura ödendi: {self.invoice_number}'

                transaction.save()

    def get_status_color(self):
        """Duruma göre renk sınıfı döndür"""
        status_colors = {
            'draft': 'secondary',
            'issued': 'warning',
            'sent': 'info',
            'paid': 'success',
            'overdue': 'danger',
            'cancelled': 'secondary',
            'refunded': 'dark'
        }
        return status_colors.get(self.status, 'secondary')

    def is_overdue(self):
        """Faturanın vadesi geçmiş mi kontrol et"""
        if self.status in ['paid', 'cancelled', 'refunded']:
            return False
        return timezone.now().date() > self.due_date
    
    def mark_as_overdue(self):
        """Faturayı vadesi geçmiş olarak işaretle"""
        if self.status == 'issued' and self.due_date < timezone.now().date():
            self.status = 'overdue'
            self.save()
            return True
        return False
    
    @staticmethod
    def generate_invoice_number(invoice_type):
        """Fatura numarası oluştur"""
        if invoice_type == 'center_admin':
            prefix = 'CAD'  # Center Admin Invoice
        elif invoice_type == 'producer':
            prefix = 'PRD'  # Producer Invoice
        elif invoice_type == 'center':
            prefix = 'CTR'  # Center Invoice (eski)
        else:
            prefix = 'INV'  # General Invoice

        date_part = timezone.now().strftime('%Y%m')

        # Bu ay için son fatura numarasını bul
        last_invoice = Invoice.objects.filter(
            invoice_number__startswith=f'{prefix}{date_part}'
        ).order_by('-invoice_number').first()

        if last_invoice:
            # Son numarayı al ve 1 artır
            last_num = int(last_invoice.invoice_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1

        return f'{prefix}{date_part}{new_num:04d}'


class FinancialSummary(models.Model):
    """Aylık Mali Özet"""
    
    # Dönem
    year = models.IntegerField('Yıl')
    month = models.IntegerField('Ay')
    
    # İşitme Merkezleri Gelirleri
    center_monthly_fees = models.DecimalField('Aylık Sistem Ücretleri', max_digits=12, decimal_places=2, default=0)
    center_mold_revenue = models.DecimalField('Kalıp Gelirleri', max_digits=12, decimal_places=2, default=0)
    center_modeling_revenue = models.DecimalField('Modeleme Gelirleri', max_digits=12, decimal_places=2, default=0)
    center_total_revenue = models.DecimalField('Merkez Toplam Gelir', max_digits=12, decimal_places=2, default=0)
    
    # Üretici Gelirleri ve Komisyonlar
    producer_gross_revenue = models.DecimalField('Üretici Brüt Gelir', max_digits=12, decimal_places=2, default=0)
    moldpark_commission_revenue = models.DecimalField('MoldPark Komisyon Geliri', max_digits=12, decimal_places=2, default=0)
    producer_net_revenue = models.DecimalField('Üretici Net Gelir', max_digits=12, decimal_places=2, default=0)
    
    # Kredi Kartı Komisyonları
    total_credit_card_fees = models.DecimalField('Toplam KK Komisyonu', max_digits=12, decimal_places=2, default=0)
    
    # Toplam Gelir
    total_gross_revenue = models.DecimalField('Toplam Brüt Gelir', max_digits=12, decimal_places=2, default=0)
    total_net_revenue = models.DecimalField('Toplam Net Gelir', max_digits=12, decimal_places=2, default=0)
    
    # İstatistikler
    total_centers = models.IntegerField('Toplam Merkez Sayısı', default=0)
    total_producers = models.IntegerField('Toplam Üretici Sayısı', default=0)
    total_molds = models.IntegerField('Toplam Kalıp Sayısı', default=0)
    total_modelings = models.IntegerField('Toplam Modeleme Sayısı', default=0)
    total_invoices = models.IntegerField('Toplam Fatura Sayısı', default=0)
    
    created_at = models.DateTimeField('Oluşturulma', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme', auto_now=True)
    
    class Meta:
        verbose_name = 'Mali Özet'
        verbose_name_plural = 'Mali Özetler'
        unique_together = ['year', 'month']
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f'{self.year}/{self.month:02d} - Toplam: ₺{self.total_net_revenue}'
    
    @staticmethod
    def calculate_monthly_summary(year, month):
        """Aylık mali özeti hesapla"""
        from datetime import date
        from calendar import monthrange
        
        start_date = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = date(year, month, last_day)
        
        # Bu ayki faturalar
        invoices = Invoice.objects.filter(
            issue_date__gte=start_date,
            issue_date__lte=end_date,
            status__in=['issued', 'paid']
        )
        
        summary, created = FinancialSummary.objects.get_or_create(
            year=year,
            month=month
        )
        
        # İşitme merkezi faturaları
        center_invoices = invoices.filter(invoice_type='center')
        summary.center_monthly_fees = sum(inv.monthly_fee for inv in center_invoices)
        # Yeni sistem ile eski sistemi birleştir
        summary.center_mold_revenue = sum((inv.physical_mold_cost or 0) + (inv.mold_cost or 0) for inv in center_invoices)
        summary.center_modeling_revenue = sum((inv.digital_scan_cost or 0) + (inv.modeling_cost or 0) for inv in center_invoices)
        summary.center_total_revenue = summary.center_monthly_fees + summary.center_mold_revenue + summary.center_modeling_revenue
        
        # Üretici faturaları
        producer_invoices = invoices.filter(invoice_type='producer')
        summary.producer_gross_revenue = sum(inv.producer_revenue for inv in producer_invoices)
        summary.moldpark_commission_revenue = sum(inv.moldpark_commission for inv in producer_invoices)
        summary.producer_net_revenue = sum(inv.net_amount for inv in producer_invoices)
        
        # Toplam kredi kartı komisyonları
        summary.total_credit_card_fees = sum(inv.credit_card_fee for inv in invoices)
        
        # Toplamlar
        summary.total_gross_revenue = summary.center_total_revenue + summary.producer_gross_revenue
        summary.total_net_revenue = summary.center_total_revenue + summary.moldpark_commission_revenue - summary.total_credit_card_fees
        
        # İstatistikler
        from center.models import Center
        from producer.models import Producer
        
        summary.total_centers = Center.objects.filter(is_active=True).count()
        summary.total_producers = Producer.objects.filter(is_active=True).count()
        # Yeni ve eski sistemi birleştir
        summary.total_molds = center_invoices.aggregate(
            total=models.Sum('physical_mold_count')
        )['total'] or 0
        if summary.total_molds == 0:  # Eski sistem
            summary.total_molds = center_invoices.aggregate(total=models.Sum('mold_count'))['total'] or 0
        
        summary.total_modelings = center_invoices.aggregate(
            total=models.Sum('digital_scan_count')
        )['total'] or 0
        if summary.total_modelings == 0:  # Eski sistem
            summary.total_modelings = center_invoices.aggregate(total=models.Sum('modeling_count'))['total'] or 0
        
        summary.total_invoices = invoices.count()
        
        summary.save()
        return summary


class PricingConfiguration(models.Model):
    """
    Merkezileştirilmiş Fiyatlandırma Yapısı
    Tüm fiyat ve komisyon oranları burada tanımlanır
    """
    # Temel Bilgiler
    name = models.CharField('Fiyatlandırma Adı', max_length=100, help_text='Örn: 2025 Standart Fiyatlandırma')
    description = models.TextField('Açıklama', blank=True, null=True)
    
    # Fiyatlar (KDV Dahil)
    physical_mold_price = models.DecimalField(
        'Fiziksel Kalıp Fiyatı (₺)',
        max_digits=10,
        decimal_places=2,
        default=450.00,
        help_text='KDV dahil fiziksel kalıp üretim fiyatı'
    )
    
    digital_modeling_price = models.DecimalField(
        '3D Modelleme Fiyatı (₺)',
        max_digits=10,
        decimal_places=2,
        default=19.00,
        help_text='KDV dahil 3D modelleme hizmet fiyatı'
    )
    
    monthly_system_fee = models.DecimalField(
        'Aylık Sistem Kullanım Ücreti (₺)',
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='İşitme merkezleri için aylık sabit ücret (0,00 TL = Ücretsiz)'
    )
    
    # Komisyon Oranları (Yüzde)
    moldpark_commission_rate = models.DecimalField(
        'MoldPark Hizmet Bedeli Oranı (%)',
        max_digits=5,
        decimal_places=2,
        default=7.50,
        help_text='MoldPark komisyon oranı (örn: 7.50 = %7.5)'
    )
    
    credit_card_commission_rate = models.DecimalField(
        'Kredi Kartı Komisyon Oranı (%)',
        max_digits=5,
        decimal_places=2,
        default=3.00,
        help_text='Kredi kartı işlem komisyonu (örn: 3.00 = %3)'
    )
    
    # KDV Oranı
    vat_rate = models.DecimalField(
        'KDV Oranı (%)',
        max_digits=5,
        decimal_places=2,
        default=20.00,
        help_text='Katma Değer Vergisi oranı (örn: 20.00 = %20)'
    )
    
    # Durum Bilgileri
    is_active = models.BooleanField(
        'Aktif',
        default=False,
        help_text='Sistemde aktif kullanılan fiyatlandırma (sadece bir tane aktif olabilir)'
    )
    
    effective_date = models.DateField(
        'Geçerlilik Başlangıç Tarihi',
        default=timezone.now,
        help_text='Bu fiyatların geçerli olduğu tarih'
    )
    
    # Tarihler
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_pricings',
        verbose_name='Oluşturan'
    )
    
    class Meta:
        verbose_name = 'Fiyatlandırma Yapılandırması'
        verbose_name_plural = 'Fiyatlandırma Yapılandırmaları'
        ordering = ['-effective_date', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'effective_date']),
        ]
    
    def __str__(self):
        status = " [AKTİF]" if self.is_active else ""
        return f"{self.name}{status} - {self.effective_date.strftime('%d.%m.%Y')}"
    
    def save(self, *args, **kwargs):
        """Aktif yapıldığında diğer tüm fiyatlandırmaları pasif yap"""
        if self.is_active:
            PricingConfiguration.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active(cls):
        """Aktif fiyatlandırmayı getir, yoksa default değerlerle yeni bir tane oluştur"""
        active = cls.objects.filter(is_active=True).first()
        if not active:
            # Default fiyatlandırma oluştur
            active = cls.objects.create(
                name='Varsayılan Fiyatlandırma',
                description='Sistem tarafından otomatik oluşturulan varsayılan fiyatlandırma',
                is_active=True,
                physical_mold_price=450.00,
                digital_modeling_price=19.00,
                moldpark_commission_rate=7.50,
                credit_card_commission_rate=3.00,
                vat_rate=20.00,
                monthly_system_fee=0.00
            )
        return active
    
    def get_physical_price_without_vat(self):
        """Fiziksel kalıp fiyatını KDV hariç döndür"""
        return self.physical_mold_price / (1 + self.vat_rate / 100)
    
    def get_digital_price_without_vat(self):
        """3D modelleme fiyatını KDV hariç döndür"""
        return self.digital_modeling_price / (1 + self.vat_rate / 100)
    
    def calculate_moldpark_fee(self, amount):
        """Verilen tutar üzerinden MoldPark komisyonunu hesapla"""
        return amount * (self.moldpark_commission_rate / 100)
    
    def calculate_credit_card_fee(self, amount):
        """Verilen tutar üzerinden kredi kartı komisyonunu hesapla"""
        return amount * (self.credit_card_commission_rate / 100)
    
    def calculate_vat(self, amount_without_vat):
        """KDV hariç tutar üzerinden KDV'yi hesapla"""
        return amount_without_vat * (self.vat_rate / 100)
    
    def get_net_to_producer_physical(self):
        """
        Fiziksel kalıp için üreticiye gidecek net tutarı hesapla
        Brüt - MoldPark komisyonu
        """
        gross_without_vat = self.get_physical_price_without_vat()
        moldpark_fee = self.calculate_moldpark_fee(gross_without_vat)
        return gross_without_vat - moldpark_fee
    
    def get_net_to_producer_digital(self):
        """
        3D modelleme için üreticiye gidecek net tutarı hesapla
        Brüt - MoldPark komisyonu
        """
        gross_without_vat = self.get_digital_price_without_vat()
        moldpark_fee = self.calculate_moldpark_fee(gross_without_vat)
        return gross_without_vat - moldpark_fee
    
    def get_pricing_summary(self):
        """Fiyatlandırma özetini döndür"""
        physical_without_vat = self.get_physical_price_without_vat()
        digital_without_vat = self.get_digital_price_without_vat()
        
        return {
            'physical': {
                'with_vat': self.physical_mold_price,
                'without_vat': physical_without_vat,
                'vat_amount': self.calculate_vat(physical_without_vat),
                'moldpark_fee': self.calculate_moldpark_fee(physical_without_vat),
                'credit_card_fee': self.calculate_credit_card_fee(self.physical_mold_price),
                'net_to_producer': self.get_net_to_producer_physical(),
            },
            'digital': {
                'with_vat': self.digital_modeling_price,
                'without_vat': digital_without_vat,
                'vat_amount': self.calculate_vat(digital_without_vat),
                'moldpark_fee': self.calculate_moldpark_fee(digital_without_vat),
                'credit_card_fee': self.calculate_credit_card_fee(self.digital_modeling_price),
                'net_to_producer': self.get_net_to_producer_digital(),
            },
            'rates': {
                'moldpark_commission': self.moldpark_commission_rate,
                'credit_card_commission': self.credit_card_commission_rate,
                'vat_rate': self.vat_rate,
            }
        }


class BankTransferConfiguration(models.Model):
    """Havale/EFT Ödeme Bilgileri"""
    
    bank_name = models.CharField('Banka Adı', max_length=100)
    account_holder = models.CharField('Hesap Sahibi', max_length=100)
    iban = models.CharField('IBAN', max_length=34, unique=True)
    swift_code = models.CharField('SWIFT Kodu', max_length=11, blank=True)
    branch_code = models.CharField('Şube Kodu', max_length=10, blank=True)
    account_number = models.CharField('Hesap Numarası', max_length=20, blank=True)
    
    is_active = models.BooleanField('Aktif', default=True)
    created_at = models.DateTimeField('Oluşturulma', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme', auto_now=True)
    
    class Meta:
        verbose_name = 'Havale Bilgileri'
        verbose_name_plural = 'Havale Bilgileri'
    
    def __str__(self):
        return f'{self.bank_name} - {self.iban}'


class PaymentMethod(models.Model):
    """Ödeme Yöntemi Tanımları"""
    
    PAYMENT_TYPE_CHOICES = [
        ('credit_card', 'Kredi Kartı'),
        ('bank_transfer', 'Havale/EFT'),
    ]
    
    method_type = models.CharField('Ödeme Türü', max_length=20, choices=PAYMENT_TYPE_CHOICES)
    name = models.CharField('Ödeme Yöntemi Adı', max_length=100)
    description = models.TextField('Açıklama', blank=True)
    
    # Havale için
    bank_transfer_config = models.ForeignKey(
        BankTransferConfiguration, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='payment_methods'
    )
    
    is_active = models.BooleanField('Aktif', default=True)
    is_default = models.BooleanField('Varsayılan', default=False)
    order = models.IntegerField('Sıra', default=0)
    
    class Meta:
        verbose_name = 'Ödeme Yöntemi'
        verbose_name_plural = 'Ödeme Yöntemleri'
        ordering = ['order']
    
    def __str__(self):
        return f'{self.name} ({self.get_method_type_display()})'


class Payment(models.Model):
    """Detaylı Ödeme Kaydı - İşitme Merkezi Ödeme Takibi"""
    
    STATUS_CHOICES = [
        ('pending', 'Beklemede'),
        ('confirmed', 'Onaylandı'),
        ('completed', 'Tamamlandı'),
        ('failed', 'Başarısız'),
        ('refunded', 'İade Edildi'),
    ]
    
    # İlişkiler
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments', verbose_name='Fatura')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='center_payments', verbose_name='Kullanıcı')
    
    # Ödeme Bilgileri
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, related_name='payments', verbose_name='Ödeme Yöntemi')
    amount = models.DecimalField('Tutar', max_digits=10, decimal_places=2)
    currency = models.CharField('Para Birimi', max_length=3, choices=[('TRY', 'TRY')], default='TRY')
    status = models.CharField('Durum', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Havale Bilgileri (Belge Yükleme İçin)
    receipt_file = models.FileField('Ödeme Makbuzu', upload_to='payment_receipts/', blank=True, null=True)
    bank_confirmation_number = models.CharField('Banka Referans No', max_length=50, blank=True)
    payment_date = models.DateField('Ödeme Tarihi', null=True, blank=True)
    
    # Kredi Kartı Bilgileri (Şifreleme gerekebilir)
    last_four_digits = models.CharField('Kartın Son 4 Hanesi', max_length=4, blank=True)
    transaction_id = models.CharField('İşlem ID', max_length=100, blank=True)
    
    # İyzico Ödeme Gateway Bilgileri
    iyzico_payment_id = models.CharField('İyzico Ödeme ID', max_length=100, blank=True)
    iyzico_conversation_id = models.CharField('İyzico Konuşma ID', max_length=100, blank=True)
    iyzico_token = models.CharField('İyzico Token', max_length=200, blank=True)
    iyzico_response = models.JSONField('İyzico Yanıt', blank=True, null=True)
    
    # Notlar
    notes = models.TextField('Notlar', blank=True)
    admin_notes = models.TextField('Admin Notları', blank=True)
    
    # İşlem Bilgileri
    created_at = models.DateTimeField('Oluşturulma', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme', auto_now=True)
    confirmed_at = models.DateTimeField('Onay Tarihi', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Ödeme'
        verbose_name_plural = 'Ödemeler'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.get_full_name()} - {self.amount} ₺ - {self.get_status_display()}'
    
    def confirm_payment(self):
        """Ödemeyi onaylı duruma getir"""
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        self.save()
    
    def complete_payment(self):
        """Ödemeyi tamamlandı duruma getir"""
        self.status = 'completed'
        self.invoice.mark_as_paid(
            payment_method=self.payment_method.get_method_type_display(),
            transaction_id=self.transaction_id or self.bank_confirmation_number
        )
        self.save()


@receiver(post_save, sender=Payment)
def notify_payment_update(sender, instance, created, **kwargs):
    """Ödeme güncellendiğinde bildirim gönder"""
    if not created and instance.status == 'confirmed':
        SimpleNotification.objects.create(
            user=instance.user,
            title='✅ Ödemeniz Onaylandı',
            message=f'₺{instance.amount} tutarındaki ödemeniz onaylanmıştır.',
            notification_type='success'
        )


# ========================================
# KARGO SİSTEMİ MODÜLLERİ
# ========================================

class CargoCompany(models.Model):
    """Türkiye Kargo Firmaları"""

    CARGO_COMPANY_CHOICES = [
        ('aras', 'Aras Kargo'),
        ('mng', 'MNG Kargo'),
        ('yurtici', 'Yurtiçi Kargo'),
        ('ptt', 'PTT Kargo'),
        ('surat', 'Sürat Kargo'),
        ('ups', 'UPS'),
        ('dhl', 'DHL'),
        ('other', 'Diğer'),
    ]

    name = models.CharField('Firma Adı', max_length=100, choices=CARGO_COMPANY_CHOICES)
    display_name = models.CharField('Görünen Ad', max_length=100)
    logo_url = models.URLField('Logo URL', blank=True)
    website = models.URLField('Web Sitesi', blank=True)

    # API Entegrasyonu
    api_enabled = models.BooleanField('API Aktif', default=False)
    api_key = models.CharField('API Anahtarı', max_length=255, blank=True)
    api_secret = models.CharField('API Gizli Anahtar', max_length=255, blank=True)
    api_base_url = models.URLField('API Base URL', blank=True)

    # Ücretlendirme
    base_price = models.DecimalField('Temel Ücret', max_digits=10, decimal_places=2, default=0)
    kg_price = models.DecimalField('KG Başına Ücret', max_digits=10, decimal_places=2, default=0)
    estimated_delivery_days = models.IntegerField('Tahmini Teslimat Süresi (Gün)', default=1)

    # Durum
    is_active = models.BooleanField('Aktif', default=True)
    is_default = models.BooleanField('Varsayılan', default=False)

    created_at = models.DateTimeField('Oluşturulma', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme', auto_now=True)

    class Meta:
        verbose_name = 'Kargo Firması'
        verbose_name_plural = 'Kargo Firmaları'
        ordering = ['display_name']

    def __str__(self):
        return self.display_name

    def get_tracking_url(self, tracking_number):
        """Takip numarası için takip URL'i oluştur"""
        tracking_urls = {
            'aras': f'https://www.araskargo.com.tr/tr/online-sorgulama?code={tracking_number}',
            'mng': f'https://www.mngkargo.com.tr/GonderiTakip/{tracking_number}',
            'yurtici': f'https://www.yurticikargo.com/tr/online-servisler/gonderi-sorgula?code={tracking_number}',
            'ptt': f'https://gonderitakip.ptt.gov.tr/Track',
            'surat': f'https://suratkargo.com.tr/KargoTakip.aspx?kod={tracking_number}',
            'ups': f'https://www.ups.com/track?loc=tr_TR&tracknum={tracking_number}',
            'dhl': f'https://www.dhl.com/tr-en/home/tracking.html?tracking-id={tracking_number}',
        }
        return tracking_urls.get(self.name, '#')


class CargoShipment(models.Model):
    """Kargo Gönderileri"""

    STATUS_CHOICES = [
        ('pending', 'Hazırlanıyor'),
        ('picked_up', 'Alındı'),
        ('in_transit', 'Yolda'),
        ('out_for_delivery', 'Dağıtıma Çıktı'),
        ('delivered', 'Teslim Edildi'),
        ('returned', 'İade Edildi'),
        ('cancelled', 'İptal Edildi'),
        ('failed', 'Teslim Edilemedi'),
    ]

    # İlişkiler
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='cargo_shipments', verbose_name='Fatura')
    cargo_company = models.ForeignKey(CargoCompany, on_delete=models.CASCADE, related_name='shipments', verbose_name='Kargo Firması')

    # Gönderi Bilgileri
    tracking_number = models.CharField('Takip Numarası', max_length=50, unique=True, blank=True)
    sender_name = models.CharField('Gönderen Adı', max_length=100)
    sender_address = models.TextField('Gönderen Adresi')
    sender_phone = models.CharField('Gönderen Telefon', max_length=20)

    recipient_name = models.CharField('Alıcı Adı', max_length=100)
    recipient_address = models.TextField('Alıcı Adresi')
    recipient_phone = models.CharField('Alıcı Telefon', max_length=20)

    # Paket Bilgileri
    weight_kg = models.DecimalField('Ağırlık (KG)', max_digits=6, decimal_places=2, default=0.5)
    package_count = models.IntegerField('Paket Adedi', default=1)
    description = models.TextField('İçerik Açıklaması', blank=True)

    # Maliyet
    shipping_cost = models.DecimalField('Kargo Ücreti', max_digits=10, decimal_places=2, default=0)
    declared_value = models.DecimalField('Beyan Değeri', max_digits=10, decimal_places=2, default=0)

    # Durum
    status = models.CharField('Durum', max_length=20, choices=STATUS_CHOICES, default='pending')
    status_description = models.TextField('Durum Açıklaması', blank=True)

    # Tarihler
    created_at = models.DateTimeField('Oluşturulma', auto_now_add=True)
    shipped_at = models.DateTimeField('Gönderilme Tarihi', null=True, blank=True)
    delivered_at = models.DateTimeField('Teslim Tarihi', null=True, blank=True)
    estimated_delivery = models.DateTimeField('Tahmini Teslimat', null=True, blank=True)

    # Ek Bilgiler
    notes = models.TextField('Notlar', blank=True)
    api_response = models.JSONField('API Yanıt', blank=True, null=True)

    class Meta:
        verbose_name = 'Kargo Gönderisi'
        verbose_name_plural = 'Kargo Gönderileri'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.tracking_number or "Yeni Gönderi"} - {self.cargo_company.display_name}'

    def update_status(self, new_status, description='', api_response=None):
        """Gönderi durumunu güncelle"""
        self.status = new_status
        self.status_description = description
        if api_response:
            self.api_response = api_response

        # Tarih güncellemeleri
        if new_status == 'picked_up' and not self.shipped_at:
            self.shipped_at = timezone.now()
        elif new_status == 'delivered' and not self.delivered_at:
            self.delivered_at = timezone.now()

        self.save()

    def get_tracking_url(self):
        """Takip URL'i döndür"""
        if self.tracking_number:
            return self.cargo_company.get_tracking_url(self.tracking_number)
        return None

    def calculate_cost(self):
        """Kargo maliyetini hesapla"""
        if not self.cargo_company:
            return 0

        company = self.cargo_company
        cost = company.base_price + (self.weight_kg * company.kg_price)
        return cost

    def can_update_status(self, new_status):
        """Durum geçişi geçerli mi kontrol et"""
        status_flow = {
            'pending': ['picked_up', 'cancelled'],
            'picked_up': ['in_transit', 'cancelled'],
            'in_transit': ['out_for_delivery', 'returned', 'failed'],
            'out_for_delivery': ['delivered', 'returned', 'failed'],
            'delivered': [],
            'returned': [],
            'cancelled': [],
            'failed': ['returned'],
        }
        return new_status in status_flow.get(self.status, [])


class CargoTracking(models.Model):
    """Kargo Takip Geçmişi"""

    shipment = models.ForeignKey(CargoShipment, on_delete=models.CASCADE, related_name='tracking_history', verbose_name='Gönderi')
    status = models.CharField('Durum', max_length=20, choices=CargoShipment.STATUS_CHOICES)
    description = models.TextField('Açıklama')
    location = models.CharField('Konum', max_length=100, blank=True)
    timestamp = models.DateTimeField('Tarih', default=timezone.now)

    # API'den gelen veriler
    raw_data = models.JSONField('Ham Veri', blank=True, null=True)

    class Meta:
        verbose_name = 'Kargo Takip'
        verbose_name_plural = 'Kargo Takip Geçmişi'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.shipment} - {self.get_status_display()} - {self.timestamp}'


class CargoIntegration(models.Model):
    """Kargo Firması API Entegrasyonları"""

    cargo_company = models.OneToOneField(CargoCompany, on_delete=models.CASCADE, related_name='integration', verbose_name='Kargo Firması')
    integration_type = models.CharField('Entegrasyon Türü', max_length=50, choices=[
        ('api', 'API'),
        ('webhook', 'Webhook'),
        ('manual', 'Manuel'),
    ], default='api')

    # Webhook ayarları
    webhook_url = models.URLField('Webhook URL', blank=True)
    webhook_secret = models.CharField('Webhook Gizli Anahtar', max_length=255, blank=True)

    # API ayarları
    auth_type = models.CharField('Kimlik Doğrulama Türü', max_length=20, choices=[
        ('bearer', 'Bearer Token'),
        ('basic', 'Basic Auth'),
        ('api_key', 'API Key'),
        ('oauth2', 'OAuth2'),
    ], default='api_key')

    # Test ayarları
    test_mode = models.BooleanField('Test Modu', default=True)
    test_api_key = models.CharField('Test API Anahtarı', max_length=255, blank=True)
    test_api_secret = models.CharField('Test API Gizli Anahtar', max_length=255, blank=True)

    # İstatistikler
    last_sync = models.DateTimeField('Son Senkronizasyon', null=True, blank=True)
    total_shipments = models.IntegerField('Toplam Gönderi', default=0)
    success_rate = models.DecimalField('Başarı Oranı (%)', max_digits=5, decimal_places=2, default=0)

    created_at = models.DateTimeField('Oluşturulma', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme', auto_now=True)

    class Meta:
        verbose_name = 'Kargo Entegrasyonu'
        verbose_name_plural = 'Kargo Entegrasyonları'

    def __str__(self):
        return f'{self.cargo_company.display_name} - {self.get_integration_type_display()}'
