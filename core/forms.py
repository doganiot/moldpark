from django import forms
from django.utils.translation import gettext_lazy as _
from .models import ContactMessage, Message, User, SubscriptionRequest, PricingPlan

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
        
        # Sadece aktif planları göster (trial hariç)
        self.fields['plan'].queryset = PricingPlan.objects.filter(
            is_active=True
        ).exclude(plan_type='trial')
        
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