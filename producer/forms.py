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


class NetworkInviteForm(forms.Form):
    """Ağa Merkez Davet Formu"""
    
    center_email = forms.EmailField(label='Merkez E-posta Adresi')
    message = forms.CharField(
        label='Davet Mesajı',
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text='Merkeze gönderilecek davet mesajı (opsiyonel)'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'center_email',
            'message',
            Submit('submit', 'Davet Gönder', css_class='btn btn-primary')
        ) 