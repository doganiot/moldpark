from django.core.management.base import BaseCommand
from core.models import UserSubscription


class Command(BaseCommand):
    help = 'Mevcut paket aboneliklerinin package_credits değerlerini düzeltir'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Paket abonelikleri kontrol ediliyor...'))
        
        # Paket planına sahip aktif abonelikleri bul
        package_subscriptions = UserSubscription.objects.filter(
            plan__plan_type='package',
            status='active'
        )
        
        fixed_count = 0
        for subscription in package_subscriptions:
            # package_credits 0 ise veya plan.monthly_model_limit'ten farklıysa düzelt
            expected_credits = subscription.plan.monthly_model_limit
            if subscription.package_credits != expected_credits:
                old_credits = subscription.package_credits
                subscription.package_credits = expected_credits
                subscription.save()
                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[OK] {subscription.user.username} - '
                        f'{subscription.plan.name}: '
                        f'{old_credits} -> {expected_credits} hak'
                    )
                )
        
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'Toplam {fixed_count} abonelik düzeltildi.'))
        self.stdout.write('=' * 60)

