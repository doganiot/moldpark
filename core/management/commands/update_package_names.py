"""
Paket adlarını güncellemek için management komutu
- İşitme Merkezi - Temel → Silver
- İşitme Merkezi - Profesyonel → Gold
- Üretici Merkez → Platinum
"""

from django.core.management.base import BaseCommand
from core.models import PricingPlan


class Command(BaseCommand):
    help = 'Paket adlarını Silver, Gold, Platinum olarak güncelleştir'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Paket Adlari Guncelleniyor ===\n'))

        # 1. İşitme Merkezi - Temel → Silver
        silver_plans = PricingPlan.objects.filter(name__icontains='İşitme Merkezi - Temel')
        silver_count = 0
        for plan in silver_plans:
            old_name = plan.name
            plan.name = 'Silver'
            plan.save()
            silver_count += 1
            self.stdout.write(f'[OK] {old_name} -> Silver')
        
        if silver_count == 0:
            # Direkt Silver yoksa oluştur veya var olanı güncelle
            silver, created = PricingPlan.objects.get_or_create(
                plan_type='center_basic',
                defaults={
                    'name': 'Silver',
                    'description': 'Küçük işitme merkezleri için uygun fiyatlı aylık abonelik. Aylık 30 kalıp modelleme hakkı.',
                    'price_usd': 15.00,
                    'price_try': 480.00,
                    'monthly_model_limit': 30,
                    'is_monthly': True,
                    'per_mold_price_try': 450.00,
                    'modeling_service_fee_try': 50.00,
                    'monthly_fee_try': 0.00,
                }
            )
            if not created:
                silver.name = 'Silver'
                silver.save()
            silver_count = 1
            self.stdout.write(f'[OK] Silver paketi olusturuldu/guncellendi')

        # 2. İşitme Merkezi - Profesyonel → Gold
        gold_plans = PricingPlan.objects.filter(name__icontains='İşitme Merkezi - Profesyonel')
        gold_count = 0
        for plan in gold_plans:
            old_name = plan.name
            plan.name = 'Gold'
            plan.save()
            gold_count += 1
            self.stdout.write(f'[OK] {old_name} -> Gold')
        
        if gold_count == 0:
            gold, created = PricingPlan.objects.get_or_create(
                plan_type='center_professional',
                defaults={
                    'name': 'Gold',
                    'description': 'Orta ve büyük işitme merkezleri için gelişmiş özellikler. Aylık 70 kalıp modelleme hakkı.',
                    'price_usd': 30.00,
                    'price_try': 960.00,
                    'monthly_model_limit': 70,
                    'is_monthly': True,
                    'per_mold_price_try': 450.00,
                    'modeling_service_fee_try': 50.00,
                    'monthly_fee_try': 0.00,
                }
            )
            if not created:
                gold.name = 'Gold'
                gold.save()
            gold_count = 1
            self.stdout.write(f'[OK] Gold paketi olusturuldu/guncellendi')

        # 3. Üretici Merkez → Platinum
        platinum_plans = PricingPlan.objects.filter(name__icontains='Üretici Merkez')
        platinum_count = 0
        for plan in platinum_plans:
            old_name = plan.name
            plan.name = 'Platinum'
            plan.save()
            platinum_count += 1
            self.stdout.write(f'[OK] {old_name} -> Platinum')
        
        if platinum_count == 0:
            platinum, created = PricingPlan.objects.get_or_create(
                plan_type='producer',
                defaults={
                    'name': 'Platinum',
                    'description': 'Üretici merkezler için yüksek kapasiteli plan. Aylık 120 kalıp modelleme hakkı ve gelişmiş özellikler.',
                    'price_usd': 45.00,
                    'price_try': 1440.00,
                    'monthly_model_limit': 120,
                    'is_monthly': True,
                    'per_mold_price_try': 450.00,
                    'modeling_service_fee_try': 50.00,
                    'monthly_fee_try': 0.00,
                }
            )
            if not created:
                platinum.name = 'Platinum'
                platinum.save()
            platinum_count = 1
            self.stdout.write(f'[OK] Platinum paketi olusturuldu/guncellendi')

        self.stdout.write(self.style.SUCCESS(f'\n[OK] Toplam {silver_count + gold_count + platinum_count} paket guncellendi!'))
        self.stdout.write(self.style.SUCCESS('=== Islem Tamamlandi ==='))

