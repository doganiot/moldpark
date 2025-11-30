from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from center.models import Center


class Command(BaseCommand):
    help = 'Test işitme merkezi oluşturur'

    def handle(self, *args, **options):
        # Test işitme merkezi kullanıcısı oluştur
        username = 'test_center'
        email = 'test@center.com'
        
        # Kullanıcı zaten varsa, onu kullan
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': 'Test',
                'last_name': 'Center'
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f'Test kullanıcısı oluşturuldu: {username}')
        else:
            self.stdout.write(f'Test kullanıcısı zaten mevcut: {username}')
        
        # Test işitme merkezi oluştur
        center, created = Center.objects.get_or_create(
            user=user,
            defaults={
                'name': 'Test İşitme Merkezi',
                'phone': '(212) 555-0456',
                'address': 'Test Mahallesi, Merkez Sokak No:2, İstanbul',
                'mold_limit': 50,
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Test işitme merkezi oluşturuldu: {center.name}'))
        else:
            # Mevcut merkezi güncelle
            center.is_active = True
            center.save()
            self.stdout.write(self.style.WARNING(f'Test işitme merkezi güncellendi: {center.name}'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'İşlem tamamlandı!\n'
                f'Kullanıcı: {user.username} ({user.email})\n'
                f'Merkez: {center.name}\n'
                f'Durumu: {"Aktif" if center.is_active else "Pasif"}'
            )
        )

