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
        ('rejected', 'Reddedildi'),
        ('shipping', 'Kargoda'),
        ('delivered', 'Teslim Edildi'),
    )
    
    GENDER_CHOICES = (
        ('M', 'Erkek'),
        ('F', 'Kadın'),
    )
    
    # Kargo durumu seçenekleri
    SHIPMENT_STATUS_CHOICES = (
        ('not_shipped', 'Henüz Gönderilmedi'),
        ('shipped', 'Kargoya Verildi'),
        ('in_transit', 'Yolda'),
        ('delivered_to_producer', 'Üreticiye Teslim Edildi'),
        ('returned', 'İade Edildi'),
    )
    
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='molds', verbose_name='Merkez')
    patient_name = models.CharField('Hasta Adı', max_length=100)
    patient_surname = models.CharField('Hasta Soyadı', max_length=100)
    patient_age = models.IntegerField('Yaş', validators=[MinValueValidator(0), MaxValueValidator(150)])
    patient_gender = models.CharField('Cinsiyet', max_length=1, choices=GENDER_CHOICES)
    mold_type = models.CharField('Kalıp Tipi', max_length=10, choices=MOLD_TYPE_CHOICES)
    vent_diameter = models.FloatField('Vent Çapı', validators=[MinValueValidator(0.0)])
    scan_file = models.FileField('Tarama Dosyası', upload_to='scans/', blank=True, null=True)
    notes = models.TextField('Notlar', blank=True)
    status = models.CharField('Durum', max_length=20, choices=STATUS_CHOICES, default='waiting')
    quality_score = models.IntegerField('Kalite Puanı', validators=[MinValueValidator(0), MaxValueValidator(100)], null=True, blank=True)
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)
    
    # Fiziksel kalıp gönderimi alanları
    is_physical_shipment = models.BooleanField('Fiziksel Kalıp Gönderimi', default=False, help_text='Dijital dosya yerine fiziksel kalıp gönderilecek')
    tracking_number = models.CharField('Kargo Takip Numarası', max_length=100, blank=True, null=True)
    shipment_date = models.DateTimeField('Kargo Gönderim Tarihi', blank=True, null=True)
    shipment_status = models.CharField('Kargo Durumu', max_length=30, choices=SHIPMENT_STATUS_CHOICES, default='not_shipped')
    carrier_company = models.CharField('Kargo Firması', max_length=100, blank=True, null=True)
    estimated_delivery = models.DateField('Tahmini Teslimat Tarihi', blank=True, null=True)
    shipment_notes = models.TextField('Kargo Notları', blank=True, help_text='Kargo ile ilgili özel talimatlar')
    
    # Öncelik ve özel talimatlar (formdan gelen alanlar için)
    priority = models.CharField('Öncelik', max_length=20, default='normal', choices=[
        ('normal', 'Normal'),
        ('high', 'Yüksek'),
        ('urgent', 'Acil'),
    ])
    special_instructions = models.TextField('Özel Talimatlar', blank=True)

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
            'rejected': 'dark',
            'shipping': 'primary',
            'delivered': 'secondary',
        }
        return color_map.get(self.status, 'light')

    def get_status_display_custom(self):
        """Türkçe durum adını döndürür"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
        
    def get_shipment_status_color(self):
        """Kargo durumu için Bootstrap renk sınıfı döndürür"""
        color_map = {
            'not_shipped': 'secondary',
            'shipped': 'info',
            'in_transit': 'warning',
            'delivered_to_producer': 'success',
            'returned': 'danger',
        }
        return color_map.get(self.shipment_status, 'secondary')
        
    def get_shipment_status_display_custom(self):
        """Türkçe kargo durumu adını döndürür"""
        return dict(self.SHIPMENT_STATUS_CHOICES).get(self.shipment_status, self.shipment_status)
        
    def get_priority_color(self):
        """Öncelik için Bootstrap renk sınıfı döndürür"""
        color_map = {
            'normal': 'success',
            'high': 'warning',
            'urgent': 'danger',
        }
        return color_map.get(self.priority, 'secondary')

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


class RevisionRequest(models.Model):
    """İşitme merkezlerinin kalıp revizyonu talepleri"""
    
    REVISION_TYPE_CHOICES = [
        ('size_adjustment', 'Boyut Ayarlaması'),
        ('shape_modification', 'Şekil Değişikliği'),
        ('vent_adjustment', 'Vent Ayarlaması'),
        ('surface_improvement', 'Yüzey İyileştirmesi'),
        ('fitting_issue', 'Oturma Sorunu'),
        ('comfort_issue', 'Konfor Sorunu'),
        ('quality_issue', 'Kalite Sorunu'),
        ('remake', 'Yeniden Yapım'),
        ('other', 'Diğer'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Beklemede'),
        ('accepted', 'Kabul Edildi'),
        ('rejected', 'Reddedildi'),
        ('in_progress', 'İşlemde'),
        ('completed', 'Tamamlandı'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Düşük'),
        ('normal', 'Normal'),
        ('high', 'Yüksek'),
        ('urgent', 'Acil'),
    ]
    
    # Üretici merkezden gelen kalıp dosyasına referans
    modeled_mold = models.ForeignKey(ModeledMold, on_delete=models.CASCADE, related_name='revision_requests', verbose_name='Kalıp Dosyası')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='revision_requests', verbose_name='Merkez')
    
    # Revizyon Detayları
    revision_type = models.CharField('Revizyon Türü', max_length=20, choices=REVISION_TYPE_CHOICES)
    title = models.CharField('Başlık', max_length=200)
    description = models.TextField('Detaylı Açıklama')
    priority = models.CharField('Öncelik', max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Durum Bilgileri
    status = models.CharField('Durum', max_length=15, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField('Admin Notları', blank=True)
    producer_response = models.TextField('Üretici Yanıtı', blank=True)
    
    # Ek Dosyalar
    reference_image = models.ImageField('Referans Görsel', upload_to='revision_requests/', blank=True, null=True)
    attachment = models.FileField('Ek Dosya', upload_to='revision_requests/', blank=True, null=True)
    
    # Tarihler
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)
    resolved_at = models.DateTimeField('Çözülme Tarihi', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Revizyon Talebi'
        verbose_name_plural = 'Revizyon Talepleri'
        ordering = ['-created_at']
    
    @property
    def mold(self):
        """Uyumluluk için - modeled_mold.ear_mold'a referans"""
        return self.modeled_mold.ear_mold

    def __str__(self):
        return f'{self.modeled_mold.ear_mold.patient_name} - {self.get_revision_type_display()} ({self.get_status_display()})'
    
    def get_status_color(self):
        """Bootstrap renk sınıfı döndürür"""
        color_map = {
            'pending': 'warning',
            'accepted': 'info',
            'rejected': 'danger',
            'in_progress': 'primary',
            'completed': 'success',
        }
        return color_map.get(self.status, 'secondary')
    
    def get_priority_color(self):
        """Öncelik için Bootstrap renk sınıfı döndürür"""
        color_map = {
            'low': 'secondary',
            'normal': 'primary',
            'high': 'warning',
            'urgent': 'danger',
        }
        return color_map.get(self.priority, 'primary')


