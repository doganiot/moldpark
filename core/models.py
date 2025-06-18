from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from notifications.signals import notify
from django.utils import timezone

class ContactMessage(models.Model):
    name = models.CharField('Ad Soyad', max_length=100)
    email = models.EmailField('E-posta')
    subject = models.CharField('Konu', max_length=200)
    message = models.TextField('Mesaj')
    is_read = models.BooleanField('Okundu', default=False)
    created_at = models.DateTimeField('Gönderilme Tarihi', auto_now_add=True)

    class Meta:
        verbose_name = 'İletişim Mesajı'
        verbose_name_plural = 'İletişim Mesajları'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.subject}'

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
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField('Okundu', default=False)
    read_at = models.DateTimeField('Okunma Tarihi', blank=True, null=True)

    class Meta:
        verbose_name = 'Mesaj Alıcısı'
        verbose_name_plural = 'Mesaj Alıcıları'
        unique_together = ('message', 'recipient')

    def __str__(self):
        return f'{self.message.subject} → {self.recipient.get_full_name()}'

    def mark_as_read(self):
        """Bu alıcı için mesajı okundu olarak işaretle"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
