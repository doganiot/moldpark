from django import forms
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div, Field
from .models import Producer, ProducerOrder, ProducerProductionLog, ProducerNetwork


class ProducerRegistrationForm(forms.ModelForm):
    """Üretici Merkez Kayıt Formu"""
    
    username = forms.CharField(label='Kullanıcı Adı', max_length=150)
    email = forms.EmailField(label='E-posta')
    password = forms.CharField(label='Şifre', widget=forms.PasswordInput)
    password_confirm = forms.CharField(label='Şifre Onayı', widget=forms.PasswordInput)
    
    class Meta:
        model = Producer
        fields = [
            'company_name', 'brand_name', 'description', 'producer_type',
            'address', 'phone', 'contact_email', 'website',
            'tax_number', 'trade_registry', 'established_year',
            'logo', 'certificate'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'established_year': forms.NumberInput(attrs={'min': 1900, 'max': 2024}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('username', css_class='form-group col-md-6 mb-0'),
                Column('email', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('password', css_class='form-group col-md-6 mb-0'),
                Column('password_confirm', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Div(css_class='mt-3'),
            Row(
                Column('company_name', css_class='form-group col-md-8 mb-0'),
                Column('producer_type', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('brand_name', css_class='form-group col-md-6 mb-0'),
                Column('website', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'description',
            Row(
                Column('phone', css_class='form-group col-md-4 mb-0'),
                Column('contact_email', css_class='form-group col-md-8 mb-0'),
                css_class='form-row'
            ),
            'address',
            Row(
                Column('tax_number', css_class='form-group col-md-4 mb-0'),
                Column('trade_registry', css_class='form-group col-md-4 mb-0'),
                Column('established_year', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('logo', css_class='form-group col-md-6 mb-0'),
                Column('certificate', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', 'Üretici Merkez Kaydı Oluştur', css_class='btn btn-primary btn-lg w-100 mt-3')
        )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Şifreler eşleşmiyor.')
        
        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Bu kullanıcı adı zaten kullanılıyor.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Bu e-posta adresi zaten kullanılıyor.')
        return email


class ProducerProfileForm(forms.ModelForm):
    """Üretici Profil Güncelleme Formu"""
    
    class Meta:
        model = Producer
        fields = [
            'company_name', 'brand_name', 'description', 'producer_type',
            'address', 'phone', 'contact_email', 'website',
            'tax_number', 'trade_registry', 'established_year',
            'logo', 'notification_preferences'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('company_name', css_class='form-group col-md-8 mb-0'),
                Column('producer_type', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('brand_name', css_class='form-group col-md-6 mb-0'),
                Column('website', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'description',
            Row(
                Column('phone', css_class='form-group col-md-4 mb-0'),
                Column('contact_email', css_class='form-group col-md-8 mb-0'),
                css_class='form-row'
            ),
            'address',
            Row(
                Column('tax_number', css_class='form-group col-md-4 mb-0'),
                Column('trade_registry', css_class='form-group col-md-4 mb-0'),
                Column('established_year', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'logo',
            'notification_preferences',
            Submit('submit', 'Profili Güncelle', css_class='btn btn-primary')
        )


class ProducerOrderForm(forms.ModelForm):
    """Üretici Sipariş Formu"""
    
    class Meta:
        model = ProducerOrder
        fields = [
            'center', 'ear_mold', 'priority', 'estimated_delivery',
            'producer_notes'
        ]
        widgets = {
            'estimated_delivery': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'producer_notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, producer=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if producer:
            # Sadece bu üreticinin ağındaki merkezleri göster
            self.fields['center'].queryset = producer.network_centers.filter(
                status='active',
                can_receive_orders=True
            ).values_list('center', flat=True)


class ProducerOrderUpdateForm(forms.ModelForm):
    """Sipariş Durum Güncelleme Formu"""
    
    class Meta:
        model = ProducerOrder
        fields = [
            'status', 'priority', 'estimated_delivery', 'actual_delivery',
            'shipping_company', 'tracking_number', 'shipping_cost',
            'producer_notes'
        ]
        widgets = {
            'estimated_delivery': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'actual_delivery': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'producer_notes': forms.Textarea(attrs={'rows': 3}),
        }


# ProducerMessageForm kaldırıldı - Sadece Admin Dashboard üzerinden mesajlaşma


class ProductionLogForm(forms.ModelForm):
    """Üretim Log Formu"""
    
    class Meta:
        model = ProducerProductionLog
        fields = [
            'stage', 'description', 'operator', 'duration_minutes',
            'photo', 'notes'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('stage', css_class='form-group col-md-6 mb-0'),
                Column('operator', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'description',
            Row(
                Column('duration_minutes', css_class='form-group col-md-6 mb-0'),
                Column('photo', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'notes',
            Submit('submit', 'Log Kaydet', css_class='btn btn-primary')
        )


# NetworkInviteForm kaldırıldı - Ağ yönetimi artık sadece admin tarafından yapılacak


class PhysicalMoldRegistrationForm(forms.Form):
    """Fiziksel Kalıp Kaydı Formu - Üretici tarafından oluşturulur"""
    
    # Merkez seçimi
    center = forms.ModelChoiceField(
        queryset=None,
        label='İşitme Merkezi',
        help_text='Kalıbı gönderen işitme merkezi',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Hasta Bilgileri
    patient_name = forms.CharField(
        label='Hasta Adı',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ahmet'})
    )
    patient_surname = forms.CharField(
        label='Hasta Soyadı',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Yılmaz'})
    )
    patient_age = forms.IntegerField(
        label='Hasta Yaşı',
        min_value=0,
        max_value=150,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '45'})
    )
    patient_gender = forms.ChoiceField(
        label='Cinsiyet',
        choices=[('M', 'Erkek'), ('F', 'Kadın')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Kalıp Detayları
    ear_side = forms.ChoiceField(
        label='Kulak Yönü',
        choices=[('right', 'Sağ'), ('left', 'Sol')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    mold_type = forms.ChoiceField(
        label='Kalıp Tipi',
        choices=[
            ('full', 'Tam Konka'),
            ('half', 'Yarım Konka'),
            ('skeleton', 'İskelet'),
            ('probe', 'Probe'),
            ('cic', 'CIC'),
            ('ite', 'ITE'),
            ('itc', 'ITC'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    vent_diameter = forms.FloatField(
        label='Vent Çapı (mm)',
        min_value=0.0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '2.0', 'step': '0.1'})
    )
    
    # Kargo Bilgileri
    carrier = forms.ChoiceField(
        label='Kargo Firması',
        required=False,
        choices=[
            ('', 'Seçiniz'),
            ('aras', 'Aras Kargo'),
            ('yurtici', 'Yurtiçi Kargo'),
            ('mng', 'MNG Kargo'),
            ('ptt', 'PTT Kargo'),
            ('ups', 'UPS'),
            ('dhl', 'DHL'),
            ('fedex', 'FedEx'),
            ('other', 'Diğer'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    tracking_number = forms.CharField(
        label='Takip Numarası',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kargo takip numarası'})
    )
    
    # Notlar
    notes = forms.CharField(
        label='Notlar',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Kalıp hakkında notlar...'})
    )
    producer_notes = forms.CharField(
        label='Üretici Notları',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Sipariş hakkında notlar...'})
    )
    
    # Öncelik
    priority = forms.ChoiceField(
        label='Öncelik',
        choices=[
            ('normal', 'Normal'),
            ('high', 'Yüksek'),
            ('urgent', 'Acil'),
        ],
        initial='normal',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, producer=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if producer:
            # Sadece bu üreticinin ağındaki aktif merkezleri göster
            from center.models import Center
            active_networks = producer.network_centers.filter(
                status='active',
                can_receive_orders=True
            ).values_list('center_id', flat=True)
            self.fields['center'].queryset = Center.objects.filter(id__in=active_networks)