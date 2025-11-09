from django.core.management.base import BaseCommand
from core.models import UserSubscription
from mold.models import EarMold
from django.utils import timezone


class Command(BaseCommand):
    help = 'Paket aboneliklerinin used_credits değerlerini mevcut kalıplara göre yeniden hesaplar'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Paket kullanım hakları yeniden hesaplanıyor...'))
        
        # Paket planına sahip aktif abonelikleri bul
        package_subscriptions = UserSubscription.objects.filter(
            plan__plan_type='package',
            status='active'
        )
        
        updated_count = 0
        for subscription in package_subscriptions:
            # Paket satın alma tarihinden sonra oluşturulan fiziksel kalıpları say
            # Paket satın alma tarihi = subscription.start_date veya subscription.created_at
            package_start_date = subscription.start_date or subscription.created_at
            
            # Bu tarihten sonra oluşturulan fiziksel kalıpları say
            physical_molds_count = EarMold.objects.filter(
                center__user=subscription.user,
                is_physical_shipment=True,
                created_at__gte=package_start_date
            ).count()
            
            # used_credits'i güncelle (paket içindeki kalıp sayısını aşmamalı)
            old_used = subscription.used_credits
            new_used = min(physical_molds_count, subscription.package_credits)
            
            if old_used != new_used:
                subscription.used_credits = new_used
                subscription.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[OK] {subscription.user.username} - '
                        f'{subscription.plan.name}: '
                        f'used_credits {old_used} -> {new_used} '
                        f'(Paket satın alındıktan sonra {physical_molds_count} fiziksel kalıp oluşturulmuş)'
                    )
                )
            else:
                self.stdout.write(
                    f'[SKIP] {subscription.user.username} - '
                    f'{subscription.plan.name}: '
                    f'used_credits zaten doğru ({old_used})'
                )
        
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'Toplam {updated_count} abonelik güncellendi.'))
        self.stdout.write('=' * 60)

