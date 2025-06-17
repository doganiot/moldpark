from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from center.models import Center
from django.core.exceptions import ValidationError
from .validators import validate_file_size

class EarMold(models.Model):
    MOLD_TYPE_CHOICES = (
        ('full', 'Tam Konka'),
        ('half', 'Yarım Konka'),
        ('skeleton', 'İskelet'),
        ('probe', 'Probe'),
        ('cic', 'CIC'),
        ('ite', 'ITE'),
        ('itc', 'ITC'),
    )
    
    # Geriye dönük uyumluluk için
    MOLD_TYPES = MOLD_TYPE_CHOICES
    
    STATUS_CHOICES = (
        ('waiting', 'Bekliyor'),
        ('processing', 'İşleniyor'),
        ('completed', 'Tamamlandı'),
        ('revision', 'Revizyon'),
        ('shipping', 'Kargoda'),
        ('delivered', 'Teslim Edildi'),
    )
    
    GENDER_CHOICES = (
        ('M', 'Erkek'),
        ('F', 'Kadın'),
    )
    
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='molds', verbose_name='Merkez')
    patient_name = models.CharField('Hasta Adı', max_length=100)
    patient_surname = models.CharField('Hasta Soyadı', max_length=100)
    patient_age = models.IntegerField('Yaş', validators=[MinValueValidator(0), MaxValueValidator(150)])
    patient_gender = models.CharField('Cinsiyet', max_length=1, choices=GENDER_CHOICES)
    mold_type = models.CharField('Kalıp Tipi', max_length=10, choices=MOLD_TYPE_CHOICES)
    vent_diameter = models.FloatField('Vent Çapı', validators=[MinValueValidator(0.0)])
    scan_file = models.FileField('Tarama Dosyası', upload_to='scans/')
    notes = models.TextField('Notlar', blank=True)
    status = models.CharField('Durum', max_length=20, choices=STATUS_CHOICES, default='waiting')
    quality_score = models.IntegerField('Kalite Puanı', validators=[MinValueValidator(0), MaxValueValidator(100)], null=True, blank=True)
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)

    class Meta:
        verbose_name = 'Kulak Kalıbı'
        verbose_name_plural = 'Kulak Kalıpları'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.patient_name} {self.patient_surname} - {self.get_mold_type_display()}'

    def get_status_color(self):
        """Durum için Bootstrap renk sınıfı döndürür"""
        color_map = {
            'waiting': 'warning',
            'processing': 'info',
            'completed': 'success',
            'revision': 'danger',
            'shipping': 'primary',
            'delivered': 'secondary',
        }
        return color_map.get(self.status, 'light')

    def get_status_display_custom(self):
        """Türkçe durum adını döndürür"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

class Revision(models.Model):
    REVISION_TYPE_CHOICES = [
        ('minor', 'Küçük Düzeltme'),
        ('major', 'Büyük Değişiklik'),
        ('remake', 'Yeniden Yapım'),
    ]
    
    mold = models.ForeignKey(EarMold, on_delete=models.CASCADE, related_name='revisions', verbose_name='Kalıp')
    revision_type = models.CharField('Revizyon Türü', max_length=10, choices=REVISION_TYPE_CHOICES, default='minor')
    description = models.TextField('Açıklama')
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)

    class Meta:
        verbose_name = 'Revizyon'
        verbose_name_plural = 'Revizyonlar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.mold} - {self.get_revision_type_display()} Revizyon {self.created_at}'

class ModeledMold(models.Model):
    ear_mold = models.ForeignKey(EarMold, on_delete=models.CASCADE, related_name='modeled_files')
    file = models.FileField(upload_to='modeled/', validators=[
        FileExtensionValidator(allowed_extensions=['stl', 'obj', 'ply']),
        validate_file_size
    ])
    notes = models.TextField(blank=True, null=True, verbose_name='Notlar')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=[
        ('waiting', 'Bekliyor'),
        ('approved', 'Onaylandı'),
        ('rejected', 'Reddedildi')
    ], default='waiting')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Modellenmiş Kalıp'
        verbose_name_plural = 'Modellenmiş Kalıplar'

    def __str__(self):
        return f"{self.ear_mold.patient_name} - {self.get_status_display()}"

    def clean(self):
        if self.file:
            if self.file.size > 52428800:  # 50MB
                raise ValidationError('Dosya boyutu 50MB\'dan büyük olamaz.')
            
            ext = self.file.name.split('.')[-1].lower()
            if ext not in ['stl', 'obj', 'ply']:
                raise ValidationError('Sadece STL, OBJ ve PLY dosyaları yüklenebilir.')

class QualityCheck(models.Model):
    mold = models.ForeignKey(EarMold, on_delete=models.CASCADE, related_name='quality_checks', verbose_name='Kalıp')
    checklist_items = models.JSONField('Kontrol Listesi')
    result = models.BooleanField('Sonuç')
    score = models.IntegerField('Puan', validators=[MinValueValidator(0), MaxValueValidator(100)])
    notes = models.TextField('Notlar', blank=True)
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)

    class Meta:
        verbose_name = 'Kalite Kontrol'
        verbose_name_plural = 'Kalite Kontroller'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.mold} - Kalite Kontrol {self.created_at}'
