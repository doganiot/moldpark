from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import SubscriptionRequest, UserSubscription, PricingPlan
from django.utils import timezone


class Command(BaseCommand):
    help = 'Onaylanmış talepleri yeniden işleyerek abonelik oluşturur'

    def handle(self, *args, **options):
        self.stdout.write("=== ONAYLANMIŞ TALEPLERİ YENİDEN İŞLEME ===")
        
        # Onaylanmış talepleri bul
        approved_requests = SubscriptionRequest.objects.filter(status='approved')
        
        self.stdout.write(f"Onaylanmış talep sayısı: {approved_requests.count()}")
        
        for req in approved_requests:
            self.stdout.write(f"\nİşleniyor: {req.user.username} - {req.plan.name}")
            
            # Admin kullanıcısı bul
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                self.stdout.write(self.style.ERROR("Admin kullanıcısı bulunamadı!"))
                continue
            
            # Bu kullanıcının bu plan için aktif aboneliği var mı kontrol et
            try:
                subscription = UserSubscription.objects.get(
                    user=req.user, 
                    plan=req.plan, 
                    status='active'
                )
                self.stdout.write(f"✓ Zaten aktif abonelik mevcut: {subscription.plan.name}")
                continue
            except UserSubscription.DoesNotExist:
                self.stdout.write(f"✗ Aktif abonelik yok, yeniden oluşturuluyor...")
            except UserSubscription.MultipleObjectsReturned:
                self.stdout.write(f"! Birden fazla abonelik var, düzeltiliyor...")
            
            # Talebi pending durumuna geri al ve yeniden onayla
            req.status = 'pending'
            req.save()
            
            # Yeniden onayla (güncellenmiş approve metodunu kullanacak)
            try:
                result = req.approve(admin_user, "Sistem tarafından yeniden onaylandı")
                if result:
                    self.stdout.write(f"✓ Abonelik başarıyla oluşturuldu: {result.plan.name} - {result.status}")
                else:
                    self.stdout.write(self.style.ERROR("✗ Onaylama işlemi başarısız!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Hata oluştu: {str(e)}"))
        
        # Son durum kontrolü
        self.stdout.write("\n=== SON DURUM KONTROLÜ ===")
        
        final_approved = SubscriptionRequest.objects.filter(status='approved')
        for req in final_approved:
            try:
                subscription = UserSubscription.objects.get(
                    user=req.user, 
                    plan=req.plan, 
                    status='active'
                )
                self.stdout.write(f"✓ {req.user.username}: {req.plan.name} - AKTİF ABONELIK VAR")
            except UserSubscription.DoesNotExist:
                self.stdout.write(f"✗ {req.user.username}: {req.plan.name} - AKTİF ABONELIK YOK!")
            except UserSubscription.MultipleObjectsReturned:
                count = UserSubscription.objects.filter(user=req.user, plan=req.plan, status='active').count()
                self.stdout.write(f"! {req.user.username}: {req.plan.name} - {count} AKTİF ABONELIK")
        
        self.stdout.write(self.style.SUCCESS("\n=== YENİDEN İŞLEME TAMAMLANDI ===")) 