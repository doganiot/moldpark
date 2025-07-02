from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import SubscriptionRequest, UserSubscription, PricingPlan, SimpleNotification
from django.utils import timezone


class Command(BaseCommand):
    help = 'Onaylanmış ama abonelik oluşturulmamış talepleri düzeltir'

    def handle(self, *args, **options):
        self.stdout.write("=== ONAYLANMIŞ TALEPLERİ DÜZELTME ===")
        
        # Onaylanmış ama abonelik oluşturulmamış talepleri bul
        approved_requests = SubscriptionRequest.objects.filter(status='approved')
        
        self.stdout.write(f"Onaylanmış talep sayısı: {approved_requests.count()}")
        
        for req in approved_requests:
            self.stdout.write(f"\nKontrol ediliyor: {req.user.username} - {req.plan.name}")
            
            # Bu kullanıcının bu plan için aktif aboneliği var mı?
            try:
                subscription = UserSubscription.objects.get(
                    user=req.user, 
                    plan=req.plan, 
                    status='active'
                )
                self.stdout.write(f"✓ Aktif abonelik mevcut: {subscription.plan.name}")
            except UserSubscription.DoesNotExist:
                self.stdout.write(f"✗ Aktif abonelik yok! Düzeltiliyor...")
                
                # Mevcut aboneliği iptal et
                try:
                    existing_subscription = UserSubscription.objects.get(user=req.user)
                    old_plan = existing_subscription.plan.name
                    existing_subscription.status = 'cancelled'
                    existing_subscription.save()
                    self.stdout.write(f"  - Eski abonelik iptal edildi: {old_plan}")
                except UserSubscription.DoesNotExist:
                    self.stdout.write(f"  - Mevcut abonelik yok")
                except UserSubscription.MultipleObjectsReturned:
                    # Tüm abonelikleri iptal et
                    UserSubscription.objects.filter(user=req.user).update(status='cancelled')
                    self.stdout.write(f"  - Birden fazla abonelik iptal edildi")
                
                # Yeni abonelik oluştur
                try:
                    subscription = UserSubscription.objects.create(
                        user=req.user,
                        plan=req.plan,
                        start_date=timezone.now(),
                        status='active'
                    )
                    self.stdout.write(f"  ✓ Yeni abonelik oluşturuldu: {subscription.plan.name}")
                    
                    # Bildirim gönder
                    SimpleNotification.objects.create(
                        user=req.user,
                        title='Abonelik Aktifleştirildi',
                        message=f'{req.plan.name} planı aboneliğiniz aktifleştirildi.',
                        notification_type='success',
                        related_url='/subscription/'
                    )
                    self.stdout.write(f"  ✓ Bildirim gönderildi")
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ Abonelik oluşturulurken hata: {str(e)}"))
            
            except UserSubscription.MultipleObjectsReturned:
                subs = UserSubscription.objects.filter(user=req.user, plan=req.plan)
                self.stdout.write(f"! Birden fazla abonelik mevcut ({subs.count()} adet)")
                
                # En son oluşturulanı aktif tut, diğerlerini iptal et
                latest_sub = subs.order_by('-created_at').first()
                older_subs = subs.exclude(id=latest_sub.id)
                older_subs.update(status='cancelled')
                
                latest_sub.status = 'active'
                latest_sub.save()
                
                self.stdout.write(f"  ✓ En güncel abonelik aktif tutuldu, {older_subs.count()} eski abonelik iptal edildi")
        
        # Son durum raporu
        self.stdout.write("\n=== SON DURUM ===")
        
        for req in approved_requests:
            try:
                subscription = UserSubscription.objects.get(
                    user=req.user, 
                    plan=req.plan, 
                    status='active'
                )
                self.stdout.write(f"✓ {req.user.username}: {req.plan.name} - AKTİF")
            except UserSubscription.DoesNotExist:
                self.stdout.write(f"✗ {req.user.username}: {req.plan.name} - SORUN VAR!")
            except UserSubscription.MultipleObjectsReturned:
                count = UserSubscription.objects.filter(user=req.user, plan=req.plan, status='active').count()
                self.stdout.write(f"! {req.user.username}: {req.plan.name} - {count} AKTIF ABONELIK")
        
        self.stdout.write(self.style.SUCCESS("\n=== DÜZELTME TAMAMLANDI ===")) 