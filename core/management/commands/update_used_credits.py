from django.core.management.base import BaseCommand
from core.models import UserSubscription
from mold.models import EarMold


class Command(BaseCommand):
    help = 'Paket aboneliklerinin used_credits değerlerini mevcut kalıp kullanımlarına göre günceller'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Paket kullanımları kontrol ediliyor...'))
        
        # Paket planına sahip aktif abonelikleri bul
        package_subscriptions = UserSubscription.objects.filter(
            plan__plan_type='package',
            status='active'
        )
        
        updated_count = 0
        for subscription in package_subscriptions:
            # Paket satın alma tarihinden sonra oluşturulan fiziksel kalıpları say
            # Paket satın alma tarihi = subscription.start_date veya subscription.created_at
            package_start_date = subscription.start_date
            
            # Bu tarihten sonra oluşturulan fiziksel kalıpları say
            used_molds = EarMold.objects.filter(
                center__user=subscription.user,
                is_physical_shipment=True,
                created_at__gte=package_start_date
            ).count()
            
            # used_credits'i güncelle (paket haklarını aşmamalı)
            if used_molds != subscription.used_credits:
                old_used = subscription.used_credits
                # Paket haklarını aşmamalı
                subscription.used_credits = min(used_molds, subscription.package_credits)
                subscription.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[OK] {subscription.user.username} - '
                        f'{subscription.plan.name}: '
                        f'used_credits {old_used} -> {subscription.used_credits} '
                        f'(Toplam {used_molds} kalıp kullanılmış, paket hakları: {subscription.package_credits})'
                    )
                )
            else:
                self.stdout.write(
                    f'[SKIP] {subscription.user.username} - '
                    f'{subscription.plan.name}: '
                    f'used_credits zaten doğru ({subscription.used_credits})'
                )
        
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'Toplam {updated_count} abonelik güncellendi.'))
        self.stdout.write('=' * 60)