class MoldEvaluation(models.Model):
    """İşitme merkezlerinin kalıp değerlendirmeleri"""
    
    mold = models.ForeignKey(EarMold, on_delete=models.CASCADE, related_name='evaluations', verbose_name='Kalıp')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='mold_evaluations', verbose_name='Merkez')
    
    # Değerlendirme Puanları (1-10 arası)
    quality_score = models.IntegerField('Kalite Puanı', validators=[MinValueValidator(1), MaxValueValidator(10)])
    speed_score = models.IntegerField('Hız Puanı', validators=[MinValueValidator(1), MaxValueValidator(10)])
    
    # Ek Değerlendirmeler
    communication_score = models.IntegerField('İletişim Puanı', validators=[MinValueValidator(1), MaxValueValidator(10)], blank=True, null=True)
    packaging_score = models.IntegerField('Paketleme Puanı', validators=[MinValueValidator(1), MaxValueValidator(10)], blank=True, null=True)
    
    # Yorum ve Notlar
    positive_feedback = models.TextField('Olumlu Geri Bildirim', blank=True)
    negative_feedback = models.TextField('Olumsuz Geri Bildirim', blank=True)
    suggestions = models.TextField('Öneriler', blank=True)
    
    # Genel Değerlendirme
    overall_satisfaction = models.IntegerField('Genel Memnuniyet', validators=[MinValueValidator(1), MaxValueValidator(10)])
    would_recommend = models.BooleanField('Tavsiye Eder misiniz?', default=True)
    
    # Tarihler
    created_at = models.DateTimeField('Değerlendirme Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)
    
    class Meta:
        verbose_name = 'Kalıp Değerlendirmesi'
        verbose_name_plural = 'Kalıp Değerlendirmeleri'
        ordering = ['-created_at']
        unique_together = ('mold', 'center')  # Her kalıp için bir merkez sadece bir değerlendirme yapabilir
    
    def __str__(self):
        return f'{self.mold} - Kalite: {self.quality_score}/10, Hız: {self.speed_score}/10'
    
    def get_average_score(self):
        """Ortalama puanı hesaplar"""
        scores = [self.quality_score, self.speed_score]
        if self.communication_score:
            scores.append(self.communication_score)
        if self.packaging_score:
            scores.append(self.packaging_score)
        return round(sum(scores) / len(scores), 1)
    
    def get_quality_color(self):
        """Kalite puanına göre renk döndürür"""
        if self.quality_score >= 8:
            return 'success'
        elif self.quality_score >= 6:
            return 'warning'
        else:
            return 'danger'
    
    def get_speed_color(self):
        """Hız puanına göre renk döndürür"""
        if self.speed_score >= 8:
            return 'success'
        elif self.speed_score >= 6:
            return 'warning'
        else:
            return 'danger'
