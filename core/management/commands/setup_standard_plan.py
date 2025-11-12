from django.core.management.base import BaseCommand
from core.models import PricingPlan
from decimal import Decimal


class Command(BaseCommand):
    help = 'Standart (ücretsiz) abonelik paketini oluşturur'

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
                'description': 'MoldPark sistemi sınırsız kullanım - Abonelik ÜCRETSİZ, kullandıkça öde',
                'monthly_fee_try': Decimal('0.00'),
                'per_mold_price_try': Decimal('450.00'),
                'modeling_service_fee_try': Decimal('50.00'),
                'monthly_model_limit': None,  # sınırsız
                'is_monthly': True,
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Standart plan oluşturuldu: {plan.name}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Standart plan güncellendi: {plan.name}'))
        
        self.stdout.write(self.style.SUCCESS(f'💰 Aylık Ücret: {plan.monthly_fee_try} TL (ÜCRETSİZ)'))
        self.stdout.write(self.style.SUCCESS('🚀 Kullandıkça öde sistemi aktif'))
        self.stdout.write(self.style.SUCCESS(f'📊 Plan ID: {plan.id}'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Standart abonelik paketi hazır!'))

