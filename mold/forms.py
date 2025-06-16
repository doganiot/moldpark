from django import forms
from .models import EarMold, Revision, ModeledMold, QualityCheck

class EarMoldForm(forms.ModelForm):
    class Meta:
        model = EarMold
        fields = [
            'patient_name', 'patient_surname', 'patient_age', 'patient_gender',
            'mold_type', 'vent_diameter', 'scan_file', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

class RevisionForm(forms.ModelForm):
    class Meta:
        model = Revision
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class ModeledMoldForm(forms.ModelForm):
    class Meta:
        model = ModeledMold
        fields = ['file', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'})
        }
        
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            ext = file.name.split('.')[-1].lower()
            if ext not in ['stl', 'obj', 'ply']:
                raise forms.ValidationError('Sadece STL, OBJ ve PLY dosyaları yüklenebilir.')
            if file.size > 52428800:  # 50MB
                raise forms.ValidationError('Dosya boyutu 50MB\'dan büyük olamaz.')
        return file

class QualityCheckForm(forms.ModelForm):
    class Meta:
        model = QualityCheck
        fields = ['checklist_items', 'result', 'score', 'notes']
        widgets = {
            'checklist_items': forms.Textarea(attrs={'rows': 4, 'class': 'json-input'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        } 