from allauth.account.forms import SignupForm
from django import forms
from center.models import Center

class CustomSignupForm(SignupForm):
    # Merkez alanları
    center_name = forms.CharField(
        max_length=100,
        label='Merkez Adı',
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Merkez adını giriniz',
            'class': 'form-control'
        })
    )
    
    phone = forms.CharField(
        max_length=20,
        label='Telefon',
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': '(5XX) XXX-XXXX',
            'class': 'form-control'
        })
    )
    
    address = forms.CharField(
        label='Adres',
        required=True,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Merkez adresini giriniz',
            'class': 'form-control'
        })
    )

    # Bildirim tercihleri
    notification_preferences = forms.MultipleChoiceField(
        choices=[
            ('new_mold', 'Yeni Kalıp Bildirimleri'),
            ('status_update', 'Durum Güncellemeleri'),
            ('revision', 'Revizyon Bildirimleri'),
            ('message', 'Yeni Mesaj Bildirimleri'),
        ],
        widget=forms.CheckboxSelectMultiple,
        label='Bildirim Tercihleri',
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        try:
            # Mevcut alanların etiketlerini Türkçeleştir (alanlar varsa)
            if 'username' in self.fields:
                self.fields['username'].label = 'Kullanıcı Adı (Opsiyonel)'
                self.fields['username'].required = False
                self.fields['username'].widget.attrs.update({'class': 'form-control'})
            if 'email' in self.fields:
                self.fields['email'].label = 'E-posta Adresi'
                self.fields['email'].required = True
                self.fields['email'].widget.attrs.update({'class': 'form-control'})
            if 'password1' in self.fields:
                self.fields['password1'].label = 'Şifre'
                self.fields['password1'].widget.attrs.update({'class': 'form-control'})
            if 'password2' in self.fields:
                self.fields['password2'].label = 'Şifre (Tekrar)'
                self.fields['password2'].widget.attrs.update({'class': 'form-control'})
            
            # Alanların sıralamasını ayarla - email'i öne al
            field_order = []
            for field_name in ['center_name', 'phone', 'address', 'email', 'password1', 'password2', 'username', 'notification_preferences']:
                if field_name in self.fields:
                    field_order.append(field_name)
            
            if field_order:
                self.order_fields(field_order)
                
        except Exception as e:
            # Hata durumunda sessizce devam et
            pass

    def save(self, request):
        # Önce kullanıcıyı kaydet
        user = super().save(request)
        
        try:
            # Merkez modelini oluştur veya güncelle
            center, created = Center.objects.get_or_create(user=user)
            center.name = self.cleaned_data['center_name']
            center.phone = self.cleaned_data['phone']
            center.address = self.cleaned_data['address']
            center.notification_preferences = self.cleaned_data.get('notification_preferences', [])
            center.save()
        except Exception as e:
            # Hata durumunda kullanıcıyı sil
            user.delete()
            raise
            
        return user 