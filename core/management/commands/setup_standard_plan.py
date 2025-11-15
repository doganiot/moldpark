from django.core.management.base import BaseCommand
from core.models import PricingPlan
from decimal import Decimal


class Command(BaseCommand):
    help = 'Standart 100 TL abonelik paketini oluşturur'

    def handle(self, *args, **options):
        self.stdout.write('Standart abonelik paketi oluşturuluyor...')
        
        # Önce tüm planları inaktif yap
        PricingPlan.objects.all().update(is_active=False)
        self.stdout.write(self.style.WARNING('Tüm eski planlar inaktif yapıldı'))
        
        # Standart planı oluştur veya güncelle
        plan, created = PricingPlan.objects.update_or_create(
            plan_type='standard',
            defaults={
                'name': 'Standart Abonelik',
                'description': 'MoldPark sistemi sınırsız kullanım - Aylık 100 TL',
                'monthly_fee_try': Decimal('100.00'),
                'per_mold_price_try': Decimal('0.00'),  # Sınırsız kullanım
                'modeling_service_fee_try': Decimal('0.00'),  # Sınırsız kullanım
                'monthly_model_limit': 999999,  # Sınırsız
                'is_monthly': True,
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Standart plan oluşturuldu: {plan.name}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Standart plan güncellendi: {plan.name}'))
        
        self.stdout.write(self.style.SUCCESS(f'💰 Aylık Ücret: {plan.monthly_fee_try} TL'))
        self.stdout.write(self.style.SUCCESS(f'🚀 Sınırsız Kullanım: Evet'))
        self.stdout.write(self.style.SUCCESS(f'📊 Plan ID: {plan.id}'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Standart abonelik paketi hazır!'))

