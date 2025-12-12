from django import forms
from .models import Center, Recipient, DeliveryNote, DeliveryNoteItem
from decimal import Decimal

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


class RecipientForm(forms.ModelForm):
    """Alıcı bilgileri formu"""
    class Meta:
        model = Recipient
        fields = ['company_name', 'address', 'city', 'phone', 'email', 'tax_number', 'tax_office']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'tax_number': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_office': forms.TextInput(attrs={'class': 'form-control'}),
        }


class DeliveryNoteItemForm(forms.ModelForm):
    """İrsaliye kalemi formu"""
    class Meta:
        model = DeliveryNoteItem
        fields = ['cinsi', 'miktar', 'birim_fiyat', 'tutari', 'order']
        widgets = {
            'cinsi': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'miktar': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '200', 'required': True}),
            'birim_fiyat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'tutari': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'readonly': True}),
            'order': forms.HiddenInput(),
        }


class DeliveryNoteForm(forms.ModelForm):
    """Sevk İrsaliyesi formu"""
    recipient_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    
    class Meta:
        model = DeliveryNote
        fields = ['recipient_company_name', 'recipient_address', 'recipient_city', 'recipient_phone', 'issue_date', 'notes']
        widgets = {
            'recipient_company_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'recipient_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),
            'recipient_city': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }