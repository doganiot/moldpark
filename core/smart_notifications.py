"""
MoldPark Akıllı Bildirim Sistemi
Kullanıcı davranışlarını analiz ederek kişiselleştirilmiş bildirimler gönderir.
"""

from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Q, F
from datetime import timedelta
from notifications.signals import notify
from center.models import Center
from producer.models import Producer, ProducerOrder, ProducerNetwork
from mold.models import EarMold, RevisionRequest
import logging


class SmartNotificationManager:
    """Akıllı bildirim yöneticisi"""
    
    def __init__(self):
        self.logger = logging.getLogger('moldpark.notifications')
    
    def process_all_notifications(self):
        """Tüm akıllı bildirimleri işle"""
        self.logger.info('Akıllı bildirim sistemi başlatılıyor...')
        
        # Farklı bildirim türlerini işle
        self.process_center_notifications()
        self.process_producer_notifications()
        self.process_admin_notifications()
        
        self.logger.info('Akıllı bildirim sistemi tamamlandı.')
    
    def process_center_notifications(self):
        """İşitme merkezleri için akıllı bildirimler"""
        centers = Center.objects.filter(is_active=True)
        
        for center in centers:
            # 1. Pasif merkez uyarısı
            self._check_inactive_center(center)
            
            # 2. Kalıp limiti uyarısı
            self._check_mold_limit_warning(center)
            
            # 3. Tamamlanan siparişler
            self._check_completed_orders(center)
            
            # 4. Revizyon durumu
            self._check_revision_status(center)
            
            # 5. Performans önerileri
            self._suggest_performance_improvements(center)
    
    def process_producer_notifications(self):
        """Üreticiler için akıllı bildirimler"""
        producers = Producer.objects.filter(is_active=True, is_verified=True)
        
        for producer in producers:
            # 1. Bekleyen siparişler
            self._check_pending_orders(producer)
            
            # 2. Kapasite uyarısı
            self._check_capacity_warning(producer)
            
            # 3. Performans analizi
            self._analyze_producer_performance(producer)
            
            # 4. Ağ önerileri
            self._suggest_network_expansion(producer)
    
    def process_admin_notifications(self):
        """Yöneticiler için akıllı bildirimler"""
        admins = User.objects.filter(is_superuser=True)
        
        for admin in admins:
            # 1. Sistem performans raporu
            self._send_performance_report(admin)
            
            # 2. Güvenlik uyarıları
            self._check_security_alerts(admin)
            
            # 3. İş akışı önerileri
            self._suggest_workflow_improvements(admin)
    
    def _check_inactive_center(self, center):
        """Pasif merkez kontrolü"""
        last_activity = center.molds.order_by('-created_at').first()
        
        if not last_activity:
            return
        
        days_inactive = (timezone.now() - last_activity.created_at).days
        
        if days_inactive >= 30:  # 30 gün pasif
            notify.send(
                sender=center.user,
                recipient=center.user,
                verb='uzun süredir pasif',
                description=f'{days_inactive} gündür yeni kalıp siparişi vermiyorsunuz. Yardıma ihtiyacınız var mı?',
                action_object=center,
                target=None
            )
            
            # Admin'e de bildir
            for admin in User.objects.filter(is_superuser=True):
                notify.send(
                    sender=center.user,
                    recipient=admin,
                    verb='merkez uzun süredir pasif',
                    description=f'{center.name} {days_inactive} gündür aktif değil. İletişime geçilmeli.',
                    action_object=center,
                    target=None
                )
    
    def _check_mold_limit_warning(self, center):
        """Kalıp limiti uyarısı"""
        used_molds = center.molds.count()
        limit_percentage = (used_molds / center.mold_limit) * 100
        
        if limit_percentage >= 80:  # %80 kullanım
            remaining = center.mold_limit - used_molds
            
            notify.send(
                sender=center.user,
                recipient=center.user,
                verb='kalıp limiti dolmak üzere',
                description=f'Kalıp limitinizin %{limit_percentage:.0f}\'ini kullandınız. {remaining} kalıp hakkınız kaldı.',
                action_object=center,
                target=None
            )
    
    def _check_completed_orders(self, center):
        """Tamamlanan siparişleri kontrol et"""
        # Son 24 saatte tamamlanan siparişler
        yesterday = timezone.now() - timedelta(days=1)
        completed_orders = ProducerOrder.objects.filter(
            center=center,
            status='delivered',
            actual_delivery__gte=yesterday
        )
        
        if completed_orders.exists():
            notify.send(
                sender=center.user,
                recipient=center.user,
                verb='siparişleriniz tamamlandı',
                description=f'{completed_orders.count()} adet kalıp siparişiniz tamamlandı ve teslim edildi.',
                action_object=center,
                target=None
            )
    
    def _check_revision_status(self, center):
        """Revizyon durumu kontrolü"""
        pending_revisions = RevisionRequest.objects.filter(
            modeled_mold__ear_mold__center=center,
            status='pending'
        )
        
        if pending_revisions.exists():
            old_revisions = pending_revisions.filter(
                created_at__lt=timezone.now() - timedelta(days=3)
            )
            
            if old_revisions.exists():
                notify.send(
                    sender=center.user,
                    recipient=center.user,
                    verb='revizyon taleplerinin durumu',
                    description=f'{old_revisions.count()} adet revizyon talebiniz 3 gündür beklemede. Takip etmek ister misiniz?',
                    action_object=center,
                    target=None
                )
    
    def _suggest_performance_improvements(self, center):
        """Performans iyileştirme önerileri"""
        # Son 30 günün analizi
        last_month = timezone.now() - timedelta(days=30)
        recent_orders = ProducerOrder.objects.filter(
            center=center,
            created_at__gte=last_month
        )
        
        if recent_orders.count() >= 5:  # Yeterli veri varsa
            avg_delivery = recent_orders.filter(
                actual_delivery__isnull=False
            ).aggregate(
                avg_days=Avg('actual_delivery') - Avg('created_at')
            )
            
            # Performans önerisi gönder (haftalık)
            last_suggestion = center.user.notifications.filter(
                verb__contains='performans önerisi'
            ).first()
            
            if not last_suggestion or (timezone.now() - last_suggestion.timestamp).days >= 7:
                notify.send(
                    sender=center.user,
                    recipient=center.user,
                    verb='performans önerisi',
                    description='Son ay siparişlerinizin analizi hazır. Dashboard\'tan detayları inceleyebilirsiniz.',
                    action_object=center,
                    target=None
                )
    
    def _check_pending_orders(self, producer):
        """Bekleyen siparişler kontrolü"""
        pending_orders = producer.orders.filter(
            status='received',
            created_at__lt=timezone.now() - timedelta(hours=24)
        )
        
        if pending_orders.exists():
            notify.send(
                sender=producer.user,
                recipient=producer.user,
                verb='bekleyen siparişler',
                description=f'{pending_orders.count()} adet sipariş 24 saattir beklemede. İşleme alınması gerekiyor.',
                action_object=producer,
                target=None
            )
    
    def _check_capacity_warning(self, producer):
        """Kapasite uyarısı"""
        current_month_orders = producer.get_current_month_orders()
        capacity_percentage = (current_month_orders / producer.mold_limit) * 100
        
        if capacity_percentage >= 90:  # %90 kapasite
            notify.send(
                sender=producer.user,
                recipient=producer.user,
                verb='kapasite dolmak üzere',
                description=f'Aylık kapasitenizin %{capacity_percentage:.0f}\'ini kullandınız. Planlama yapmanız önerilir.',
                action_object=producer,
                target=None
            )
    
    def _analyze_producer_performance(self, producer):
        """Üretici performans analizi"""
        # Son 30 günün performansı
        last_month = timezone.now() - timedelta(days=30)
        recent_orders = producer.orders.filter(created_at__gte=last_month)
        
        if recent_orders.count() >= 10:  # Yeterli veri
            on_time_delivery = recent_orders.filter(
                actual_delivery__lte=F('estimated_delivery')
            ).count()
            
            on_time_percentage = (on_time_delivery / recent_orders.count()) * 100
            
            if on_time_percentage < 70:  # %70'in altında zamanında teslimat
                notify.send(
                    sender=producer.user,
                    recipient=producer.user,
                    verb='teslimat performansı uyarısı',
                    description=f'Son ay teslimat performansınız %{on_time_percentage:.0f}. İyileştirme önerileri için iletişime geçin.',
                    action_object=producer,
                    target=None
                )
    
    def _suggest_network_expansion(self, producer):
        """Ağ genişletme önerisi"""
        current_networks = producer.network_centers.filter(status='active').count()
        
        # Kapasite kullanımı yüksekse ve az ağ varsa
        capacity_usage = producer.get_current_month_orders() / producer.mold_limit
        
        if capacity_usage > 0.8 and current_networks < 5:
            notify.send(
                sender=producer.user,
                recipient=producer.user,
                verb='ağ genişletme önerisi',
                description='Yüksek kapasite kullanımınız var. Daha fazla işitme merkezi ile ağ kurarak işinizi büyütebilirsiniz.',
                action_object=producer,
                target=None
            )
    
    def _send_performance_report(self, admin):
        """Performans raporu gönder"""
        # Haftalık rapor
        last_report = admin.notifications.filter(
            verb='haftalık performans raporu'
        ).first()
        
        if not last_report or (timezone.now() - last_report.timestamp).days >= 7:
            # Temel istatistikler
            total_orders = ProducerOrder.objects.count()
            active_orders = ProducerOrder.objects.filter(
                status__in=['received', 'designing', 'production']
            ).count()
            
            notify.send(
                sender=admin,
                recipient=admin,
                verb='haftalık performans raporu',
                description=f'Sistem özeti: {total_orders} toplam sipariş, {active_orders} aktif sipariş. Detaylar admin panelinde.',
                action_object=None,
                target=None
            )
    
    def _check_security_alerts(self, admin):
        """Güvenlik uyarıları"""
        # Güvenlik riski taşıyan üretici hesapları
        risky_producers = Producer.objects.filter(
            Q(user__is_staff=True) | Q(user__is_superuser=True)
        )
        
        if risky_producers.exists():
            notify.send(
                sender=admin,
                recipient=admin,
                verb='güvenlik uyarısı',
                description=f'{risky_producers.count()} üretici hesabının admin yetkisi var. Güvenlik riski!',
                action_object=None,
                target=None
            )
    
    def _suggest_workflow_improvements(self, admin):
        """İş akışı iyileştirme önerileri"""
        # Geciken siparişler
        overdue_orders = ProducerOrder.objects.filter(
            estimated_delivery__lt=timezone.now(),
            status__in=['received', 'designing', 'production']
        ).count()
        
        if overdue_orders > 10:
            notify.send(
                sender=admin,
                recipient=admin,
                verb='iş akışı önerisi',
                description=f'{overdue_orders} sipariş gecikmiş. Üretici kapasitelerini gözden geçirmeniz önerilir.',
                action_object=None,
                target=None
            )


# Kullanım için yardımcı fonksiyonlar
def send_smart_notifications():
    """Akıllı bildirimleri gönder - management command için"""
    manager = SmartNotificationManager()
    manager.process_all_notifications()


def send_center_notification(center_id, notification_type):
    """Belirli bir merkez için bildirim gönder"""
    try:
        center = Center.objects.get(id=center_id)
        manager = SmartNotificationManager()
        
        if notification_type == 'inactive':
            manager._check_inactive_center(center)
        elif notification_type == 'limit':
            manager._check_mold_limit_warning(center)
        # Diğer türler...
        
    except Center.DoesNotExist:
        pass


def send_producer_notification(producer_id, notification_type):
    """Belirli bir üretici için bildirim gönder"""
    try:
        producer = Producer.objects.get(id=producer_id)
        manager = SmartNotificationManager()
        
        if notification_type == 'pending':
            manager._check_pending_orders(producer)
        elif notification_type == 'capacity':
            manager._check_capacity_warning(producer)
        # Diğer türler...
        
    except Producer.DoesNotExist:
        pass 