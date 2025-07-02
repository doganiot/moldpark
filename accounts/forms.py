from allauth.account.forms import SignupForm
from django import forms
from center.models import Center
from producer.models import Producer
from notifications.signals import notify
from django.contrib.auth.models import User
from django.utils import timezone

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

    # Üretici Merkez Seçimi - ZORUNLU
    producer_network = forms.ChoiceField(
        label='Üretici Merkez Seçimi *',
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'producer-select'
        }),
        help_text='Zorunlu: Kalıp üretimi için bir üretici merkez seçmelisiniz'
    )

    # Bildirim tercihleri
    notification_preferences = forms.MultipleChoiceField(
        choices=[
            ('new_order', 'Yeni Sipariş Bildirimleri'),
            ('revision', 'Revizyon Bildirimleri'), 
            ('completed', 'Tamamlanan Sipariş'),
            ('urgent', 'Acil Durum'),
            ('system', 'Sistem Bildirimleri'),
        ],
        widget=forms.CheckboxSelectMultiple,
        label='Bildirim Tercihleri',
        required=False,
        initial=['system', 'completed', 'revision']
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Üretici seçeneklerini yükle
        producer_choices = [('', 'Lütfen bir üretici merkez seçiniz')]
        try:
            # Aktif ve doğrulanmış üreticileri al
            active_producers = Producer.objects.filter(is_verified=True, is_active=True).order_by('company_name')
            
            for producer in active_producers:
                network_count = producer.network_centers.filter(status='active').count()
                producer_choices.append((
                    producer.id, 
                    f"{producer.company_name} - {producer.get_producer_type_display()} ({network_count} aktif ağ)"
                ))
        except Exception:
            producer_choices.append(('', 'Üretici merkezler yüklenemedi'))
        
        self.fields['producer_network'].choices = producer_choices
        
        try:
            # Mevcut alanların etiketlerini Türkçeleştir
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
            
            # Alanların sıralamasını ayarla
            field_order = ['center_name', 'phone', 'address', 'producer_network', 'email', 'password1', 'password2', 'username', 'notification_preferences']
            self.order_fields(field_order)
                
        except Exception:
            pass

    def clean_producer_network(self):
        producer_id = self.cleaned_data.get('producer_network')
        if not producer_id:
            raise forms.ValidationError('Üretici merkez seçimi zorunludur.')
        
        try:
            producer = Producer.objects.get(id=producer_id, is_verified=True, is_active=True)
            return producer_id
        except Producer.DoesNotExist:
            raise forms.ValidationError('Seçilen üretici merkez geçerli değil.')

    def save(self, request):
        # Önce kullanıcıyı kaydet
        user = super().save(request)
        
        try:
            # Merkez modelini oluştur
            center = Center.objects.create(
                user=user,
                name=self.cleaned_data['center_name'],
                phone=self.cleaned_data['phone'],
                address=self.cleaned_data['address'],
                notification_preferences=self.cleaned_data.get('notification_preferences', ['system'])
            )
            
            # OTOMATIK DENEME PAKETİ VER
            from core.models import PricingPlan, UserSubscription, SimpleNotification
            try:
                # Deneme paketini al
                trial_plan = PricingPlan.objects.get(plan_type='trial', is_active=True)
                
                # Deneme aboneliği oluştur
                subscription = UserSubscription.objects.create(
                    user=user,
                    plan=trial_plan,
                    status='active',
                    models_used_this_month=0,
                    amount_paid=0,
                    currency='USD'
                )
                
                # Hoşgeldin bildirimi gönder
                SimpleNotification.objects.create(
                    user=user,
                    title='🎉 Hoş Geldiniz!',
                    message=f'Size özel {trial_plan.monthly_model_limit} kalıp gönderme hakkı hediye ettik! Platformu keşfetmeye başlayın.',
                    notification_type='success',
                    related_url='/subscription/'
                )
                
            except PricingPlan.DoesNotExist:
                # Deneme paketi yoksa normal devam et ama admin'i bilgilendir
                from django.contrib.auth.models import User as AdminUser
                admin_users = AdminUser.objects.filter(is_superuser=True)
                for admin in admin_users:
                    SimpleNotification.objects.create(
                        user=admin,
                        title='⚠️ Deneme Paketi Bulunamadı',
                        message=f'Yeni kullanıcı {user.username} için deneme paketi atanamadı. Deneme paketi oluşturulmalı.',
                        notification_type='warning',
                        related_url='/admin/core/pricingplan/'
                    )
            
            # OTOMATIK ÜRETİCİ AĞ BAĞLANTISI OLUŞTUR
            producer_id = self.cleaned_data.get('producer_network')
            if producer_id:
                from producer.models import ProducerNetwork
                producer = Producer.objects.get(id=producer_id)
                
                # Network bağlantısı oluştur
                network = ProducerNetwork.objects.create(
                    producer=producer,
                    center=center,
                    status='active',  # Direkt aktif olarak başla
                    activated_at=timezone.now(),
                    last_activity=timezone.now()
                )
                
                # ÜRETİCİYE BİLDİRİM GÖNDER
                notify.send(
                    sender=center,
                    recipient=producer.user,
                    verb=f'yeni işitme merkezi ağa katıldı',
                    action_object=center,
                    description=f'{center.name} adlı işitme merkezi ağınıza katıldı. Artık kalıp siparişleri alabilirsiniz.',
                    target=network
                )
                
                # MERKEZE BİLDİRİM GÖNDER  
                notify.send(
                    sender=producer,
                    recipient=user,
                    verb=f'üretici ağına başarıyla katıldınız',
                    action_object=producer,
                    description=f'{producer.company_name} üretici ağına başarıyla katıldınız. Artık kalıp siparişleri verebilirsiniz.',
                    target=network
                )
                
        except Exception as e:
            # Hata durumunda kullanıcıyı sil
            user.delete()
            raise
            
        return user 