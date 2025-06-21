from django import forms
from .models import EarMold, Revision, ModeledMold, QualityCheck, RevisionRequest, MoldEvaluation
from producer.models import Producer, ProducerNetwork

class EarMoldForm(forms.ModelForm):
    # Sipariş türü seçimi (artık modelde is_physical_shipment ile kontrol edilecek)
    order_type = forms.ChoiceField(
        label='Sipariş Türü',
        choices=[
            ('digital', 'Dijital Tarama (STL/OBJ/PLY dosyası)'),
            ('physical', 'Fiziksel Kalıp Gönderimi'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='digital',
        help_text='Dijital tarama dosyası göndermek veya fiziksel kalıp göndermek istediğinizi seçin'
    )
    
    # Aciliyet durumu
    PRIORITY_CHOICES = [
        ('normal', 'Normal (5-7 iş günü)'),
        ('high', 'Yüksek (3-4 iş günü)'),
        ('urgent', 'Acil (1-2 iş günü)'),
    ]
    
    priority = forms.ChoiceField(
        label='Öncelik',
        choices=PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='normal',
        help_text='Sipariş önceliğini belirleyin'
    )
    
    # Özel talimatlar
    special_instructions = forms.CharField(
        label='Özel Talimatlar',
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Üretici için özel talimatlar varsa yazınız...'
        }),
        required=False
    )

    class Meta:
        model = EarMold
        fields = [
            'patient_name', 'patient_surname', 'patient_age', 'patient_gender',
            'mold_type', 'vent_diameter', 'scan_file', 'notes',
            'priority', 'special_instructions'
        ]
        widgets = {
            'patient_name': forms.TextInput(attrs={'class': 'form-control'}),
            'patient_surname': forms.TextInput(attrs={'class': 'form-control'}),
            'patient_age': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 150}),
            'patient_gender': forms.Select(attrs={'class': 'form-select'}),
            'mold_type': forms.Select(attrs={'class': 'form-select'}),
            'vent_diameter': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0'}),
            'scan_file': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'special_instructions': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Üretici için özel talimatlar varsa yazınız...'
            }),
        }
        
    def clean_scan_file(self):
        scan_file = self.cleaned_data.get('scan_file')
        order_type = self.data.get('order_type')  # form data'dan al
        
        if order_type == 'digital' and not scan_file:
            raise forms.ValidationError('Dijital tarama türü için dosya yüklenmesi zorunludur.')
        
        if scan_file:
            # Dosya uzantısı kontrolü
            allowed_extensions = ['stl', 'obj', 'ply', 'zip', 'rar']
            ext = scan_file.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise forms.ValidationError('Sadece STL, OBJ, PLY, ZIP ve RAR dosyaları yüklenebilir.')
            
            # Dosya boyutu kontrolü (100MB)
            if scan_file.size > 104857600:
                raise forms.ValidationError('Dosya boyutu 100MB\'dan büyük olamaz.')
        
        return scan_file
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # order_type'a göre is_physical_shipment ayarla
        order_type = self.data.get('order_type', 'digital')
        instance.is_physical_shipment = (order_type == 'physical')
        
        # Fiziksel gönderim ise scan_file'ı temizle
        if instance.is_physical_shipment and instance.scan_file:
            instance.scan_file = None
            
        if commit:
            instance.save()
        return instance

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Instance varsa order_type'ı set et
        if self.instance and self.instance.pk:
            if self.instance.is_physical_shipment:
                self.fields['order_type'].initial = 'physical'
            else:
                self.fields['order_type'].initial = 'digital'
        
        # Eğer merkez ağında üretici yoksa form devre dışı bırak
        if self.user and hasattr(self.user, 'center'):
            try:
                active_networks = ProducerNetwork.objects.filter(
                    center=self.user.center,
                    status='active'
                ).exists()
                
                if not active_networks:
                    for field in self.fields:
                        self.fields[field].disabled = True
                    self.fields['notes'].help_text = 'UYARI: Kalıp siparişi verebilmek için bir üretici ağına katılmanız gerekiyor.'
            except:
                pass


