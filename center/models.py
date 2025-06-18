from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

class Center(models.Model):
    NOTIFICATION_CHOICES = (
        ('new_order', 'Yeni Sipariş'),
        ('revision', 'Revizyon'),
        ('completed', 'Tamamlanan Sipariş'),
        ('urgent', 'Acil Durum'),
        ('system', 'Sistem Bildirimleri'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='center')
    name = models.CharField('Merkez Adı', max_length=100)
    address = models.TextField('Adres')
    phone = models.CharField('Telefon', max_length=20)
    mold_limit = models.IntegerField('Kalıp Limiti', validators=[MinValueValidator(0)], default=10)
    monthly_limit = models.IntegerField('Aylık Kalıp Limiti', validators=[MinValueValidator(1)], default=50)
    notification_preferences = models.CharField('Bildirim Tercihleri', max_length=200, default='system', help_text='Virgülle ayrılmış bildirim türleri')
    is_active = models.BooleanField('Aktif', default=True)
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)
    avatar = models.ImageField('Profil Fotoğrafı', upload_to='avatars/', blank=True, null=True)

    class Meta:
        verbose_name = 'Merkez'
        verbose_name_plural = 'Merkezler'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class CenterMessage(models.Model):
    sender = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='Gönderen')
    receiver = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='received_messages', verbose_name='Alıcı')
    subject = models.CharField('Konu', max_length=200)
    message = models.TextField('Mesaj')
    is_read = models.BooleanField('Okundu', default=False)
    is_archived = models.BooleanField('Arşivlendi', default=False)
    created_at = models.DateTimeField('Gönderilme Tarihi', auto_now_add=True)

    class Meta:
        verbose_name = 'Merkez Mesajı'
        verbose_name_plural = 'Merkez Mesajları'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.sender} -> {self.receiver}: {self.subject}'
