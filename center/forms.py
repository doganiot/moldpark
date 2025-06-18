from django import forms
from .models import Center

class CenterProfileForm(forms.ModelForm):
    class Meta:
        model = Center
        fields = ['name', 'address', 'phone', 'notification_preferences']

# CenterMessageForm kaldırıldı - Sadece Admin Dashboard üzerinden mesajlaşma

class CenterLimitForm(forms.ModelForm):
    class Meta:
        model = Center
        fields = ['mold_limit']
        labels = {
            'mold_limit': 'Kalıp Gönderim Limiti',
        }
        widgets = {
            'mold_limit': forms.NumberInput(attrs={'min': 1, 'max': 100, 'class': 'form-control'}),
        } 