class PhysicalShipmentForm(forms.ModelForm):
    """Fiziksel kalıp gönderimi için kargo bilgileri formu"""
    
    class Meta:
        model = EarMold
        fields = [
            'carrier_company', 'tracking_number', 'shipment_date', 
            'estimated_delivery', 'shipment_notes'
        ]
        widgets = {
            'carrier_company': forms.Select(attrs={
                'class': 'form-select',
            }, choices=[
                ('', 'Kargo firması seçin'),
                ('aras', 'Aras Kargo'),
                ('yurtici', 'Yurtiçi Kargo'),
                ('mng', 'MNG Kargo'),
                ('ptt', 'PTT Kargo'),
                ('ups', 'UPS'),
                ('dhl', 'DHL'),
                ('fedex', 'FedEx'),
                ('other', 'Diğer'),
            ]),
            'tracking_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kargo takip numarasını girin'
            }),
            'shipment_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'estimated_delivery': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'shipment_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Kargo ile ilgili özel notlar...'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Sadece fiziksel gönderim için kullanılabilir
        if self.instance and not self.instance.is_physical_shipment:
            for field in self.fields:
                self.fields[field].widget.attrs['disabled'] = True
                
        # Kargo firması seçildiğinde otomatik tamamlama
        if self.instance and self.instance.tracking_number and not self.instance.carrier_company:
            # Takip numarasından kargo firmasını tahmin etmeye çalış
            tracking = self.instance.tracking_number.upper()
            if tracking.startswith('1Z'):
                self.fields['carrier_company'].initial = 'ups'
            elif len(tracking) == 12 and tracking.isdigit():
                self.fields['carrier_company'].initial = 'aras'
            elif len(tracking) == 10 and tracking.isdigit():
                self.fields['carrier_company'].initial = 'yurtici'


class TrackingUpdateForm(forms.ModelForm):
    """Sadece kargo takip numarası güncelleme formu"""
    
    class Meta:
        model = EarMold
        fields = ['tracking_number', 'shipment_status', 'carrier_company']
        widgets = {
            'tracking_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kargo takip numarasını girin'
            }),
            'shipment_status': forms.Select(attrs={'class': 'form-select'}),
            'carrier_company': forms.Select(attrs={
                'class': 'form-select',
            }, choices=[
                ('', 'Kargo firması seçin'),
                ('aras', 'Aras Kargo'),
                ('yurtici', 'Yurtiçi Kargo'),
                ('mng', 'MNG Kargo'),
                ('ptt', 'PTT Kargo'),
                ('ups', 'UPS'),
                ('dhl', 'DHL'),
                ('fedex', 'FedEx'),
                ('other', 'Diğer'),
            ]),
        }

class RevisionForm(forms.ModelForm):
    REVISION_TYPE_CHOICES = [
        ('minor', 'Küçük Düzeltme'),
        ('major', 'Büyük Değişiklik'),
        ('remake', 'Yeniden Yapım'),
    ]
    
    revision_type = forms.ChoiceField(
        label='Revizyon Türü',
        choices=REVISION_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='minor'
    )
    
    class Meta:
        model = Revision
        fields = ['revision_type', 'description']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'form-control',
                'placeholder': 'Revizyon detaylarını açıklayınız...'
            }),
        }

class ModeledMoldForm(forms.ModelForm):
    class Meta:
        model = ModeledMold
        fields = ['file', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'})
        }
        
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            ext = file.name.split('.')[-1].lower()
            if ext not in ['stl', 'obj', 'ply']:
                raise forms.ValidationError('Sadece STL, OBJ ve PLY dosyaları yüklenebilir.')
            if file.size > 52428800:  # 50MB
                raise forms.ValidationError('Dosya boyutu 50MB\'dan büyük olamaz.')
        return file

