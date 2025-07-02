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
        if self.is_broadcast:
            return f'[TOPLU] {self.subject} - {self.sender.get_full_name()}'
        return f'{self.subject} - {self.sender.get_full_name()} → {self.recipient.get_full_name() if self.recipient else "Toplu"}'

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
        if (hasattr(user, 'center') or hasattr(user, 'producer')) and self.sender.is_superuser:
            return True
            
        return False


class MessageRecipient(models.Model):
    """Toplu Mesajlar için Alıcı Listesi"""
    
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='recipients')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Alıcı')
    is_read = models.BooleanField('Okundu', default=False)
    read_at = models.DateTimeField('Okunma Tarihi', blank=True, null=True)
    is_archived = models.BooleanField('Arşivlendi', default=False)

    class Meta:
        verbose_name = 'Mesaj Alıcısı'
        verbose_name_plural = 'Mesaj Alıcıları'
        unique_together = ['message', 'recipient']

    def mark_as_read(self):
        """Bu alıcı için mesajı okundu olarak işaretle"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    def __str__(self):
        return f'{self.message.subject} → {self.recipient.get_full_name()}'


class PricingPlan(models.Model):
    """Fiyatlandırma Planları"""
    
    PLAN_TYPE_CHOICES = [
        ('trial', 'Ücretsiz Deneme'),
        ('pay_per_use', 'Kullandıkça Öde'),
        ('center_basic', 'İşitme Merkezi - Temel'),
        ('center_professional', 'İşitme Merkezi - Profesyonel'),
        ('producer', 'Üretici Merkez'),
        ('enterprise', 'Kurumsal'),
    ]
    
    name = models.CharField('Plan Adı', max_length=100)
    plan_type = models.CharField('Plan Türü', max_length=20, choices=PLAN_TYPE_CHOICES, unique=True)
    description = models.TextField('Açıklama')
    
    # Fiyatlar
    price_usd = models.DecimalField('Fiyat (USD)', max_digits=10, decimal_places=2)
    price_try = models.DecimalField('Fiyat (TL)', max_digits=10, decimal_places=2)
    
    # Limitler
    monthly_model_limit = models.IntegerField('Aylık Model Limiti', null=True, blank=True, help_text='Null ise sınırsız')
    is_monthly = models.BooleanField('Aylık Plan', default=True)
    
    # Özellikler
    features = models.JSONField('Özellikler', default=list, blank=True)
    
    # Durum
    is_active = models.BooleanField('Aktif', default=True)
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)
    
    class Meta:
        verbose_name = 'Fiyatlandırma Planı'
        verbose_name_plural = 'Fiyatlandırma Planları'
        ordering = ['price_usd']
    
    def __str__(self):
        return f'{self.name} - ${self.price_usd}'
    
    def get_price_display(self):
        """Fiyat görüntüleme"""
        if self.is_monthly:
            return f'${self.price_usd}/ay (₺{self.price_try}/ay)'
        else:
            return f'${self.price_usd} (₺{self.price_try})'
    
    def get_limit_display(self):
        """Limit görüntüleme"""
        if self.plan_type == 'enterprise' or self.monthly_model_limit == -1:
            return 'İletişim Gerekli'
        elif self.monthly_model_limit == 0:
            return 'Sınırsız'
        elif self.monthly_model_limit:
            return f'{self.monthly_model_limit} kalıp/ay'
        else:
            return 'Sınırsız'


class UserSubscription(models.Model):
    """Kullanıcı Abonelikleri"""
    
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
    
    # Kullanım İstatistikleri
    models_used_this_month = models.IntegerField('Bu Ay Kullanılan Model Sayısı', default=0)
    last_reset_date = models.DateTimeField('Son Sıfırlama Tarihi', default=timezone.now)
    
    # Ödeme Bilgileri
    amount_paid = models.DecimalField('Ödenen Tutar', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField('Para Birimi', max_length=3, choices=[('USD', 'USD'), ('TRY', 'TRY')], default='USD')
    
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)
    
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
        """Model oluşturabilir mi?"""
        if not self.is_valid():
            return False
        
        # Sınırsız plan ise
        if not self.plan.monthly_model_limit:
            return True
        
        # Aylık limit kontrolü
        self.reset_monthly_usage_if_needed()
        return self.models_used_this_month < self.plan.monthly_model_limit
    
    def use_model_quota(self):
        """Model kotası kullan"""
        self.reset_monthly_usage_if_needed()
        self.models_used_this_month += 1
        self.save()
    
    def reset_monthly_usage_if_needed(self):
        """Gerekirse aylık kullanımı sıfırla"""
        now = timezone.now()
        if (now.year != self.last_reset_date.year or 
            now.month != self.last_reset_date.month):
            self.models_used_this_month = 0
            self.last_reset_date = now
            self.save()
    
    def get_remaining_models(self):
        """Kalan model sayısı"""
        if not self.plan.monthly_model_limit:
            return None  # Sınırsız
        
        self.reset_monthly_usage_if_needed()
        return max(0, self.plan.monthly_model_limit - self.models_used_this_month)


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
