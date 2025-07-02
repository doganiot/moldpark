from django.core.management.base import BaseCommand
from core.models import PricingPlan

class Command(BaseCommand):
    help = 'Deneme paketi oluşturur'

    def handle(self, *args, **options):
        trial_plan, created = PricingPlan.objects.get_or_create(
            plan_type='trial',
            defaults={
                'name': 'Ücretsiz Deneme Paketi',
                'description': 'Platformu test etmek için 3 kalıp gönderme hakkı ile ücretsiz deneme paketi.',
                'price_usd': 0.00,
                'price_try': 0.00,
                'monthly_model_limit': 3,
                'is_monthly': False,
                'features': [
                    '3 kalıp gönderme hakkı',
                    'Temel kalıp takibi',
                    'E-posta bildirimleri',
                    'Temel destek'
                ],
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Deneme paketi başarıyla oluşturuldu: {trial_plan.name}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Deneme paketi zaten mevcut: {trial_plan.name}')
            ) 