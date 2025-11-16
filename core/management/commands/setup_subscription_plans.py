from django.core.management.base import BaseCommand
from core.models import PricingPlan
from decimal import Decimal


class Command(BaseCommand):
    help = 'Standart ve Gold abonelik paketlerini oluştur'

    def handle(self, *args, **options):
        # Standart Paket - Ücretsiz, Kullandıkça Öde
        standard_plan, created = PricingPlan.objects.get_or_create(
            name='Standart Abonelik',
            defaults={
                'plan_type': 'standard',
                'description': 'Ücretsiz abonelik - Fiziksel kalıp yapım ₺450/adet, 3D modelleme ₺19/adet',
                'monthly_fee_try': Decimal('0.00'),  # Aylık ücret yok
                'per_mold_price_try': Decimal('450.00'),  # Fiziksel kalıp ücreti
                'modeling_service_fee_try': Decimal('19.00'),  # 3D modelleme ücreti
                'price_usd': Decimal('0.00'),
                'price_try': Decimal('0.00'),
                'monthly_model_limit': None,  # Sınırsız
                'is_monthly': True,
                'trial_days': 0,
                'is_active': True,
                'badge_text': None,
                'is_featured': False,
                'order': 1,
                'features': [
                    'Ücretsiz',
                    'Kullandıkça Öde Sistemi',
                    'Sınırsız Kalıp Yükleme',
                    '₺450/adet Fiziksel Kalıp',
                    '₺19/adet 3D Modelleme',
                ]
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'[OK] Standart Abonelik paketi olusturuldu')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'[EXISTS] Standart Abonelik paketi zaten mevcut')
            )

        # Gold Paket - Aylık 99 TL
        gold_plan, created = PricingPlan.objects.get_or_create(
            name='Gold Abonelik',
            defaults={
                'plan_type': 'package',
                'description': 'Aylik 99 TL - Fiziksel kalip yapim 399 TL/adet, 3D modelleme 15 TL/adet',
                'monthly_fee_try': Decimal('99.00'),  # Aylık ücret
                'per_mold_price_try': Decimal('399.00'),  # Fiziksel kalıp ücreti (indirimli)
                'modeling_service_fee_try': Decimal('15.00'),  # 3D modelleme ücreti
                'price_usd': Decimal('3.09'),  # 99 TL ≈ 3.09 USD (1 USD = 32 TL)
                'price_try': Decimal('99.00'),
                'monthly_model_limit': None,  # Sınırsız
                'is_monthly': True,
                'trial_days': 0,
                'is_active': True,
                'badge_text': 'POPULER',
                'is_featured': True,
                'order': 2,
                'features': [
                    'Aylik 99 TL',
                    'Sinirsiz Kalip Yukleme',
                    'Indirimli Fiyatlar',
                    '399 TL/adet Fiziksel Kalip',
                    '15 TL/adet 3D Modelleme',
                    'Oncelikli Destek',
                ]
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'[OK] Gold Abonelik paketi olusturuldu')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'[EXISTS] Gold Abonelik paketi zaten mevcut')
            )

        self.stdout.write(
            self.style.SUCCESS(f'\n[SUCCESS] Abonelik paketleri basariyla kuruldu!')
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'\nPaket Ozeti:\n'
                f'  Standart: 0 TL/ay + 450 TL/fiziksel kalip + 19 TL/3D modelleme\n'
                f'  Gold: 99 TL/ay + 399 TL/fiziksel kalip + 15 TL/3D modelleme'
            )
        )

