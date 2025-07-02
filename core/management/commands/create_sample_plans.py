from django.core.management.base import BaseCommand
from core.models import PricingPlan

class Command(BaseCommand):
    help = 'Sample fiyatlandırma planları oluşturur'

    def handle(self, *args, **options):
        # Mevcut planları kontrol et
        existing_plans = PricingPlan.objects.exclude(plan_type='trial')
        if existing_plans.exists():
            self.stdout.write(
                self.style.WARNING(f'{existing_plans.count()} adet plan zaten mevcut.')
            )
        
        # TEMEL PLAN
        basic_plan, created = PricingPlan.objects.get_or_create(
            plan_type='basic',
            defaults={
                'name': 'Temel Plan',
                'description': 'Küçük işitme merkezleri için ideal başlangıç paketi',
                'price_usd': 29.99,
                'price_try': 899.99,  # ~30 dolar
                'monthly_model_limit': 50,
                'is_monthly': True,
                'is_active': True,
                'features': [
                    '50 kalıp/ay',
                    'Temel üretici ağı erişimi',
                    'E-posta desteği',
                    'Temel raporlama'
                ]
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ {basic_plan.name} oluşturuldu')
            )
        
        # STANDART PLAN
        standard_plan, created = PricingPlan.objects.get_or_create(
            plan_type='standard',
            defaults={
                'name': 'Standart Plan',
                'description': 'Orta ölçekli işitme merkezleri için kapsamlı çözüm',
                'price_usd': 59.99,
                'price_try': 1799.99,  # ~60 dolar
                'monthly_model_limit': 150,
                'is_monthly': True,
                'is_active': True,
                'features': [
                    '150 kalıp/ay',
                    'Tüm üretici ağı erişimi',
                    'Öncelikli destek',
                    'Gelişmiş raporlama',
                    'Kalıp takip sistemi',
                    'SMS bildirimler'
                ]
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ {standard_plan.name} oluşturuldu')
            )
        
        # PREMİUM PLAN
        premium_plan, created = PricingPlan.objects.get_or_create(
            plan_type='premium',
            defaults={
                'name': 'Premium Plan',
                'description': 'Büyük işitme merkezleri için sınırsız imkanlar',
                'price_usd': 99.99,
                'price_try': 2999.99,  # ~100 dolar
                'monthly_model_limit': 500,
                'is_monthly': True,
                'is_active': True,
                'features': [
                    '500 kalıp/ay',
                    'Tüm üretici ağı + Premium ağ',
                    '7/24 destek',
                    'Özel hesap yöneticisi',
                    'Gelişmiş analitik',
                    'API erişimi',
                    'Özel entegrasyonlar',
                    'White-label çözümler'
                ]
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ {premium_plan.name} oluşturuldu')
            )
        
        # ENTERPRİSE PLAN
        enterprise_plan, created = PricingPlan.objects.get_or_create(
            plan_type='enterprise',
            defaults={
                'name': 'Kurumsal Plan',
                'description': 'Zincir işitme merkezleri ve büyük organizasyonlar için',
                'price_usd': 199.99,
                'price_try': 5999.99,  # ~200 dolar
                'monthly_model_limit': 0,  # Sınırsız
                'is_monthly': True,
                'is_active': True,
                'features': [
                    'Sınırsız kalıp',
                    'Özel üretici ağı',
                    'Dedicated hesap yöneticisi',
                    'Özel SLA',
                    'Kurumsal analitik',
                    'Multi-location yönetim',
                    'Özel geliştirmeler',
                    'On-premise deployment seçeneği'
                ]
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ {enterprise_plan.name} oluşturuldu')
            )
        
        # PLANLAR ÖZETI
        all_plans = PricingPlan.objects.filter(is_active=True).order_by('price_usd')
        self.stdout.write(
            self.style.SUCCESS(f'\n📊 Toplam aktif plan sayısı: {all_plans.count()}')
        )
        
        for plan in all_plans:
            self.stdout.write(f'   • {plan.name} ({plan.plan_type}) - ${plan.price_usd}/ay')
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 Sample planlar başarıyla oluşturuldu!')
        ) 