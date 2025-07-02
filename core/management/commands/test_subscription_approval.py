from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import SubscriptionRequest, UserSubscription, PricingPlan
from django.utils import timezone


class Command(BaseCommand):
    help = 'Abonelik onaylama sürecini test eder'

    def handle(self, *args, **options):
        self.stdout.write("=== ABONELIK ONAYLAMA TEST SÜRECI ===")
        
        # Mevcut durum kontrolü
        self.stdout.write("\n1. MEVCUT DURUMU KONTROL EDİYORUZ...")
        
        # Tüm talepleri listele
        requests = SubscriptionRequest.objects.all()
        self.stdout.write(f"Toplam talep sayısı: {requests.count()}")
        
        for req in requests:
            self.stdout.write(f"- {req.user.username} | {req.plan.name} | {req.status}")
        
        # Tüm abonelikleri listele
        subscriptions = UserSubscription.objects.all()
        self.stdout.write(f"\nToplam abonelik sayısı: {subscriptions.count()}")
        
        for sub in subscriptions:
            self.stdout.write(f"- {sub.user.username} | {sub.plan.name} | {sub.status}")
        
        # Beklemede olan talepleri bul
        pending_requests = SubscriptionRequest.objects.filter(status='pending')
        self.stdout.write(f"\nBeklemede olan talep sayısı: {pending_requests.count()}")
        
        if pending_requests.exists():
            self.stdout.write("\n2. TEST ONAYLAMASI YAPIYORUZ...")
            
            # İlk bekleyen talebi onaylamaya çalış
            test_request = pending_requests.first()
            self.stdout.write(f"Test talebi: {test_request.user.username} - {test_request.plan.name}")
            
            # Admin kullanıcısı bul
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                self.stdout.write(self.style.ERROR("Admin kullanıcısı bulunamadı!"))
                return
            
            # Onaylama işlemini gerçekleştir
            try:
                result = test_request.approve(admin_user, "Test onaylaması")
                if result:
                    self.stdout.write(self.style.SUCCESS(f"✓ Talep başarıyla onaylandı!"))
                    
                    # Oluşan aboneliği kontrol et
                    try:
                        new_subscription = UserSubscription.objects.get(user=test_request.user)
                        self.stdout.write(f"✓ Yeni abonelik oluşturuldu: {new_subscription.plan.name} - {new_subscription.status}")
                    except UserSubscription.DoesNotExist:
                        self.stdout.write(self.style.ERROR("✗ Abonelik oluşturulmadı!"))
                    except UserSubscription.MultipleObjectsReturned:
                        subs = UserSubscription.objects.filter(user=test_request.user)
                        self.stdout.write(f"! Birden fazla abonelik mevcut ({subs.count()} adet):")
                        for sub in subs:
                            self.stdout.write(f"  - {sub.plan.name} ({sub.status}) - {sub.created_at}")
                        
                else:
                    self.stdout.write(self.style.ERROR("✗ Onaylama işlemi başarısız!"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Hata oluştu: {str(e)}"))
        
        else:
            self.stdout.write("\n2. Beklemede olan talep yok.")
        
        # Son durum kontrolü
        self.stdout.write("\n3. SON DURUM KONTROLÜ...")
        
        final_requests = SubscriptionRequest.objects.all()
        for req in final_requests:
            self.stdout.write(f"Talep: {req.user.username} | {req.plan.name} | {req.status}")
        
        final_subscriptions = UserSubscription.objects.all()
        for sub in final_subscriptions:
            self.stdout.write(f"Abonelik: {sub.user.username} | {sub.plan.name} | {sub.status}")
            
        self.stdout.write(self.style.SUCCESS("\n=== TEST TAMAMLANDI ===")) 