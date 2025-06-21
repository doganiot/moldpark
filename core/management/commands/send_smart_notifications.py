"""
MoldPark Akıllı Bildirim Gönderme Komutu
Bu komut akıllı bildirim sistemini çalıştırır ve kullanıcılara kişiselleştirilmiş bildirimler gönderir.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.smart_notifications import SmartNotificationManager
import logging


class Command(BaseCommand):
    help = 'Akıllı bildirimleri gönderir'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['all', 'center', 'producer', 'admin'],
            default='all',
            help='Bildirim türü (varsayılan: all)',
        )
        parser.add_argument(
            '--center-id',
            type=int,
            help='Belirli bir merkez için bildirim gönder',
        )
        parser.add_argument(
            '--producer-id',
            type=int,
            help='Belirli bir üretici için bildirim gönder',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Bildirim göndermeden sadece analiz yap',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        notification_type = options['type']
        center_id = options.get('center_id')
        producer_id = options.get('producer_id')
        
        logger = logging.getLogger('moldpark.notifications')
        
        self.stdout.write(
            self.style.SUCCESS('🔔 Akıllı Bildirim Sistemi Başlatılıyor...\n')
        )
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('⚠️  DRY RUN MODU - Bildirimler gönderilmeyecek, sadece analiz yapılacak.\n')
            )
        
        start_time = timezone.now()
        manager = SmartNotificationManager()
        
        try:
            if center_id:
                self._process_specific_center(manager, center_id)
            elif producer_id:
                self._process_specific_producer(manager, producer_id)
            else:
                self._process_by_type(manager, notification_type)
            
            # İşlem süresi
            duration = (timezone.now() - start_time).total_seconds()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Akıllı bildirim sistemi tamamlandı! ({duration:.1f} saniye)')
            )
            
            logger.info(f'Akıllı bildirim sistemi tamamlandı - Süre: {duration:.1f}s')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Hata oluştu: {str(e)}')
            )
            logger.error(f'Akıllı bildirim sistemi hatası: {str(e)}')
            raise

    def _process_by_type(self, manager, notification_type):
        """Bildirim türüne göre işlem yap"""
        if notification_type == 'all':
            self.stdout.write('📋 Tüm bildirim türleri işleniyor...')
            if not self.dry_run:
                manager.process_all_notifications()
            else:
                self._dry_run_all_analysis(manager)
                
        elif notification_type == 'center':
            self.stdout.write('🏥 Merkez bildirimleri işleniyor...')
            if not self.dry_run:
                manager.process_center_notifications()
            else:
                self._dry_run_center_analysis(manager)
                
        elif notification_type == 'producer':
            self.stdout.write('🏭 Üretici bildirimleri işleniyor...')
            if not self.dry_run:
                manager.process_producer_notifications()
            else:
                self._dry_run_producer_analysis(manager)
                
        elif notification_type == 'admin':
            self.stdout.write('👨‍💼 Admin bildirimleri işleniyor...')
            if not self.dry_run:
                manager.process_admin_notifications()
            else:
                self._dry_run_admin_analysis(manager)

    def _process_specific_center(self, manager, center_id):
        """Belirli bir merkez için işlem yap"""
        from center.models import Center
        
        try:
            center = Center.objects.get(id=center_id)
            self.stdout.write(f'🏥 {center.name} merkezi için bildirimler işleniyor...')
            
            if not self.dry_run:
                manager._check_inactive_center(center)
                manager._check_mold_limit_warning(center)
                manager._check_completed_orders(center)
                manager._check_revision_status(center)
                manager._suggest_performance_improvements(center)
            else:
                self._analyze_center(center)
                
        except Center.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ ID {center_id} ile merkez bulunamadı.')
            )

    def _process_specific_producer(self, manager, producer_id):
        """Belirli bir üretici için işlem yap"""
        from producer.models import Producer
        
        try:
            producer = Producer.objects.get(id=producer_id)
            self.stdout.write(f'🏭 {producer.company_name} üreticisi için bildirimler işleniyor...')
            
            if not self.dry_run:
                manager._check_pending_orders(producer)
                manager._check_capacity_warning(producer)
                manager._analyze_producer_performance(producer)
                manager._suggest_network_expansion(producer)
            else:
                self._analyze_producer(producer)
                
        except Producer.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ ID {producer_id} ile üretici bulunamadı.')
            )

    def _dry_run_all_analysis(self, manager):
        """Tüm sistem için dry run analizi"""
        self.stdout.write('\n📊 SİSTEM ANALİZİ (DRY RUN):')
        self.stdout.write('=' * 50)
        
        self._dry_run_center_analysis(manager)
        self._dry_run_producer_analysis(manager)
        self._dry_run_admin_analysis(manager)

    def _dry_run_center_analysis(self, manager):
        """Merkez bildirimleri için dry run analizi"""
        from center.models import Center
        from producer.models import ProducerOrder
        from mold.models import RevisionRequest
        
        self.stdout.write('\n🏥 MERKEZ ANALİZİ:')
        self.stdout.write('-' * 30)
        
        centers = Center.objects.filter(is_active=True)
        inactive_centers = 0
        limit_warnings = 0
        completed_orders = 0
        pending_revisions = 0
        
        for center in centers:
            # Pasif merkez kontrolü
            last_activity = center.molds.order_by('-created_at').first()
            if last_activity:
                days_inactive = (timezone.now() - last_activity.created_at).days
                if days_inactive >= 30:
                    inactive_centers += 1
            
            # Kalıp limiti kontrolü
            used_molds = center.molds.count()
            limit_percentage = (used_molds / center.mold_limit) * 100
            if limit_percentage >= 80:
                limit_warnings += 1
            
            # Tamamlanan siparişler (son 24 saat)
            yesterday = timezone.now() - timezone.timedelta(days=1)
            recent_completed = ProducerOrder.objects.filter(
                center=center,
                status='delivered',
                actual_delivery__gte=yesterday
            ).count()
            completed_orders += recent_completed
            
            # Bekleyen revizyonlar
            old_revisions = RevisionRequest.objects.filter(
                modeled_mold__ear_mold__center=center,
                status='pending',
                created_at__lt=timezone.now() - timezone.timedelta(days=3)
            ).count()
            pending_revisions += old_revisions
        
        self.stdout.write(f'  📈 Toplam aktif merkez: {centers.count()}')
        self.stdout.write(f'  😴 Pasif merkez (30+ gün): {inactive_centers}')
        self.stdout.write(f'  ⚠️  Limit uyarısı (%80+): {limit_warnings}')
        self.stdout.write(f'  ✅ Tamamlanan sipariş (24h): {completed_orders}')
        self.stdout.write(f'  🔄 Bekleyen revizyon (3+ gün): {pending_revisions}')

    def _dry_run_producer_analysis(self, manager):
        """Üretici bildirimleri için dry run analizi"""
        from producer.models import Producer, ProducerOrder
        
        self.stdout.write('\n🏭 ÜRETİCİ ANALİZİ:')
        self.stdout.write('-' * 30)
        
        producers = Producer.objects.filter(is_active=True, is_verified=True)
        pending_orders = 0
        capacity_warnings = 0
        performance_issues = 0
        expansion_candidates = 0
        
        for producer in producers:
            # Bekleyen siparişler
            pending = producer.orders.filter(
                status='received',
                created_at__lt=timezone.now() - timezone.timedelta(hours=24)
            ).count()
            pending_orders += pending
            
            # Kapasite uyarısı
            current_month_orders = producer.get_current_month_orders()
            capacity_percentage = (current_month_orders / producer.mold_limit) * 100
            if capacity_percentage >= 90:
                capacity_warnings += 1
            
            # Performans analizi
            last_month = timezone.now() - timezone.timedelta(days=30)
            recent_orders = producer.orders.filter(created_at__gte=last_month)
            if recent_orders.count() >= 10:
                # Zamanında teslimat analizi yapılabilir
                performance_issues += 0  # Placeholder
            
            # Ağ genişletme önerisi
            current_networks = producer.network_centers.filter(status='active').count()
            capacity_usage = current_month_orders / producer.mold_limit
            if capacity_usage > 0.8 and current_networks < 5:
                expansion_candidates += 1
        
        self.stdout.write(f'  📈 Toplam aktif üretici: {producers.count()}')
        self.stdout.write(f'  ⏰ Bekleyen sipariş (24h+): {pending_orders}')
        self.stdout.write(f'  🔥 Kapasite uyarısı (%90+): {capacity_warnings}')
        self.stdout.write(f'  📊 Performans sorunu: {performance_issues}')
        self.stdout.write(f'  🌟 Ağ genişletme adayı: {expansion_candidates}')

    def _dry_run_admin_analysis(self, manager):
        """Admin bildirimleri için dry run analizi"""
        from django.contrib.auth.models import User
        from producer.models import Producer, ProducerOrder
        
        self.stdout.write('\n👨‍💼 ADMİN ANALİZİ:')
        self.stdout.write('-' * 30)
        
        # Güvenlik uyarıları
        risky_producers = Producer.objects.filter(
            user__is_staff=True
        ) | Producer.objects.filter(
            user__is_superuser=True
        )
        
        # Geciken siparişler
        overdue_orders = ProducerOrder.objects.filter(
            estimated_delivery__lt=timezone.now(),
            status__in=['received', 'designing', 'production']
        ).count()
        
        # Admin sayısı
        admin_count = User.objects.filter(is_superuser=True).count()
        
        self.stdout.write(f'  👨‍💼 Toplam admin: {admin_count}')
        self.stdout.write(f'  🚨 Güvenlik riski: {risky_producers.count()} üretici')
        self.stdout.write(f'  ⏰ Geciken sipariş: {overdue_orders}')

    def _analyze_center(self, center):
        """Belirli merkez için analiz"""
        self.stdout.write(f'\n📊 {center.name} MERKEZİ ANALİZİ:')
        self.stdout.write('-' * 40)
        
        # Temel bilgiler
        used_molds = center.molds.count()
        limit_percentage = (used_molds / center.mold_limit) * 100
        
        self.stdout.write(f'  📊 Kullanılan kalıp: {used_molds}/{center.mold_limit} (%{limit_percentage:.1f})')
        
        # Son aktivite
        last_activity = center.molds.order_by('-created_at').first()
        if last_activity:
            days_inactive = (timezone.now() - last_activity.created_at).days
            self.stdout.write(f'  📅 Son aktivite: {days_inactive} gün önce')
        
        # Aktif ağlar
        active_networks = center.producer_networks.filter(status='active').count()
        self.stdout.write(f'  🔗 Aktif ağ: {active_networks}')

    def _analyze_producer(self, producer):
        """Belirli üretici için analiz"""
        self.stdout.write(f'\n📊 {producer.company_name} ÜRETİCİSİ ANALİZİ:')
        self.stdout.write('-' * 40)
        
        # Kapasite bilgileri
        current_month_orders = producer.get_current_month_orders()
        capacity_percentage = (current_month_orders / producer.mold_limit) * 100
        
        self.stdout.write(f'  📊 Aylık kapasite: {current_month_orders}/{producer.mold_limit} (%{capacity_percentage:.1f})')
        
        # Bekleyen siparişler
        pending = producer.orders.filter(status='received').count()
        self.stdout.write(f'  ⏰ Bekleyen sipariş: {pending}')
        
        # Aktif ağlar
        active_networks = producer.network_centers.filter(status='active').count()
        self.stdout.write(f'  🔗 Aktif ağ: {active_networks}')
        
        # Doğrulama durumu
        verification_status = "✅ Doğrulanmış" if producer.is_verified else "❌ Doğrulanmamış"
        self.stdout.write(f'  🛡️  Durum: {verification_status}') 