from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    ContactMessage, Message, User, SubscriptionRequest, PricingPlan, PaymentHistory,
    Payment, PaymentMethod
)

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        labels = {
            'name': _('İsim'),
            'email': _('E-posta'),
            'subject': _('Konu'),
            'message': _('Mesaj'),
        }
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': _('Mesajınızı buraya yazın...')
            }),
            'name': forms.TextInput(attrs={
                'placeholder': _('Adınız Soyadınız')
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': _('ornek@email.com')
            }),
            'subject': forms.TextInput(attrs={
                'placeholder': _('Mesaj konusu')
            }),
        } 

class MessageForm(forms.ModelForm):
    """Mesaj Gönderme Formu"""
    
    class Meta:
        model = Message
        fields = ['subject', 'content', 'priority', 'attachment']
        labels = {
            'subject': _('Konu'),
            'content': _('Mesaj'),
            'priority': _('Öncelik'),
            'attachment': _('Dosya Eki'),
        }
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Mesaj konusu...')
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': _('Mesajınızı yazın...')
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Kullanıcı tipine göre form düzenle
        if self.user:
            if not self.user.is_superuser:
                # Merkez ve üreticiler sadece normal öncelik seçebilir
                self.fields['priority'].choices = [
                    ('normal', _('Normal')),
                    ('high', _('Yüksek'))
                ]


