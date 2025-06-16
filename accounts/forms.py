from allauth.account.forms import SignupForm
from django import forms
from center.models import Center
from producer.models import Producer

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

    # Üretici Merkez Seçimi
    producer_network = forms.ChoiceField(
        label='Üretici Merkez Seçimi',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'producer-select'
        }),
        help_text='İsteğe bağlı: Bir üretici ağına katılmak istiyorsanız seçiniz'
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
        
        # Üretici seçeneklerini yükle
        producer_choices = [('', 'Üretici ağına katılmadan devam et (MoldPark Merkez Yönetimi)')]
        try:
            # Aktif ve doğrulanmış üreticileri al
            active_producers = Producer.objects.filter(is_verified=True, is_active=True)
            
            for producer in active_producers:
                producer_choices.append((
                    producer.id, 
                    f"{producer.company_name} - {producer.get_producer_type_display()}"
                ))
        except Exception:
            pass
        
        self.fields['producer_network'].choices = producer_choices
        
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
            for field_name in ['center_name', 'phone', 'address', 'producer_network', 'email', 'password1', 'password2', 'username', 'notification_preferences']:
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
            
            # Üretici ağına katılım
            producer_id = self.cleaned_data.get('producer_network')
            if producer_id:
                try:
                    from producer.models import ProducerNetwork
                    producer = Producer.objects.get(id=producer_id, is_verified=True, is_active=True)
                    ProducerNetwork.objects.create(
                        producer=producer,
                        center=center,
                        status='active'
                    )
                except Producer.DoesNotExist:
                    pass  # Üretici bulunamadıysa sessizce devam et
                except Exception:
                    pass  # Diğer hatalar için de sessizce devam et
                    
        except Exception as e:
            # Hata durumunda kullanıcıyı sil
            user.delete()
            raise
            
        return user 