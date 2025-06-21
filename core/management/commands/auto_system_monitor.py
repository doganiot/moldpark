"""
MoldPark Otomatik Sistem İzleme Komutu
Bu komut sistemin otomatik olarak izlenmesi ve sorunların tespit edilmesi için kullanılır.
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from center.models import Center
from producer.models import Producer, ProducerOrder, ProducerNetwork
from mold.models import EarMold
from notifications.signals import notify
import logging


class Command(BaseCommand):
    help = 'MoldPark sisteminin otomatik izlenmesi ve uyarı gönderimi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-alerts',
            action='store_true',
            help='Sorun tespit edildiğinde e-posta uyarısı gönder',
        )
        parser.add_argument(
            '--alert-threshold',
            type=int,
            default=5,
            help='Uyarı gönderilecek sorun sayısı eşiği (varsayılan: 5)',
        )

    def handle(self, *args, **options):
        self.send_alerts = options['send_alerts']
        self.alert_threshold = options['alert_threshold']
        
        logger = logging.getLogger('moldpark')
        
        self.stdout.write(
            self.style.SUCCESS('🔍 MoldPark Otomatik Sistem İzleme Başlatılıyor...\n')
        )
        
        # Kritik kontroller
        critical_issues = []
        warnings = []
        
        # 1. Geciken Siparişler
        overdue_orders = self.check_overdue_orders()
        if overdue_orders['count'] > 0:
            if overdue_orders['count'] > 10:
                critical_issues.append(overdue_orders)
            else:
                warnings.append(overdue_orders)
        
        # 2. Sistem Performansı
        performance_issues = self.check_performance()
        if performance_issues:
            warnings.extend(performance_issues)
        
        # 3. Güvenlik Kontrolleri
        security_issues = self.check_security()
        if security_issues:
            critical_issues.extend(security_issues)
        
        # 4. Disk Alanı Kontrolü
        disk_issues = self.check_disk_space()
        if disk_issues:
            warnings.extend(disk_issues)
        
        # 5. Ağ Bağlantı Sorunları
        network_issues = self.check_network_health()
        if network_issues:
            warnings.extend(network_issues)
        
        # Raporlama
        total_issues = len(critical_issues) + len(warnings)
        
        if total_issues == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ Sistem sağlıklı - hiçbir sorun tespit edilmedi.')
            )
            logger.info('Sistem sağlık kontrolü: Sorun yok')
            
        else:
            # Kritik sorunları rapor et
            if critical_issues:
                self.stdout.write(
                    self.style.ERROR(f'🚨 {len(critical_issues)} KRİTİK SORUN TESPİT EDİLDİ:')
                )
                for issue in critical_issues:
                    self.stdout.write(f'  ❌ {issue["message"]}')
                    logger.error(f'Kritik sorun: {issue["message"]}')
            
            # Uyarıları rapor et
            if warnings:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  {len(warnings)} UYARI TESPİT EDİLDİ:')
                )
                for warning in warnings:
                    self.stdout.write(f'  ⚠️  {warning["message"]}')
                    logger.warning(f'Uyarı: {warning["message"]}')
            
            # E-posta uyarısı gönder
            if self.send_alerts and total_issues >= self.alert_threshold:
                self.send_alert_email(critical_issues, warnings)
                
            # Admin kullanıcılarına bildirim gönder
            if critical_issues:
                self.send_admin_notifications(critical_issues, warnings)
        
        # İstatistikleri logla
        self.log_system_stats()

    def check_overdue_orders(self):
        """Geciken siparişleri kontrol et"""
        now = timezone.now()
        overdue_orders = ProducerOrder.objects.filter(
            estimated_delivery__lt=now,
            status__in=['received', 'designing', 'production', 'quality_check']
        )
        
        return {
            'type': 'overdue_orders',
            'count': overdue_orders.count(),
            'message': f'{overdue_orders.count()} sipariş tahmini teslimat tarihini geçti',
            'details': list(overdue_orders.values(
                'order_number', 'estimated_delivery', 'status'
            )[:10])  # İlk 10 tanesini al
        }

    def check_performance(self):
        """Sistem performansını kontrol et"""
        issues = []
        
        # Büyük tablo kontrolü
        mold_count = EarMold.objects.count()
        if mold_count > 50000:
            issues.append({
                'type': 'large_table',
                'message': f'EarMold tablosu çok büyük: {mold_count} kayıt - indeksleme gerekebilir'
            })
        
        # Orphan kayıt kontrolü
        orphan_users = User.objects.filter(
            center__isnull=True,
            producer__isnull=True,
            is_superuser=False
        ).count()
        
        if orphan_users > 10:
            issues.append({
                'type': 'orphan_records',
                'message': f'{orphan_users} orphan kullanıcı kayıt - temizleme gerekebilir'
            })
        
        return issues

    def check_security(self):
        """Güvenlik sorunlarını kontrol et"""
        issues = []
        
        # Producer admin yetkisi kontrolü
        producer_admins = Producer.objects.filter(
            user__is_staff=True
        ) | Producer.objects.filter(
            user__is_superuser=True
        )
        
        if producer_admins.exists():
            issues.append({
                'type': 'security_risk',
                'message': f'{producer_admins.count()} üretici hesabının admin yetkisi var - GÜVENLİK RİSKİ!'
            })
        
        # Zayıf şifre kontrolü (basit kontrol)
        recent_users = User.objects.filter(
            date_joined__gte=timezone.now() - timezone.timedelta(days=7)
        )
        
        weak_passwords = 0
        for user in recent_users[:20]:  # Son 20 kullanıcı
            if user.check_password('123456') or user.check_password('password'):
                weak_passwords += 1
        
        if weak_passwords > 0:
            issues.append({
                'type': 'weak_passwords',
                'message': f'{weak_passwords} kullanıcı zayıf şifre kullanıyor'
            })
        
        return issues

    def check_disk_space(self):
        """Disk alanı kontrolü"""
        issues = []
        
        # Bu basit bir implementasyon - production'da daha gelişmiş olabilir
        try:
            import shutil
            total, used, free = shutil.disk_usage(settings.BASE_DIR)
            
            # GB'ye çevir
            free_gb = free // (1024**3)
            usage_percent = (used / total) * 100
            
            if usage_percent > 85:
                issues.append({
                    'type': 'disk_space',
                    'message': f'Disk kullanımı %{usage_percent:.1f} - {free_gb}GB boş alan kaldı'
                })
        except:
            pass
        
        return issues

    def check_network_health(self):
        """Ağ bağlantı sağlığını kontrol et"""
        issues = []
        
        # Askıya alınmış ağlar
        suspended_networks = ProducerNetwork.objects.filter(status='suspended').count()
        if suspended_networks > 5:
            issues.append({
                'type': 'suspended_networks',
                'message': f'{suspended_networks} üretici ağı askıya alınmış'
            })
        
        # Sonlandırılmış ağlar (son 7 gün)
        recent_terminated = ProducerNetwork.objects.filter(
            status='terminated',
            terminated_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()
        
        if recent_terminated > 10:
            issues.append({
                'type': 'network_terminations',
                'message': f'{recent_terminated} ağ son 7 günde sonlandırıldı - anormal aktivite olabilir'
            })
        
        return issues

    def send_alert_email(self, critical_issues, warnings):
        """E-posta uyarısı gönder"""
        try:
            subject = f'🚨 MoldPark Sistem Uyarısı - {len(critical_issues + warnings)} sorun tespit edildi'
            
            message_lines = [
                'MoldPark Sistem İzleme Raporu',
                '=' * 40,
                f'Tarih: {timezone.now().strftime("%d.%m.%Y %H:%M")}',
                '',
            ]
            
            if critical_issues:
                message_lines.extend([
                    'KRİTİK SORUNLAR:',
                    '-' * 20,
                ])
                for issue in critical_issues:
                    message_lines.append(f'❌ {issue["message"]}')
                message_lines.append('')
            
            if warnings:
                message_lines.extend([
                    'UYARILAR:',
                    '-' * 10,
                ])
                for warning in warnings:
                    message_lines.append(f'⚠️  {warning["message"]}')
            
            message_lines.extend([
                '',
                'Detaylı inceleme için admin panelini kontrol edin.',
                '',
                'Bu otomatik bir mesajdır.',
            ])
            
            message = '\n'.join(message_lines)
            
            # Admin e-postalarını al
            admin_emails = User.objects.filter(
                is_superuser=True,
                email__isnull=False
            ).exclude(email='').values_list('email', flat=True)
            
            if admin_emails:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@moldpark.com'),
                    recipient_list=list(admin_emails),
                    fail_silently=False,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'📧 E-posta uyarısı {len(admin_emails)} admin\'e gönderildi.')
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'E-posta gönderim hatası: {str(e)}')
            )

    def send_admin_notifications(self, critical_issues, warnings):
        """Admin kullanıcılarına sistem bildirimi gönder"""
        try:
            admins = User.objects.filter(is_superuser=True)
            
            for admin in admins:
                notify.send(
                    sender=admin,  # Sistem bildirimi
                    recipient=admin,
                    verb='sistem uyarısı',
                    description=f'{len(critical_issues)} kritik sorun, {len(warnings)} uyarı tespit edildi. Admin panelini kontrol edin.',
                    action_object=None,
                    target=None
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'🔔 {len(admins)} admin\'e bildirim gönderildi.')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Bildirim gönderim hatası: {str(e)}')
            )

    def log_system_stats(self):
        """Temel sistem istatistiklerini logla"""
        logger = logging.getLogger('moldpark')
        
        stats = {
            'timestamp': timezone.now().isoformat(),
            'users': User.objects.count(),
            'centers': Center.objects.count(),
            'producers': Producer.objects.count(),
            'verified_producers': Producer.objects.filter(is_verified=True).count(),
            'total_orders': ProducerOrder.objects.count(),
            'active_orders': ProducerOrder.objects.filter(
                status__in=['received', 'designing', 'production', 'quality_check']
            ).count(),
            'total_molds': EarMold.objects.count(),
            'active_networks': ProducerNetwork.objects.filter(status='active').count(),
        }
        
        logger.info(f'Sistem istatistikleri: {stats}')
        
        self.stdout.write(
            self.style.HTTP_INFO(f'📊 Sistem istatistikleri kaydedildi.')
        ) 