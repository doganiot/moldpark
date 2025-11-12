"""
Yeni fiyatlandırma sistemini kurmak için management komutu
- Eski planları devre dışı bırakır
- Yeni standard planı oluşturur
- Mevcut kullanıcıların aboneliklerini günceller
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import PricingPlan, UserSubscription


class Command(BaseCommand):
    help = 'Yeni fiyatlandırma sistemini kurar (Ücretsiz abonelik + kullandıkça öde)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Yeni Fiyatlandırma Sistemi Kurulumu Başlatılıyor ===\n'))

        # 1. Eski planları devre dışı bırak
        self.stdout.write('1. Eski planlar devre dışı bırakılıyor...')
        old_plans = PricingPlan.objects.filter(is_active=True).exclude(plan_type='standard')
        old_count = old_plans.count()
        old_plans.update(is_active=False)
        self.stdout.write(self.style.SUCCESS(f'   ✓ {old_count} eski plan devre dışı bırakıldı\n'))

        # 2. Yeni standard planı oluştur veya güncelle
        self.stdout.write('2. Yeni standart plan oluşturuluyor...')
        default_features = [
            'Abonelik ücreti yok (Ücretsiz)',
            'Kalıp başına 450 TL (kargo hariç)',
            '3D modelleme hizmeti 50 TL',
            'Sınırsız kalıp oluşturma',
            'Kullandıkça öde sistemi',
            'Tüm üretici ağına erişim',
            'Kalite kontrol garantisi',
            '7/24 müşteri desteği',
            'Hızlı teslimat'
        ]
        plan, created = PricingPlan.objects.get_or_create(
            plan_type='standard',
            defaults={
                'name': 'MoldPark Standart Paket',
                'description': 'Abonelik ücreti yok. Fiziksel kalıp 450 TL, 3D modelleme 50 TL.',
                'monthly_fee_try': 0.00,
                'per_mold_price_try': 450.00,
                'modeling_service_fee_try': 50.00,
                'is_active': True,
                'price_usd': 0,
                'price_try': 0,
                'monthly_model_limit': None,  # Sınırsız
                'is_monthly': True,
                'features': default_features,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('   ✓ Yeni standart plan oluşturuldu'))
        else:
            # Var olan planı güncelle
            plan.name = 'MoldPark Standart Paket'
            plan.description = 'Abonelik ücreti yok. Fiziksel kalıp 450 TL, 3D modelleme 50 TL.'
            plan.monthly_fee_try = 0.00
            plan.per_mold_price_try = 450.00
            plan.modeling_service_fee_try = 50.00
            plan.is_active = True
            plan.price_try = 0
            plan.features = default_features
            plan.save()
            self.stdout.write(self.style.SUCCESS('   ✓ Mevcut standart plan güncellendi'))
        
        self.stdout.write(self.style.SUCCESS(f'   Plan ID: {plan.id}\n'))

        # 3. Mevcut kullanıcıların aboneliklerini yeni plana geçir
        self.stdout.write('3. Mevcut kullanıcı abonelikleri güncelleniyor...')
        subscriptions = UserSubscription.objects.filter(status='active')
        updated_count = 0
        
        for subscription in subscriptions:
            if subscription.plan.plan_type != 'standard':
                subscription.plan = plan
                subscription.currency = 'TRY'
                subscription.monthly_fee_paid = False
                subscription.total_mold_cost_this_month = 0
                subscription.models_used_total = subscription.models_used_this_month
                subscription.save()
                updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {updated_count} abonelik yeni plana geçirildi\n'))

        # 4. Özet bilgiler
        self.stdout.write(self.style.SUCCESS('=== Kurulum Tamamlandı ==='))
        self.stdout.write(self.style.SUCCESS(f'Plan Adı: {plan.name}'))
        self.stdout.write(self.style.SUCCESS(f'Aylık Sistem Ücreti: ₺{plan.monthly_fee_try} (ÜCRETSİZ)'))
        self.stdout.write(self.style.SUCCESS(f'Kalıp Başına Ücret: ₺{plan.per_mold_price_try}'))
        self.stdout.write(self.style.SUCCESS(f'Digital Tarama Hizmeti Ücreti: ₺{plan.modeling_service_fee_try}'))
        self.stdout.write(self.style.SUCCESS(f'Aktif Abonelik Sayısı: {UserSubscription.objects.filter(status="active").count()}'))
        self.stdout.write(self.style.SUCCESS('\n✓ Yeni fiyatlandırma sistemi başarıyla kuruldu!'))

