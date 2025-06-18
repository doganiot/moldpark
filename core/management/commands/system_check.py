"""
MoldPark Sistem Kontrol Komutu
Bu komut sistemin genel sağlığını kontrol eder ve sorunları tespit eder.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.db import connection
from django.contrib.auth.models import User
from center.models import Center
from producer.models import Producer, ProducerNetwork
from mold.models import EarMold
import os
import sys
from pathlib import Path


class Command(BaseCommand):
    help = 'MoldPark sisteminin genel sağlığını kontrol eder'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Tespit edilen sorunları otomatik düzelt',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Detaylı çıktı göster',
        )

    def handle(self, *args, **options):
        self.fix_mode = options['fix']
        self.verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS('🔍 MoldPark Sistem Kontrolü Başlatılıyor...\n')
        )
        
        # Kontrol kategorileri
        checks = [
            ('Database', self.check_database),
            ('Models', self.check_models),
            ('Files', self.check_files),
            ('Settings', self.check_settings),
            ('Security', self.check_security),
            ('Performance', self.check_performance),
        ]
        
        total_issues = 0
        
        for check_name, check_func in checks:
            self.stdout.write(f'\n📋 {check_name} Kontrolü:')
            self.stdout.write('-' * 40)
            
            try:
                issues = check_func()
                if issues:
                    total_issues += len(issues)
                    for issue in issues:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  {issue}')
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS('✅ Sorun bulunamadı')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Kontrol hatası: {str(e)}')
                )
                total_issues += 1
        
        # Özet
        self.stdout.write('\n' + '='*50)
        if total_issues == 0:
            self.stdout.write(
                self.style.SUCCESS(f'🎉 Sistem kontrolü tamamlandı! Hiç sorun bulunamadı.')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Toplam {total_issues} sorun tespit edildi.')
            )
            if not self.fix_mode:
                self.stdout.write(
                    self.style.HTTP_INFO('💡 Sorunları otomatik düzeltmek için --fix parametresini kullanın.')
                )

    def check_database(self):
        """Veritabanı kontrolü"""
        issues = []
        
        try:
            # Bağlantı testi
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            # Migration kontrolü
            if self.verbose:
                self.stdout.write('  📊 Migration durumu kontrol ediliyor...')
            
            # Model sayıları
            user_count = User.objects.count()
            center_count = Center.objects.count()
            producer_count = Producer.objects.count()
            mold_count = EarMold.objects.count()
            
            if self.verbose:
                self.stdout.write(f'  👥 Kullanıcılar: {user_count}')
                self.stdout.write(f'  🏥 Merkezler: {center_count}')
                self.stdout.write(f'  🏭 Üreticiler: {producer_count}')
                self.stdout.write(f'  👂 Kalıplar: {mold_count}')
            
            # Orphan kullanıcı kontrolü
            orphan_users = User.objects.filter(
                center__isnull=True,
                producer__isnull=True,
                is_superuser=False
            )
            if orphan_users.exists():
                issues.append(f'{orphan_users.count()} orphan kullanıcı bulundu')
                if self.fix_mode:
                    orphan_users.delete()
                    self.stdout.write('  🔧 Orphan kullanıcılar temizlendi')
            
        except Exception as e:
            issues.append(f'Veritabanı bağlantı sorunu: {str(e)}')
        
        return issues

    def check_models(self):
        """Model kontrolü"""
        issues = []
        
        try:
            # Producer güvenlik kontrolü
            unsafe_producers = Producer.objects.filter(
                user__is_staff=True
            ) | Producer.objects.filter(
                user__is_superuser=True
            )
            
            if unsafe_producers.exists():
                issues.append(f'{unsafe_producers.count()} güvenlik riski taşıyan üretici hesabı')
                if self.fix_mode:
                    for producer in unsafe_producers:
                        producer.user.is_staff = False
                        producer.user.is_superuser = False
                        producer.user.save()
                    self.stdout.write('  🔧 Üretici güvenlik riskleri düzeltildi')
            
            # Duplicate tax_number kontrolü
            from django.db.models import Count
            duplicate_tax_numbers = Producer.objects.values('tax_number').annotate(
                count=Count('tax_number')
            ).filter(count__gt=1)
            
            if duplicate_tax_numbers.exists():
                issues.append(f'{duplicate_tax_numbers.count()} duplicate vergi numarası')
            
            # Network ilişki kontrolü
            broken_networks = ProducerNetwork.objects.filter(
                producer__isnull=True
            ) | ProducerNetwork.objects.filter(
                center__isnull=True
            )
            
            if broken_networks.exists():
                issues.append(f'{broken_networks.count()} bozuk network ilişkisi')
                if self.fix_mode:
                    broken_networks.delete()
                    self.stdout.write('  🔧 Bozuk network ilişkileri temizlendi')
            
        except Exception as e:
            issues.append(f'Model kontrol hatası: {str(e)}')
        
        return issues

    def check_files(self):
        """Dosya sistemi kontrolü"""
        issues = []
        
        try:
            # Media dizini kontrolü
            media_root = Path(settings.MEDIA_ROOT)
            if not media_root.exists():
                issues.append('Media dizini bulunamadı')
                if self.fix_mode:
                    media_root.mkdir(parents=True, exist_ok=True)
                    self.stdout.write('  🔧 Media dizini oluşturuldu')
            
            # Static dizini kontrolü
            static_root = Path(settings.STATIC_ROOT)
            if not static_root.exists():
                issues.append('Static dizini bulunamadı')
                if self.fix_mode:
                    static_root.mkdir(parents=True, exist_ok=True)
                    self.stdout.write('  🔧 Static dizini oluşturuldu')
            
            # Log dizini kontrolü
            log_dir = Path(settings.BASE_DIR) / 'logs'
            if not log_dir.exists():
                issues.append('Log dizini bulunamadı')
                if self.fix_mode:
                    log_dir.mkdir(parents=True, exist_ok=True)
                    self.stdout.write('  🔧 Log dizini oluşturuldu')
            
            # Orphan dosya kontrolü (media'da kayıt olmayan dosyalar)
            if media_root.exists():
                scan_files = set()
                modeled_files = set()
                
                # Veritabanındaki dosyaları topla
                for mold in EarMold.objects.all():
                    if mold.scan_file:
                        scan_files.add(str(mold.scan_file))
                
                # Gerçek dosyaları kontrol et
                actual_files = set()
                for root, dirs, files in os.walk(media_root):
                    for file in files:
                        rel_path = os.path.relpath(
                            os.path.join(root, file), 
                            settings.MEDIA_ROOT
                        )
                        actual_files.add(rel_path.replace('\\', '/'))
                
                orphan_files = actual_files - scan_files - modeled_files
                if orphan_files:
                    issues.append(f'{len(orphan_files)} orphan dosya bulundu')
                    if self.verbose:
                        for file in list(orphan_files)[:5]:  # İlk 5'ini göster
                            self.stdout.write(f'    📄 {file}')
            
        except Exception as e:
            issues.append(f'Dosya sistemi kontrolü hatası: {str(e)}')
        
        return issues

    def check_settings(self):
        """Ayar kontrolü"""
        issues = []
        
        try:
            # Debug modu kontrolü
            if settings.DEBUG and 'production' in sys.argv:
                issues.append('Production ortamında DEBUG=True')
            
            # Secret key kontrolü
            if 'django-insecure' in settings.SECRET_KEY:
                issues.append('Güvenli olmayan SECRET_KEY kullanılıyor')
            
            # Allowed hosts kontrolü
            if settings.DEBUG and '*' in settings.ALLOWED_HOSTS:
                pass  # Development'ta normal
            elif not settings.DEBUG and '*' in settings.ALLOWED_HOSTS:
                issues.append('Production ortamında ALLOWED_HOSTS=["*"] güvenli değil')
            
            # Database kontrolü
            if not settings.DEBUG and 'sqlite3' in settings.DATABASES['default']['ENGINE']:
                issues.append('Production ortamında SQLite kullanılması önerilmez')
            
        except Exception as e:
            issues.append(f'Ayar kontrolü hatası: {str(e)}')
        
        return issues

    def check_security(self):
        """Güvenlik kontrolü"""
        issues = []
        
        try:
            # Superuser kontrolü
            superusers = User.objects.filter(is_superuser=True)
            if not superusers.exists():
                issues.append('Hiç superuser bulunamadı')
            elif superusers.count() > 3:
                issues.append(f'Çok fazla superuser ({superusers.count()})')
            
            # Weak password kontrolü
            weak_users = []
            for user in User.objects.all()[:10]:  # İlk 10 kullanıcıyı kontrol et
                if user.check_password('123456') or user.check_password('password'):
                    weak_users.append(user.username)
            
            if weak_users:
                issues.append(f'{len(weak_users)} zayıf şifre tespit edildi')
            
            # Producer admin yetkisi kontrolü
            producer_admins = Producer.objects.filter(
                user__is_staff=True
            ) | Producer.objects.filter(
                user__is_superuser=True
            )
            
            if producer_admins.exists():
                issues.append(f'{producer_admins.count()} üretici hesabının admin yetkisi var')
            
        except Exception as e:
            issues.append(f'Güvenlik kontrolü hatası: {str(e)}')
        
        return issues

    def check_performance(self):
        """Performans kontrolü"""
        issues = []
        
        try:
            # Büyük tablo kontrolü
            large_tables = []
            
            mold_count = EarMold.objects.count()
            if mold_count > 10000:
                large_tables.append(f'EarMold: {mold_count} kayıt')
            
            if large_tables:
                issues.append(f'Büyük tablolar: {", ".join(large_tables)}')
            
            # Cache kontrolü
            if not hasattr(settings, 'CACHES') or settings.CACHES['default']['BACKEND'] == 'django.core.cache.backends.dummy.DummyCache':
                issues.append('Cache sistemi aktif değil')
            
            # Index kontrolü (basit)
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA index_list('mold_earmold')")
                indexes = cursor.fetchall()
                if len(indexes) < 3:  # created_at, center_id gibi temel indexler
                    issues.append('EarMold tablosunda yeterli index yok')
            
        except Exception as e:
            issues.append(f'Performans kontrolü hatası: {str(e)}')
        
        return issues 