class AdminMessageForm(forms.ModelForm):
    """Admin Mesaj Gönderme Formu"""
    
    recipient_type = forms.ChoiceField(
        label='Alıcı Türü',
        choices=[
            ('single_center', 'Belirli İşitme Merkezi'),
            ('single_producer', 'Belirli Üretici Merkez'),
            ('all_centers', 'Tüm İşitme Merkezleri'),
            ('all_producers', 'Tüm Üretici Merkezler'),
            ('all_users', 'Tüm Kullanıcılar'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    specific_recipient = forms.ModelChoiceField(
        label='Alıcı Seç',
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Message
        fields = ['subject', 'content', 'priority', 'attachment']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mesaj konusu...'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Mesajınızı yazın...'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Tüm kullanıcıları yükle (admin hariç)
        base_queryset = User.objects.filter(is_superuser=False)
        
        # Alıcı türüne göre queryset'i filtrele
        recipient_type = None
        
        # POST veya GET verilerinden alıcı türünü al
        if self.data:  # POST verisi
            recipient_type = self.data.get('recipient_type')
        elif self.initial:  # Initial data
            recipient_type = self.initial.get('recipient_type')
        elif len(args) > 0 and isinstance(args[0], dict):  # GET verisi
            recipient_type = args[0].get('recipient_type')
            
        if recipient_type == 'single_center':
            self.fields['specific_recipient'].queryset = base_queryset.filter(center__isnull=False)
            self.fields['specific_recipient'].label = 'İşitme Merkezi Seç'
            self.fields['specific_recipient'].required = True
        elif recipient_type == 'single_producer':
            self.fields['specific_recipient'].queryset = base_queryset.filter(producer__isnull=False)
            self.fields['specific_recipient'].label = 'Üretici Merkez Seç'
            self.fields['specific_recipient'].required = True
        else:
            self.fields['specific_recipient'].queryset = base_queryset
            self.fields['specific_recipient'].required = False

    def clean(self):
        cleaned_data = super().clean()
        recipient_type = cleaned_data.get('recipient_type')
        specific_recipient = cleaned_data.get('specific_recipient')
        
        if recipient_type in ['single_center', 'single_producer'] and not specific_recipient:
            raise forms.ValidationError('Belirli bir alıcı seçmelisiniz.')
        
        return cleaned_data


class MessageReplyForm(forms.ModelForm):
    """Mesaj Cevaplama Formu"""
    
    class Meta:
        model = Message
        fields = ['content', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Cevabınızı yazın...'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, *args, **kwargs):
        self.original_message = kwargs.pop('original_message', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        reply = super().save(commit=False)
        
        if self.original_message and self.user:
            reply.sender = self.user
            reply.recipient = self.original_message.sender
            reply.reply_to = self.original_message
            reply.subject = f'Re: {self.original_message.subject}'
            
            # Mesaj tipini belirle
            if self.user.is_superuser:
                if hasattr(self.original_message.sender, 'center'):
                    reply.message_type = 'admin_to_center'
                elif hasattr(self.original_message.sender, 'producer'):
                    reply.message_type = 'admin_to_producer'
            else:
                reply.message_type = 'center_to_admin' if hasattr(self.user, 'center') else 'producer_to_admin'
            
            reply.priority = 'normal'
            
            if commit:
                reply.save()
                # Orijinal mesajı cevaplandı olarak işaretle
                self.original_message.mark_as_replied()
        
        return reply 


class SubscriptionRequestForm(forms.ModelForm):
    """Abonelik Talep Formu"""
    
    class Meta:
        model = SubscriptionRequest
        fields = ['plan', 'user_notes']
        widgets = {
            'plan': forms.Select(attrs={
                'class': 'form-select',
                'id': 'plan-select'
            }),
            'user_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Abonelik talebinizle ilgili özel notlarınız varsa yazabilirsiniz...'
            })
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Sadece aktif standard planı göster
        self.fields['plan'].queryset = PricingPlan.objects.filter(
            is_active=True,
            plan_type='standard'
        )
        
        # Plan seçimi zorunlu
        self.fields['plan'].required = True
        
        # Eğer kullanıcının beklemede talebi varsa uyarı ver
        if self.user:
            pending_requests = SubscriptionRequest.objects.filter(
                user=self.user,
                status='pending'
            )
            if pending_requests.exists():
                self.fields['plan'].help_text = "UYARI: Zaten beklemede abonelik talebiniz bulunmaktadır."
                
    def clean(self):
        cleaned_data = super().clean()
        plan = cleaned_data.get('plan')
        
        if self.user and plan:
            # Aynı plan için beklemede talep kontrolü
            existing_request = SubscriptionRequest.objects.filter(
                user=self.user,
                plan=plan,
                status='pending'
            ).exists()
            
            if existing_request:
                raise forms.ValidationError(f'{plan.name} planı için zaten beklemede bir talebiniz bulunmaktadır.')
            
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.user:
            instance.user = self.user
            
        if commit:
            instance.save()
            
        return instance


class PackagePurchaseForm(forms.Form):
    """Paket Satın Alma Formu"""
    
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Kredi Kartı'),
        ('bank_transfer', 'Havale/EFT'),
    ]
    
    plan = forms.ModelChoiceField(
        queryset=PricingPlan.objects.filter(is_active=True, plan_type__in=['package', 'single']),
        label='Paket Seçimi',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'package-select'
        })
    )
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        label='Ödeme Yöntemi',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Paketleri sıralı göster
        self.fields['plan'].queryset = PricingPlan.objects.filter(
            is_active=True, 
            plan_type__in=['package', 'single']
        ).order_by('order')
        
    def clean_plan(self):
        plan = self.cleaned_data.get('plan')
        if not plan:
            raise forms.ValidationError('Lütfen bir paket seçin.')
        return plan


class InvoicePaymentForm(forms.ModelForm):
    """Fatura Ödeme Formu"""
    
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.filter(is_active=True),
        label='Ödeme Yöntemi',
        widget=forms.RadioSelect,
        empty_label=None
    )
    
    class Meta:
        model = Payment
        fields = ['payment_method']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aktif olan ödeme yöntemlerini göster
        self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
            is_active=True
        ).order_by('order')


