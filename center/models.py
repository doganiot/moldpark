from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

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

    @property
    def email(self):
        """Merkez kullanıcısının e-posta adresini döndür"""
        return self.user.email if self.user else ''


class Recipient(models.Model):
    """İrsaliye için kayıtlı alıcı bilgileri"""
    center = models.ForeignKey(
        Center,
        on_delete=models.CASCADE,
        related_name='recipients',
        verbose_name='İşitme Merkezi'
    )
    company_name = models.CharField('Firma Adı', max_length=200)
    address = models.TextField('Adres')
    city = models.CharField('Şehir', max_length=100, blank=True)
    phone = models.CharField('Telefon', max_length=20, blank=True)
    email = models.EmailField('E-posta', blank=True)
    tax_number = models.CharField('Vergi No', max_length=50, blank=True)
    tax_office = models.CharField('Vergi Dairesi', max_length=100, blank=True)
    is_active = models.BooleanField('Aktif', default=True)
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)

    class Meta:
        verbose_name = 'Alıcı'
        verbose_name_plural = 'Alıcılar'
        ordering = ['company_name']
        unique_together = [['center', 'company_name']]

    def __str__(self):
        return f"{self.company_name} - {self.center.name}"


class DeliveryNoteItem(models.Model):
    """İrsaliye kalemleri"""
    delivery_note = models.ForeignKey(
        'DeliveryNote',
        on_delete=models.CASCADE,
        related_name='note_items',
        verbose_name='Sevk İrsaliyesi',
        null=True,
        blank=True
    )
    cinsi = models.CharField('Cinsi', max_length=200)
    miktar = models.DecimalField('Miktar', max_digits=10, decimal_places=2, default=1)
    birim_fiyat = models.DecimalField('Birim Fiyat', max_digits=10, decimal_places=2, default=0)
    tutari = models.DecimalField('Tutarı', max_digits=10, decimal_places=2, default=0)
    order = models.IntegerField('Sıra', default=0)

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        """Tutarı otomatik hesapla"""
        if not self.tutari or self.tutari == 0:
            self.tutari = self.miktar * self.birim_fiyat
        super().save(*args, **kwargs)


class DeliveryNote(models.Model):
    """Sevk İrsaliyesi"""
    center = models.ForeignKey(
        Center,
        on_delete=models.CASCADE,
        related_name='delivery_notes',
        verbose_name='İşitme Merkezi'
    )
    recipient = models.ForeignKey(
        Recipient,
        on_delete=models.SET_NULL,
        related_name='delivery_notes',
        verbose_name='Alıcı',
        null=True,
        blank=True
    )
    # Alıcı bilgileri (recipient yoksa manuel girilir)
    recipient_company_name = models.CharField('Alıcı Firma Adı', max_length=200)
    recipient_address = models.TextField('Alıcı Adres')
    recipient_city = models.CharField('Alıcı Şehir', max_length=100, blank=True)
    recipient_phone = models.CharField('Alıcı Telefon', max_length=20, blank=True)
    
    # Tarih
    issue_date = models.DateField('Tarih')
    
    # İrsaliye numarası
    note_number = models.CharField('İrsaliye No', max_length=50, unique=True, blank=True)
    
    # Notlar
    notes = models.TextField('Notlar', blank=True)
    
    # Durum
    is_draft = models.BooleanField('Taslak', default=True)
    
    # Tarihler
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)

    class Meta:
        verbose_name = 'Sevk İrsaliyesi'
        verbose_name_plural = 'Sevk İrsaliyeleri'
        ordering = ['-issue_date', '-created_at']

    def __str__(self):
        return f"İrsaliye {self.note_number} - {self.recipient_company_name}"

    def save(self, *args, **kwargs):
        """İrsaliye numarası otomatik oluştur"""
        if not self.note_number:
            from datetime import datetime
            prefix = "IRS"
            date_str = datetime.now().strftime("%Y%m%d")
            last_note = DeliveryNote.objects.filter(
                note_number__startswith=f"{prefix}-{date_str}"
            ).order_by('-note_number').first()
            
            if last_note:
                try:
                    last_num = int(last_note.note_number.split('-')[-1])
                    new_num = last_num + 1
                except:
                    new_num = 1
            else:
                new_num = 1
            
            self.note_number = f"{prefix}-{date_str}-{new_num:04d}"
        
        super().save(*args, **kwargs)

    def get_total_amount(self):
        """Toplam tutarı hesapla"""
        return sum(item.tutari for item in self.note_items.all())

# CenterMessage modeli kaldırıldı - Merkezi mesajlaşma sistemi kullanılıyor