class QualityCheckForm(forms.ModelForm):
    class Meta:
        model = QualityCheck
        fields = ['checklist_items', 'result', 'score', 'notes']
        widgets = {
            'checklist_items': forms.Textarea(attrs={'rows': 4, 'class': 'json-input'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }


class RevisionRequestForm(forms.ModelForm):
    """Revizyon talebi formu"""
    
    class Meta:
        model = RevisionRequest
        fields = [
            'modeled_mold', 'revision_type', 'title', 'description', 'priority',
            'reference_image', 'attachment'
        ]
        widgets = {
            'modeled_mold': forms.Select(attrs={'class': 'form-select'}),
            'revision_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Revizyon talebiniz için kısa bir başlık'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Revizyon talebinizi detaylı olarak açıklayın...'
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'reference_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        center = kwargs.pop('center', None)
        super().__init__(*args, **kwargs)
        
        if center:
            # Sadece bu merkeze ait ve onaylanmış kalıp dosyalarını göster
            self.fields['modeled_mold'].queryset = ModeledMold.objects.filter(
                ear_mold__center=center,
                status='approved'
            ).select_related('ear_mold').order_by('-created_at')
            
            # Kalıp dosyası seçimi için özel label
            self.fields['modeled_mold'].label = 'Revizyon Yapılacak Kalıp Dosyası'
            self.fields['modeled_mold'].help_text = 'Üretici merkezden aldığınız hangi kalıp dosyası için revizyon talep ediyorsunuz?'
            self.fields['modeled_mold'].empty_label = 'Kalıp dosyası seçiniz...'
    
    def clean_reference_image(self):
        image = self.cleaned_data.get('reference_image')
        if image:
            # Dosya boyutu kontrolü (10MB)
            if image.size > 10485760:
                raise forms.ValidationError('Görsel boyutu 10MB\'dan büyük olamaz.')
            
            # Dosya uzantısı kontrolü
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp']
            ext = image.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise forms.ValidationError('Sadece JPG, PNG, GIF ve BMP dosyaları yüklenebilir.')
        
        return image
    
    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            # Dosya boyutu kontrolü (50MB)
            if attachment.size > 52428800:
                raise forms.ValidationError('Ek dosya boyutu 50MB\'dan büyük olamaz.')
        
        return attachment


class MoldEvaluationForm(forms.ModelForm):
    """Kalıp değerlendirme formu"""
    
    class Meta:
        model = MoldEvaluation
        fields = [
            'quality_score', 'speed_score', 'communication_score', 'packaging_score',
            'positive_feedback', 'negative_feedback', 'suggestions',
            'overall_satisfaction', 'would_recommend'
        ]
        widgets = {
            'quality_score': forms.Select(
                choices=[(i, f'{i}/10') for i in range(1, 11)],
                attrs={'class': 'form-select'}
            ),
            'speed_score': forms.Select(
                choices=[(i, f'{i}/10') for i in range(1, 11)],
                attrs={'class': 'form-select'}
            ),
            'communication_score': forms.Select(
                choices=[('', 'Değerlendirme Yok')] + [(i, f'{i}/10') for i in range(1, 11)],
                attrs={'class': 'form-select'}
            ),
            'packaging_score': forms.Select(
                choices=[('', 'Değerlendirme Yok')] + [(i, f'{i}/10') for i in range(1, 11)],
                attrs={'class': 'form-select'}
            ),
            'positive_feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Beğendiğiniz yönleri belirtiniz...'
            }),
            'negative_feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'İyileştirilebilecek yönleri belirtiniz...'
            }),
            'suggestions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Önerilerinizi yazınız...'
            }),
            'overall_satisfaction': forms.Select(
                choices=[(i, f'{i}/10') for i in range(1, 11)],
                attrs={'class': 'form-select'}
            ),
            'would_recommend': forms.Select(
                choices=[(True, 'Evet'), (False, 'Hayır')],
                attrs={'class': 'form-select'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Zorunlu alanları işaretle
        self.fields['quality_score'].help_text = 'Kalıp kalitesini 1-10 arasında değerlendirin'
        self.fields['speed_score'].help_text = 'Teslimat hızını 1-10 arasında değerlendirin'
        self.fields['overall_satisfaction'].help_text = 'Genel memnuniyetinizi 1-10 arasında değerlendirin'
        
        # Opsiyonel alanları belirt
        self.fields['communication_score'].help_text = 'İletişim kalitesini değerlendirin (opsiyonel)'
        self.fields['packaging_score'].help_text = 'Paketleme kalitesini değerlendirin (opsiyonel)'
        
        # Geri bildirim alanları
        self.fields['positive_feedback'].required = False
        self.fields['negative_feedback'].required = False
        self.fields['suggestions'].required = False 