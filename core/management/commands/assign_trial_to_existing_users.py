from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import PricingPlan, UserSubscription, SimpleNotification
from django.utils import timezone

class Command(BaseCommand):
    help = 'Mevcut kullanıcılara deneme paketi atar'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Mevcut abonelikleri varsa da deneme paketi atar',
        )

    def handle(self, *args, **options):
        try:
            # Deneme paketini al
            trial_plan = PricingPlan.objects.get(plan_type='trial', is_active=True)
        except PricingPlan.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Deneme paketi bulunamadı. Önce create_trial_plan komutunu çalıştırın.')
            )
            return

        # Aboneliği olmayan kullanıcıları bul
        users_without_subscription = User.objects.exclude(subscription__status='active')
        
        if options['force']:
            # Tüm kullanıcıları al
            users_to_process = User.objects.filter(is_superuser=False)
            self.stdout.write(
                self.style.WARNING('--force seçeneği kullanıldı. Tüm kullanıcıların abonelikleri güncellenecek.')
            )
        else:
            users_to_process = users_without_subscription

        created_count = 0
        updated_count = 0
        
        for user in users_to_process:
            try:
                # Mevcut abonelik kontrolü
                existing_subscription = UserSubscription.objects.filter(user=user, status='active').first()
                
                if existing_subscription and not options['force']:
                    self.stdout.write(f'Kullanıcı {user.username} zaten aktif aboneliğe sahip, atlandı.')
                    continue
                
                if existing_subscription and options['force']:
                    # Mevcut aboneliği güncelle
                    existing_subscription.plan = trial_plan
                    existing_subscription.models_used_this_month = 0
                    existing_subscription.save()
                    updated_count += 1
                    action = 'güncellendi'
                else:
                    # Yeni abonelik oluştur
                    subscription = UserSubscription.objects.create(
                        user=user,
                        plan=trial_plan,
                        status='active',
                        models_used_this_month=0,
                        amount_paid=0,
                        currency='USD'
                    )
                    created_count += 1
                    action = 'oluşturuldu'
                
                # Bildirim gönder
                SimpleNotification.objects.create(
                    user=user,
                    title='Deneme Paketi Hediyeniz!',
                    message=f'Size özel {trial_plan.monthly_model_limit} kalıp gönderme hakkı hediye ettik! Platformu keşfetmeye başlayın.',
                    notification_type='success',
                    related_url='/subscription/'
                )
                
                self.stdout.write(
                    f'✓ {user.username} kullanıcısı için deneme paketi {action}'
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ {user.username} için hata: {str(e)}')
                )
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(
                f'İşlem tamamlandı!\n'
                f'Yeni abonelik oluşturulan: {created_count}\n'
                f'Güncellenen abonelik: {updated_count}\n'
                f'Toplam işlem: {created_count + updated_count}'
            )
        ) 