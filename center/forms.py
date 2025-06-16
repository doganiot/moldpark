from django import forms
from .models import Center, CenterMessage

class CenterProfileForm(forms.ModelForm):
    class Meta:
        model = Center
        fields = ['name', 'address', 'phone', 'notification_preferences']

class CenterMessageForm(forms.ModelForm):
    class Meta:
        model = CenterMessage
        fields = ['receiver', 'subject', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Eğer kullanıcı admin/superuser ise tüm merkezleri göster
        if user and (user.is_staff or user.is_superuser):
            self.fields['receiver'].queryset = Center.objects.exclude(user=user)
        else:
            # Normal merkez kullanıcıları için sadece admin/superuser merkezleri göster
            admin_centers = Center.objects.filter(user__is_staff=True) | Center.objects.filter(user__is_superuser=True)
            self.fields['receiver'].queryset = admin_centers.distinct()
        
        # Eğer sadece bir ana merkez varsa, otomatik seçili ve gizli yap
        if self.fields['receiver'].queryset.count() == 1:
            self.fields['receiver'].initial = self.fields['receiver'].queryset.first().pk
            self.fields['receiver'].widget = forms.HiddenInput()

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