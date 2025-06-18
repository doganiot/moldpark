from django import forms
from .models import ContactMessage, Message, User

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        } 

class MessageForm(forms.ModelForm):
    """Mesaj Gönderme Formu"""
    
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
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Kullanıcı tipine göre form düzenle
        if self.user:
            if not self.user.is_superuser:
                # Merkez ve üreticiler sadece normal öncelik seçebilir
                self.fields['priority'].choices = [
                    ('normal', 'Normal'),
                    ('high', 'Yüksek')
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
        self.fields['specific_recipient'].queryset = User.objects.filter(
            is_superuser=False
        ).select_related('center', 'producer')

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