class CreditCardPaymentForm(forms.Form):
    """Kredi Kartı Ödeme Formu"""
    
    card_number = forms.CharField(
        label='Kart Numarası',
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1234 5678 9012 3456',
            'maxlength': '19'
        }),
        required=False  # Kredi Kartı seçildiğinde zorunlu
    )
    
    expiry_date = forms.CharField(
        label='Geçerlilik Tarihi',
        max_length=5,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'AA/YY',
            'maxlength': '5'
        }),
        required=False
    )
    
    cvv = forms.CharField(
        label='CVV',
        max_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '123',
            'maxlength': '4'
        }),
        required=False
    )
    
    cardholder_name = forms.CharField(
        label='Kart Sahibinin Adı',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'MEHMET YILMAZ'
        }),
        required=False
    )


class SubscriptionPaymentForm(forms.Form):
    """Abonelik Ödeme Formu"""
    
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Kredi Kartı'),
        ('bank_transfer', 'Havale/EFT'),
    ]
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        label='Ödeme Yöntemi',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        initial='credit_card'
    )
    
    # Kredi Kartı Alanları
    card_number = forms.CharField(
        label='Kart Numarası',
        max_length=19,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1234 5678 9012 3456',
            'maxlength': '19'
        })
    )
    
    expiry_date = forms.CharField(
        label='Geçerlilik Tarihi (AA/YY)',
        max_length=5,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12/25',
            'maxlength': '5'
        })
    )
    
    cvv = forms.CharField(
        label='CVV',
        max_length=4,
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '123',
            'maxlength': '4'
        })
    )
    
    cardholder_name = forms.CharField(
        label='Kart Sahibinin Adı',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'MEHMET YILMAZ'
        })
    )
    
    # Havale/EFT Alanları
    bank_reference_number = forms.CharField(
        label='Banka Referans Numarası',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Örn: 1234567890'
        })
    )
    
    payment_date = forms.DateField(
        label='Ödeme Tarihi',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    receipt_file = forms.FileField(
        label='Ödeme Makbuzu',
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png'
        })
    )
    
    notes = forms.CharField(
        label='Notlar (Opsiyonel)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ek bilgiler...'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        
        if payment_method == 'credit_card':
            if not cleaned_data.get('card_number'):
                raise forms.ValidationError({'card_number': 'Kart numarası gereklidir.'})
            if not cleaned_data.get('expiry_date'):
                raise forms.ValidationError({'expiry_date': 'Geçerlilik tarihi gereklidir.'})
            if not cleaned_data.get('cvv'):
                raise forms.ValidationError({'cvv': 'CVV gereklidir.'})
            if not cleaned_data.get('cardholder_name'):
                raise forms.ValidationError({'cardholder_name': 'Kart sahibinin adı gereklidir.'})
        
        elif payment_method == 'bank_transfer':
            if not cleaned_data.get('bank_reference_number'):
                raise forms.ValidationError({'bank_reference_number': 'Banka referans numarası gereklidir.'})
            if not cleaned_data.get('payment_date'):
                raise forms.ValidationError({'payment_date': 'Ödeme tarihi gereklidir.'})
        
        return cleaned_data


class BankTransferPaymentForm(forms.ModelForm):
    """Havale/EFT Ödeme Formu"""
    
    bank_confirmation_number = forms.CharField(
        label='Banka Referans Numarası',
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Örn: REF-202511-001234'
        }),
        required=False,
        help_text='Banka transferinin referans numarasını giriniz'
    )
    
    payment_date = forms.DateField(
        label='Ödeme Tarihi',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )
    
    receipt_file = forms.FileField(
        label='Ödeme Makbuzu',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png'
        }),
        required=False,
        help_text='Banka makulesinin görselini yükleyiniz (PDF, JPG, PNG)'
    )
    
    notes = forms.CharField(
        label='Notlar',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ödeme ile ilgili açıklamaları yazınız...'
        }),
        required=False
    )
    
    class Meta:
        model = Payment
        fields = ['bank_confirmation_number', 'payment_date', 'receipt_file', 'notes']