from django.core.management.base import BaseCommand
from core.models import PricingPlan

class Command(BaseCommand):
    help = 'MoldPark fiyatlandırma planlarını oluşturur'

    def handle(self, *args, **options):
        # Mevcut planları temizle
        PricingPlan.objects.all().delete()
        
        # 1. Kullandıkça Öde - Tek Model
        pay_per_use = PricingPlan.objects.create(
            name='Kullandıkça Öde',
            plan_type='pay_per_use',
            description='Tek kalıp modelleme için tekil ödeme. İhtiyacınız olan her model için ayrı ödeme yapın.',
            price_usd=0.99,
            price_try=32.00,  # 1 USD = ~32 TL
            monthly_model_limit=None,  # Sınırsız ama tek tek öde
            is_monthly=False,
            features=[
                'Model başına ödeme',
                'Anında işleme',
                'Premium kalite',
                'E-posta desteği',
                'Hızlı teslimat'
            ]
        )
        
        # 2. İşitme Merkezi - Temel Plan
        center_basic = PricingPlan.objects.create(
            name='İşitme Merkezi - Temel',
            plan_type='center_basic',
            description='Küçük işitme merkezleri için uygun fiyatlı aylık abonelik. Aylık 30 kalıp modelleme hakkı.',
            price_usd=15.00,
            price_try=480.00,  # 15 USD = ~480 TL
            monthly_model_limit=30,
            is_monthly=True,
            features=[
                'Aylık 30 kalıp modelleme',
                'Standart kalite',
                'E-posta desteği',
                'Temel raporlama',
                '7/24 sistem erişimi'
            ]
        )
        
        # 3. İşitme Merkezi - Profesyonel Plan
        center_professional = PricingPlan.objects.create(
            name='İşitme Merkezi - Profesyonel',
            plan_type='center_professional',
            description='Orta ve büyük işitme merkezleri için gelişmiş özellikler. Aylık 70 kalıp modelleme hakkı.',
            price_usd=30.00,
            price_try=960.00,  # 30 USD = ~960 TL
            monthly_model_limit=70,
            is_monthly=True,
            features=[
                'Aylık 70 kalıp modelleme',
                'Premium kalite',
                'Öncelikli destek',
                'Gelişmiş raporlama',
                'Revizyon garantisi',
                'API erişimi',
                'Özel müşteri temsilcisi'
            ]
        )
        
        # 4. Üretici Merkez Plan
        producer_plan = PricingPlan.objects.create(
            name='Üretici Merkez',
            plan_type='producer',
            description='Üretici merkezler için yüksek kapasiteli plan. Aylık 120 kalıp modelleme hakkı ve gelişmiş özellikler.',
            price_usd=45.00,
            price_try=1440.00,  # 45 USD = ~1440 TL
            monthly_model_limit=120,
            is_monthly=True,
            features=[
                'Aylık 120 kalıp modelleme',
                'Premium kalite',
                'Öncelikli destek',
                'Gelişmiş raporlama',
                'Sınırsız revizyon',
                'API erişimi',
                'Özel müşteri temsilcisi',
                'Toplu işlem desteği',
                'Özelleştirilebilir iş akışı',
                'Gelişmiş analitik'
            ]
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Başarıyla 4 fiyatlandırma planı oluşturuldu:\n'
                f'1. {pay_per_use.name} - ${pay_per_use.price_usd} (₺{pay_per_use.price_try})\n'
                f'2. {center_basic.name} - ${center_basic.price_usd}/ay (₺{center_basic.price_try}/ay)\n'
                f'3. {center_professional.name} - ${center_professional.price_usd}/ay (₺{center_professional.price_try}/ay)\n'
                f'4. {producer_plan.name} - ${producer_plan.price_usd}/ay (₺{producer_plan.price_try}/ay)'
            )
        ) 