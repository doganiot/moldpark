from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from center.models import Center
from django.core.exceptions import ValidationError
from .validators import validate_file_size
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

def validate_scan_file_size(value):
    filesize = value.size
    if filesize > 104857600:  # 100MB
        raise ValidationError(_('Maksimum dosya boyutu 100MB olabilir.'))

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
    
    STATUS_CHOICES = (
        ('waiting', 'Bekliyor'),
        ('shipped_to_producer', 'Üreticiye Gönderildi'),
        ('processing', 'İşleniyor'),
        ('completed', 'Tamamlandı'),
        ('revision', 'Revizyon'),
        ('rejected', 'Reddedildi'),
        ('shipped_to_center', 'Merkeze Gönderildi'),
        ('delivered_pending_approval', 'Teslimat Onayı Bekleniyor'),
        ('delivered', 'Teslim Edildi ve Onaylandı'),
    )
    
    GENDER_CHOICES = (
        ('M', 'Erkek'),
        ('F', 'Kadın'),
    )

    EAR_SIDE_CHOICES = (
        ('right', 'Sağ'),
        ('left', 'Sol'),
    )
    
    # Kargo durumu seçenekleri
    SHIPMENT_STATUS_CHOICES = (
        ('not_shipped', 'Henüz Gönderilmedi'),
        ('shipped', 'Kargoya Verildi'),
        ('in_transit', 'Yolda'),
        ('delivered_to_producer', 'Üreticiye Teslim Edildi'),
        ('returned', 'İade Edildi'),
    )
    
    # Kargo firmaları
    CARRIER_CHOICES = (
        ('aras', 'Aras Kargo'),
        ('yurtici', 'Yurtiçi Kargo'),
        ('mng', 'MNG Kargo'),
        ('ptt', 'PTT Kargo'),
        ('ups', 'UPS'),
        ('dhl', 'DHL'),
        ('fedex', 'FedEx'),
        ('other', 'Diğer'),
    )
    
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='molds', verbose_name='Merkez')
    patient_name = models.CharField('Hasta Adı', max_length=100)
    patient_surname = models.CharField('Hasta Soyadı', max_length=100)
    patient_age = models.IntegerField('Yaş', validators=[MinValueValidator(0), MaxValueValidator(150)])
    patient_gender = models.CharField('Cinsiyet', max_length=1, choices=GENDER_CHOICES)
    ear_side = models.CharField('Kulak Yönü', max_length=5, choices=EAR_SIDE_CHOICES, default='right')
    mold_type = models.CharField('Kalıp Tipi', max_length=10, choices=MOLD_TYPE_CHOICES)
    vent_diameter = models.FloatField('Vent Çapı', validators=[MinValueValidator(0.0)])
    
    # Scan file - artık isteğe bağlı (fiziksel gönderim için)
    scan_file = models.FileField(
        'Tarama Dosyası',
        upload_to='scans/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['stl', 'obj', 'ply', 'zip', 'rar'],
                message='Sadece STL, OBJ, PLY, ZIP ve RAR dosyaları yüklenebilir.'
            ),
            validate_scan_file_size
        ],
        null=True,
        blank=True,
        help_text='STL, OBJ, PLY, ZIP veya RAR formatında tarama dosyası yükleyin (Maks. 100MB)'
    )
    
    notes = models.TextField('Notlar', blank=True)
    status = models.CharField('Durum', max_length=30, choices=STATUS_CHOICES, default='waiting')
    quality_score = models.IntegerField('Kalite Puanı', validators=[MinValueValidator(0), MaxValueValidator(100)], null=True, blank=True)
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)
    
    # Fiziksel kalıp gönderimi alanları
    is_physical_shipment = models.BooleanField('Fiziksel Kalıp Gönderimi', default=False, help_text='Dijital dosya yerine fiziksel kalıp gönderilecek')
    tracking_number = models.CharField('Kargo Takip Numarası', max_length=100, blank=True, null=True)

    # Teslimat onay sistemi
    delivery_approved_at = models.DateTimeField('Teslimat Onay Tarihi', null=True, blank=True)
    delivery_approved_by = models.ForeignKey('center.Center', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_deliveries', verbose_name='Teslimatı Onaylayan')
    delivery_notes = models.TextField('Teslimat Notları', blank=True, help_text='Teslimat onayı sırasında eklenen notlar')
    shipment_date = models.DateTimeField('Kargo Gönderim Tarihi', blank=True, null=True)
    shipment_status = models.CharField('Kargo Durumu', max_length=30, choices=SHIPMENT_STATUS_CHOICES, default='not_shipped')
    carrier_company = models.CharField('Kargo Firması', max_length=20, choices=CARRIER_CHOICES, blank=True, null=True)
    estimated_delivery = models.DateField('Tahmini Teslimat Tarihi', blank=True, null=True)
    shipment_notes = models.TextField('Kargo Notları', blank=True, help_text='Kargo ile ilgili özel talimatlar')
    
    # Öncelik ve özel talimatlar
    priority = models.CharField('Öncelik', max_length=20, default='normal', choices=[
        ('normal', 'Normal (5-7 iş günü)'),
        ('high', 'Yüksek (3-4 iş günü)'),
        ('urgent', 'Acil (1-2 iş günü)'),
    ])
    special_instructions = models.TextField('Özel Talimatlar', blank=True)
    
    # 3D Görselleştirme Alanları
    scan_thumbnail = models.ImageField(
        'Tarama Önizleme',
        upload_to='thumbnails/scans/',
        blank=True,
        null=True,
        help_text='3D tarama dosyasının küçük önizleme görseli'
    )
    model_complexity = models.CharField(
        'Model Karmaşıklığı',
        max_length=20,
        choices=[
            ('low', 'Düşük (< 10K polygon)'),
            ('medium', 'Orta (10K-50K polygon)'),
            ('high', 'Yüksek (> 50K polygon)'),
        ],
        blank=True,
        null=True
    )
    vertex_count = models.IntegerField('Vertex Sayısı', blank=True, null=True)
    polygon_count = models.IntegerField('Polygon Sayısı', blank=True, null=True)
    file_format = models.CharField('Dosya Formatı', max_length=10, blank=True, null=True)
    
    # Fiyat Bilgileri (Dinamik - kalıp oluşturulduğunda kaydedilir)
    unit_price = models.DecimalField('Birim Fiyat (TL)', max_digits=10, decimal_places=2, null=True, blank=True, help_text='Bu kalıp için kullanılan birim fiyat (paket hakkından kullanıldıysa 0)')
    digital_modeling_price = models.DecimalField('3D Modelleme Fiyatı (TL)', max_digits=10, decimal_places=2, null=True, blank=True, help_text='Bu kalıp için kullanılan 3D modelleme fiyatı')
    
    class Meta:
        verbose_name = 'Kulak Kalıbı'
        verbose_name_plural = 'Kulak Kalıpları'
        ordering = ['-created_at']

    def approve_delivery(self, center, notes=''):
        """Teslimatı onayla"""
        if self.status == 'delivered_pending_approval' and self.center == center:
            self.status = 'delivered'
            self.delivery_approved_at = timezone.now()
            self.delivery_approved_by = center
            if notes:
                self.delivery_notes = notes
            self.save()

            # Bildirim gönder
            from notifications.signals import notify
            from django.contrib.auth.models import User

            # Admin'e bildirim
            admin_users = User.objects.filter(is_superuser=True)
            for admin in admin_users:
                notify.send(
                    sender=self,
                    recipient=admin,
                    verb='teslimatı onayladı',
                    action_object=self,
                    description=f'{self.center.name} - {self.patient_name} {self.patient_surname} kalıp teslimatını onayladı.'
                )

            return True
        return False

    def __str__(self):
        return f'{self.patient_name} {self.patient_surname} - {self.get_mold_type_display()}'

    def clean(self):
        super().clean()
        # Dijital gönderim için dosya zorunlu
        if not self.is_physical_shipment and not self.scan_file:
            raise ValidationError({'scan_file': 'Dijital tarama için dosya yüklenmesi zorunludur.'})
        
        # Fiziksel gönderim için dosya isteğe bağlı
        if self.is_physical_shipment and self.scan_file:
            # Fiziksel gönderimde dosya varsa uyarı ver ama engelleme
            pass

    def save(self, *args, **kwargs):
        # Fiziksel gönderimde dosya varsa temizle
        if self.is_physical_shipment and self.scan_file:
            self.scan_file = None
        super().save(*args, **kwargs)

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
        
    def get_priority_display_custom(self):
        """Türkçe öncelik adını döndürür"""
        priority_map = {
            'normal': 'Normal (5-7 iş günü)',
            'high': 'Yüksek (3-4 iş günü)',
            'urgent': 'Acil (1-2 iş günü)',
        }
        return priority_map.get(self.priority, self.priority)
        
    def get_delivery_address(self):
        """Üretici adresini döndürür"""
        try:
            # İlk aktif üretici ağını bul
            from producer.models import ProducerNetwork
            network = ProducerNetwork.objects.filter(
                center=self.center,
                status='active'
            ).first()
            
            if network and network.producer:
                return {
                    'company': network.producer.company_name,
                    'address': network.producer.address,
                    'phone': network.producer.phone,
                    'contact_email': network.producer.contact_email
                }
        except:
            pass
        return None

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
        ('pending', 'Beklemede'),
        ('approved', 'Onaylandı'),
        ('rejected', 'Reddedildi'),
    ], default='pending', verbose_name='Durum')
    
    # 3D Görselleştirme Alanları
    model_thumbnail = models.ImageField(
        'Model Önizleme',
        upload_to='thumbnails/models/',
        blank=True,
        null=True,
        help_text='3D model dosyasının küçük önizleme görseli'
    )
    model_complexity = models.CharField(
        'Model Karmaşıklığı',
        max_length=20,
        choices=[
            ('low', 'Düşük (< 10K polygon)'),
            ('medium', 'Orta (10K-50K polygon)'),
            ('high', 'Yüksek (> 50K polygon)'),
        ],
        blank=True,
        null=True
    )
    vertex_count = models.IntegerField('Vertex Sayısı', blank=True, null=True)
    polygon_count = models.IntegerField('Polygon Sayısı', blank=True, null=True)
    file_format = models.CharField('Dosya Formatı', max_length=10, blank=True, null=True)
    render_settings = models.JSONField(
        '3D Render Ayarları',
        default=dict,
        blank=True,
        help_text='3D görüntüleyici için kamera pozisyonu, ışık ayarları vb.'
    )
    
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
    
    # Genişletilmiş status seçenekleri
    STATUS_CHOICES = [
        ('pending', 'Beklemede'),           # İşitme merkezi talepte bulundu
        ('producer_review', 'Üretici İncelemesi'),  # Üretici inceliyor
        ('accepted', 'Kabul Edildi'),       # Üretici kabul etti
        ('producer_rejected', 'Üretici Reddetti'),  # Üretici reddetti
        ('in_progress', 'İşlemde'),         # Revizyon yapılıyor
        ('quality_check', 'Kalite Kontrol'),  # Kalite kontrolde
        ('ready_for_delivery', 'Teslimat Hazır'),  # Teslimat için hazır
        ('completed', 'Tamamlandı'),        # Süreç tamamlandı
        ('cancelled', 'İptal Edildi'),      # İptal edildi
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Düşük (7-10 iş günü)'),
        ('normal', 'Normal (5-7 iş günü)'),
        ('high', 'Yüksek (3-4 iş günü)'),
        ('urgent', 'Acil (1-2 iş günü)'),
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
    status = models.CharField('Durum', max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField('Admin Notları', blank=True)
    producer_response = models.TextField('Üretici Yanıtı', blank=True)
    rejection_reason = models.TextField('Red Nedeni', blank=True)
    
    # Ek Dosyalar
    reference_image = models.ImageField('Referans Görsel', upload_to='revision_requests/', blank=True, null=True)
    attachment = models.FileField('Ek Dosya', upload_to='revision_requests/', blank=True, null=True)
    
    # Revize Edilmiş Dosyalar
    revised_file = models.FileField('Revize Edilmiş Dosya', upload_to='revised/', blank=True, null=True, validators=[
        FileExtensionValidator(allowed_extensions=['stl', 'obj', 'ply', '3mf', 'amf']),
        validate_file_size
    ])
    revision_notes = models.TextField('Revizyon Notları', blank=True, help_text='Üretici tarafından yapılan değişiklikler hakkında notlar')
    
    # Süreç Takibi - Tarihler
    created_at = models.DateTimeField('Oluşturulma Tarihi', auto_now_add=True)
    updated_at = models.DateTimeField('Güncellenme Tarihi', auto_now=True)
    admin_reviewed_at = models.DateTimeField('Admin İnceleme Tarihi', blank=True, null=True)
    producer_reviewed_at = models.DateTimeField('Üretici İnceleme Tarihi', blank=True, null=True)
    work_started_at = models.DateTimeField('İş Başlama Tarihi', blank=True, null=True)
    quality_checked_at = models.DateTimeField('Kalite Kontrol Tarihi', blank=True, null=True)
    completed_at = models.DateTimeField('Tamamlanma Tarihi', blank=True, null=True)
    resolved_at = models.DateTimeField('Çözülme Tarihi', blank=True, null=True)
    
    # Beklenen Teslim Tarihi
    expected_delivery = models.DateField('Beklenen Teslim Tarihi', blank=True, null=True)
    
    # Süreç Metrikleri
    total_days = models.IntegerField('Toplam Gün', default=0)
    admin_response_time = models.DurationField('Admin Yanıt Süresi', blank=True, null=True)
    producer_response_time = models.DurationField('Üretici Yanıt Süresi', blank=True, null=True)
    
    # Süreç Takibi
    process_steps = models.JSONField('Süreç Adımları', default=list, blank=True)
    
    class Meta:
        verbose_name = 'Revizyon Talebi'
        verbose_name_plural = 'Revizyon Talepleri'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at', 'status']),
        ]
    
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
            'admin_review': 'info',
            'approved': 'success', 
            'rejected': 'danger',
            'producer_review': 'primary',
            'accepted': 'success',
            'producer_rejected': 'danger',
            'in_progress': 'primary',
            'quality_check': 'info',
            'ready_for_delivery': 'success',
            'completed': 'success',
            'cancelled': 'secondary',
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
    
    def get_progress_percentage(self):
        """Süreç tamamlanma yüzdesi"""
        status_progress = {
            'pending': 10,
            'producer_review': 30,
            'accepted': 40,
            'producer_rejected': 0,
            'in_progress': 60,
            'quality_check': 80,
            'ready_for_delivery': 90,
            'completed': 100,
            'cancelled': 0,
        }
        return status_progress.get(self.status, 0)
    
    def get_expected_completion_date(self):
        """Beklenen tamamlanma tarihi"""
        if self.expected_delivery:
            return self.expected_delivery
        
        priority_days = {
            'low': 10,
            'normal': 7,
            'high': 4,
            'urgent': 2,
        }
        
        from datetime import timedelta
        days = priority_days.get(self.priority, 7)
        return self.created_at.date() + timedelta(days=days)
    
    def is_overdue(self):
        """Süreç gecikmede mi?"""
        if self.status in ['completed', 'cancelled']:
            return False
        
        from datetime import date
        expected_date = self.get_expected_completion_date()
        return date.today() > expected_date
    
    def add_process_step(self, step_name, description="", user=None):
        """Süreç adımı ekle - harici kullanım için"""
        from django.utils import timezone
        
        # User kontrolü - string, User objesi veya None olabilir
        if user is None:
            user_name = 'System'
        elif hasattr(user, 'username'):
            user_name = user.username
        elif isinstance(user, str):
            user_name = user
        else:
            user_name = str(user)
        
        step = {
            'step': step_name,
            'description': description,
            'timestamp': timezone.now().isoformat(),
            'user': user_name,
        }
        
        if not self.process_steps:
            self.process_steps = []
        
        self.process_steps.append(step)
        self.save()
    
    def add_process_step_without_save(self, step_name, description="", user=None):
        """Süreç adımı ekle - save çağırmadan"""
        from django.utils import timezone
        
        # User kontrolü - string, User objesi veya None olabilir
        if user is None:
            user_name = 'System'
        elif hasattr(user, 'username'):
            user_name = user.username
        elif isinstance(user, str):
            user_name = user
        else:
            user_name = str(user)
        
        step = {
            'step': step_name,
            'description': description,
            'timestamp': timezone.now().isoformat(),
            'user': user_name,
        }
        
        if not self.process_steps:
            self.process_steps = []
        
        self.process_steps.append(step)
        # save() çağırma - sonsuz döngü önlemek için
        RevisionRequest.objects.filter(pk=self.pk).update(process_steps=self.process_steps)
    
    def calculate_response_times(self):
        """Yanıt sürelerini hesapla"""
        if self.producer_reviewed_at:
            self.producer_response_time = self.producer_reviewed_at - self.created_at
        
        if self.completed_at:
            self.total_days = (self.completed_at.date() - self.created_at.date()).days
    
    def save(self, *args, **kwargs):
        """Revizyon talebi kaydedilirken otomatik işlemler"""
        from django.utils import timezone
        
        # Status değişikliklerini takip et
        process_step_needed = False
        step_description = ""
        
        if self.pk:
            try:
                old_instance = RevisionRequest.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    # Status değişti - tarih güncelle
                    now = timezone.now()
                    
                    if self.status == 'producer_review':
                        self.producer_reviewed_at = now
                    elif self.status == 'in_progress':
                        self.work_started_at = now
                    elif self.status == 'quality_check':
                        self.quality_checked_at = now
                    elif self.status == 'completed':
                        self.completed_at = now
                        self.resolved_at = now
                    
                    # Süreç adımı için bilgi hazırla
                    process_step_needed = True
                    step_description = f"Status {old_instance.get_status_display()} → {self.get_status_display()}"
            except RevisionRequest.DoesNotExist:
                pass
        
        # Yanıt sürelerini hesapla
        self.calculate_response_times()
        
        # Önce kaydet
        super().save(*args, **kwargs)
        
        # Sonra süreç adımını ekle (sonsuz döngü önlemek için)
        if process_step_needed:
            self.add_process_step_without_save(step_description)
    
    def get_next_steps(self):
        """Sonraki adımları döndür"""
        next_steps = {
            'pending': ['Üretici incelemesi bekleniyor'],
            'producer_review': ['Üretici kararı bekleniyor'],
            'accepted': ['Revizyon işlemi başlayacak'],
            'producer_rejected': ['Üretici reddetti - süreç sonlandırıldı'],
            'in_progress': ['Revizyon yapılıyor'],
            'quality_check': ['Kalite kontrol ediliyor'],
            'ready_for_delivery': ['Teslimat yapılacak'],
            'completed': ['Süreç tamamlandı'],
            'cancelled': ['İptal edildi'],
        }
        return next_steps.get(self.status, [])
    
    def get_timeline_data(self):
        """Zaman çizelgesi verilerini döndür"""
        timeline = []
        
        if self.created_at:
            timeline.append({
                'date': self.created_at,
                'title': 'Revizyon Talebi Oluşturuldu',
                'description': f'{self.center.company_name} tarafından revizyon talep edildi',
                'status': 'pending',
                'icon': 'fas fa-plus',
            })
        
        if self.producer_reviewed_at:
            timeline.append({
                'date': self.producer_reviewed_at,
                'title': 'Üretici İncelemesi',
                'description': 'Üretici tarafından incelendi',
                'status': 'producer_review',
                'icon': 'fas fa-industry',
            })
        
        if self.work_started_at:
            timeline.append({
                'date': self.work_started_at,
                'title': 'İş Başladı',
                'description': 'Revizyon işlemi başladı',
                'status': 'in_progress',
                'icon': 'fas fa-tools',
            })
        
        if self.quality_checked_at:
            timeline.append({
                'date': self.quality_checked_at,
                'title': 'Kalite Kontrol',
                'description': 'Kalite kontrol yapıldı',
                'status': 'quality_check',
                'icon': 'fas fa-check-circle',
            })
        
        if self.completed_at:
            timeline.append({
                'date': self.completed_at,
                'title': 'Tamamlandı',
                'description': 'Revizyon süreci tamamlandı',
                'status': 'completed',
                'icon': 'fas fa-flag-checkered',
            })
        
        return sorted(timeline, key=lambda x: x['date'])


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
