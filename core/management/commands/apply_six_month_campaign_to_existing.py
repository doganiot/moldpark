from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import PricingPlan, UserSubscription, SimpleNotification
from center.models import Center
from producer.models import Producer
from datetime import timedelta
from django.utils import timezone

class Command(BaseCommand):
    help = 'Mevcut kullanıcılara 6 aylık ücretsiz kampanya uygular'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--apply-all',
            action='store_true',
            help='Tüm kullanıcılara (aktif aboneliği olanlara da) kampanyayı uygula'
        )
        parser.add_argument(
            '--only-inactive',
            action='store_true',
            help='Sadece aktif aboneliği olmayanlara uygula'
        )
    
    def handle(self, *args, **options):
        # İşitme merkezi planını al
        center_plan = PricingPlan.objects.filter(
            plan_type='trial',
            trial_days__gte=180,
            is_active=True
        ).first()
        
        # Üretici merkez planını al
        producer_plan = PricingPlan.objects.filter(
            plan_type='producer_trial',
            trial_days__gte=180,
            is_active=True
        ).first()
        
        if not center_plan:
            self.stdout.write(self.style.ERROR('❌ 6 Aylık İşitme Merkezi kampanya planı bulunamadı!'))
            return
        
        if not producer_plan:
            self.stdout.write(self.style.ERROR('❌ 6 Aylık Üretici Merkez kampanya planı bulunamadı!'))
            return
        
        # İşleme sayaçları
        center_updated = 0
        center_created = 0
        producer_updated = 0
        producer_created = 0
        
        # İşitme Merkezlerini işle
        self.stdout.write(self.style.WARNING('\n📍 İşitme Merkezleri işleniyor...'))
        centers = Center.objects.all()
        
        for center in centers:
            user = center.user
            
            # Mevcut abonelik kontrolü
            try:
                subscription = UserSubscription.objects.get(user=user)
                
                if subscription.status == 'active' and not options['apply_all']:
                    self.stdout.write(f'   - {user.username}: Zaten aktif aboneliği var, atlandı')
                    continue
                
                # Mevcut aboneliği güncelle
                subscription.plan = center_plan
                subscription.start_date = timezone.now()
                subscription.end_date = timezone.now() + timedelta(days=180)
                subscription.status = 'active'
                subscription.models_used_this_month = 0
                subscription.save()
                
                center_updated += 1
                self.stdout.write(self.style.SUCCESS(f'   ✅ {user.username}: Abonelik 6 aylık kampanyaya güncellendi'))
                
            except UserSubscription.DoesNotExist:
                # Yeni abonelik oluştur
                UserSubscription.objects.create(
                    user=user,
                    plan=center_plan,
                    status='active',
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=180),
                    models_used_this_month=0,
                    amount_paid=0,
                    currency='USD'
                )
                
                center_created += 1
                self.stdout.write(self.style.SUCCESS(f'   ✅ {user.username}: 6 aylık kampanya aboneliği oluşturuldu'))
            
            # Bildirim gönder
            SimpleNotification.objects.create(
                user=user,
                title='🎉 6 Aylık Ücretsiz Kampanya!',
                message='Müjde! Platformumuzu yaygınlaştırmak için başlattığımız kampanyadan sizin de yararlanmanızı istiyoruz. 6 ay boyunca tüm özellikleri ücretsiz kullanabilirsiniz!',
                notification_type='success',
                related_url='/subscription/'
            )
        
        # Üretici Merkezleri işle
        self.stdout.write(self.style.WARNING('\n🏭 Üretici Merkezler işleniyor...'))
        producers = Producer.objects.filter(is_verified=True)
        
        for producer in producers:
            user = producer.user
            
            # Mevcut abonelik kontrolü
            try:
                subscription = UserSubscription.objects.get(user=user)
                
                if subscription.status == 'active' and not options['apply_all']:
                    self.stdout.write(f'   - {user.username}: Zaten aktif aboneliği var, atlandı')
                    continue
                
                # Mevcut aboneliği güncelle
                subscription.plan = producer_plan
                subscription.start_date = timezone.now()
                subscription.end_date = timezone.now() + timedelta(days=180)
                subscription.status = 'active'
                subscription.models_used_this_month = 0
                subscription.save()
                
                producer_updated += 1
                self.stdout.write(self.style.SUCCESS(f'   ✅ {producer.company_name}: Abonelik 6 aylık kampanyaya güncellendi'))
                
            except UserSubscription.DoesNotExist:
                # Yeni abonelik oluştur
                UserSubscription.objects.create(
                    user=user,
                    plan=producer_plan,
                    status='active',
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=180),
                    models_used_this_month=0,
                    amount_paid=0,
                    currency='USD'
                )
                
                producer_created += 1
                self.stdout.write(self.style.SUCCESS(f'   ✅ {producer.company_name}: 6 aylık kampanya aboneliği oluşturuldu'))
            
            # Bildirim gönder
            SimpleNotification.objects.create(
                user=user,
                title='🏭 6 Aylık Ücretsiz Üretici Kampanyası!',
                message='Platformumuzun büyümesi için başlattığımız özel kampanyadan yararlanabilirsiniz! 6 ay boyunca tüm özellikleri ücretsiz kullanın ve daha fazla siparişe ulaşın.',
                notification_type='success',
                related_url='/subscription/'
            )
        
        # Özet
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('📊 KAMPANYA UYGULAMA ÖZETİ:'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'\n📍 İşitme Merkezleri:')
        self.stdout.write(f'   - Güncellenen: {center_updated}')
        self.stdout.write(f'   - Yeni oluşturulan: {center_created}')
        self.stdout.write(f'   - TOPLAM: {center_updated + center_created}')
        
        self.stdout.write(f'\n🏭 Üretici Merkezler:')
        self.stdout.write(f'   - Güncellenen: {producer_updated}')
        self.stdout.write(f'   - Yeni oluşturulan: {producer_created}')
        self.stdout.write(f'   - TOPLAM: {producer_updated + producer_created}')
        
        total = center_updated + center_created + producer_updated + producer_created
        self.stdout.write(self.style.SUCCESS(f'\n✅ Toplam {total} kullanıcıya 6 aylık ücretsiz kampanya uygulandı!'))
