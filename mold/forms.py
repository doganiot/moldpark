from django import forms
from django.utils.translation import gettext_lazy as _
from .models import EarMold, Revision, ModeledMold, QualityCheck, RevisionRequest, MoldEvaluation
from producer.models import Producer, ProducerNetwork
from django.core.exceptions import ValidationError

class EarMoldForm(forms.ModelForm):
    # Sipariş türü seçimi
    order_type = forms.ChoiceField(
        label=_('Sipariş Türü'),
        choices=[
            ('digital', _('Dijital Tarama (STL/OBJ/PLY dosyası)')),
            ('physical', _('Fiziksel Kalıp Gönderimi')),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='digital',
        help_text=_('Dijital tarama dosyası göndermek veya fiziksel kalıp göndermek istediğinizi seçin')
    )

    class Meta:
        model = EarMold
        fields = [
            'order_type', 'patient_name', 'patient_surname', 'patient_age', 'patient_gender',
            'ear_side', 'mold_type', 'vent_diameter', 'scan_file', 'notes', 
            'priority', 'special_instructions', 'is_physical_shipment'
        ]
        labels = {
            'patient_name': _('Hasta Adı'),
            'patient_surname': _('Hasta Soyadı'),
            'patient_age': _('Yaş'),
            'patient_gender': _('Cinsiyet'),
            'ear_side': _('Kulak Tarafı'),
            'mold_type': _('Kalıp Türü'),
            'vent_diameter': _('Vent Çapı'),
            'scan_file': _('Tarama Dosyası'),
            'notes': _('Notlar'),
            'priority': _('Öncelik'),
            'special_instructions': _('Özel Talimatlar'),
        }
        widgets = {
            'patient_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Hasta adını girin')
            }),
            'patient_surname': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': _('Hasta soyadını girin')
            }),
            'patient_age': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 150,
                'placeholder': _('Yaş')
            }),
            'patient_gender': forms.Select(attrs={'class': 'form-select'}),
            'ear_side': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'mold_type': forms.Select(attrs={'class': 'form-select'}),
            'vent_diameter': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0',
                'placeholder': '2.0'
            }),
            'scan_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.stl,.obj,.ply,.zip,.rar'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': _('Kalıp ile ilgili özel notlar...')
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'special_instructions': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': _('Üretici için özel talimatlar...')
            }),
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.center = getattr(self.user, 'center', None) if self.user else None
        super().__init__(*args, **kwargs)
        
        # Instance varsa order_type'ı set et
        if self.instance and self.instance.pk:
            if self.instance.is_physical_shipment:
                self.fields['order_type'].initial = 'physical'
            else:
                self.fields['order_type'].initial = 'digital'
        
        # Üretici ağı kontrolü
        if self.center:
            active_networks = ProducerNetwork.objects.filter(
                center=self.center,
                status='active'
            ).exists()
            
            if not active_networks:
                # Ağ yoksa formu devre dışı bırak
                for field_name, field in self.fields.items():
                    if field_name != 'order_type':  # Order type hariç tüm alanları disable et
                        field.disabled = True
                        field.help_text = '⚠️ Kalıp siparişi verebilmek için önce bir üretici ağına katılmanız gerekiyor.'
        
        # Dosya alanını dinamik yap
        self.fields['scan_file'].required = False  # Başlangıçta opsiyonel
        
    def clean(self):
        cleaned_data = super().clean()
        order_type = cleaned_data.get('order_type')
        scan_file = cleaned_data.get('scan_file')
        
        # Sipariş türüne göre validasyon
        if order_type == 'digital':
            # is_physical_shipment false olacak
            cleaned_data['is_physical_shipment'] = False
            
            if not scan_file:
                raise ValidationError({
                    'scan_file': 'Dijital tarama türü için dosya yüklenmesi zorunludur.'
                })
            elif scan_file:
                # Dosya uzantısı kontrolü
                allowed_extensions = ['stl', 'obj', 'ply', 'zip', 'rar']
                ext = scan_file.name.split('.')[-1].lower()
                if ext not in allowed_extensions:
                    raise ValidationError({
                        'scan_file': 'Sadece STL, OBJ, PLY, ZIP ve RAR dosyaları yüklenebilir.'
                    })
                
                # Dosya boyutu kontrolü (100MB)
                if scan_file.size > 104857600:  # 100MB in bytes
                    raise ValidationError({
                        'scan_file': 'Dosya boyutu 100MB\'dan büyük olamaz.'
                    })
        
        elif order_type == 'physical':
            # is_physical_shipment true olacak
            cleaned_data['is_physical_shipment'] = True
            
            # Fiziksel gönderimde dosya opsiyonel
            if scan_file:
                # Dosya yüklenmişse uyarı ver
                self.add_error(None, 
                    'Fiziksel kalıp gönderimi seçtiniz. Yüklenen dosya işlenmeyecektir.')
        
        # Üretici ağı kontrolü
        if self.center:
            active_networks = ProducerNetwork.objects.filter(
                center=self.center,
                status='active'
            ).exists()
            
            if not active_networks:
                raise ValidationError(
                    'Kalıp siparişi verebilmek için önce bir üretici ağına katılmanız gerekiyor.'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Sipariş türüne göre is_physical_shipment ayarla
        order_type = self.cleaned_data.get('order_type')
        if order_type:
            instance.is_physical_shipment = (order_type == 'physical')
        
        # Center'ı ata
        if self.center:
            instance.center = self.center
            
        if commit:
            instance.save()
            
        return instance


class PhysicalShipmentForm(forms.ModelForm):
    """Fiziksel kalıp gönderimi için kargo bilgileri formu"""
    
    class Meta:
        model = EarMold
        fields = [
            'carrier_company', 'tracking_number', 'shipment_date', 
            'estimated_delivery', 'shipment_notes'
        ]
        widgets = {
            'carrier_company': forms.Select(attrs={'class': 'form-select'}),
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
                self.fields[field].disabled = True
                self.fields[field].help_text = 'Bu kalıp dijital tarama olarak oluşturulmuş.'


class TrackingUpdateForm(forms.ModelForm):
    """Kargo takip güncelleme formu"""
    
    class Meta:
        model = EarMold
        fields = ['tracking_number', 'shipment_status', 'carrier_company', 'shipment_notes']
        widgets = {
            'tracking_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Takip numarası'
            }),
            'shipment_status': forms.Select(attrs={'class': 'form-select'}),
            'carrier_company': forms.Select(attrs={'class': 'form-select'}),
            'shipment_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Güncelleme notları...'
            }),
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
        user = kwargs.pop('user', None)
        center = kwargs.pop('center', None)
        super().__init__(*args, **kwargs)
        
        # User'dan center'ı al
        if user and hasattr(user, 'center'):
            center = user.center
            
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
                choices=[(i, str(i)) for i in range(10, 0, -1)],
                attrs={'class': 'form-select'}
            ),
            'speed_score': forms.Select(
                choices=[(i, str(i)) for i in range(10, 0, -1)],
                attrs={'class': 'form-select'}
            ),
            'communication_score': forms.Select(
                choices=[('', 'Değerlendirme Yok')] + [(i, str(i)) for i in range(10, 0, -1)],
                attrs={'class': 'form-select'}
            ),
            'packaging_score': forms.Select(
                choices=[('', 'Değerlendirme Yok')] + [(i, str(i)) for i in range(10, 0, -1)],
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
                choices=[(i, str(i)) for i in range(10, 0, -1)],
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