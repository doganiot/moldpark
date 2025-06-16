from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from producer.models import Producer


class Command(BaseCommand):
    help = 'Test üreticisi oluşturur'

    def handle(self, *args, **options):
        # Test üreticisi kullanıcısı oluştur
        username = 'test_producer'
        email = 'test@producer.com'
        
        # Kullanıcı zaten varsa, onu kullan
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': 'Test',
                'last_name': 'Producer'
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f'Test kullanıcısı oluşturuldu: {username}')
        else:
            self.stdout.write(f'Test kullanıcısı zaten mevcut: {username}')
        
        # Test üreticisi oluştur
        producer, created = Producer.objects.get_or_create(
            user=user,
            defaults={
                'company_name': 'Test Kalıp Üretim A.Ş.',
                'brand_name': 'TestKalıp',
                'description': 'Test amaçlı oluşturulmuş üretici merkezi',
                'producer_type': 'manufacturer',
                'address': 'Test Mahallesi, Test Sokak No:1, İstanbul',
                'phone': '(212) 555-0123',
                'contact_email': 'info@testuretici.com',
                'website': 'https://www.testuretici.com',
                'tax_number': '1234567890',
                'trade_registry': 'İstanbul-123456',
                'established_year': 2020,
                'mold_limit': 100,
                'monthly_limit': 500,
                'is_active': True,
                'is_verified': True,  # Test için doğrulanmış olarak ayarla
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Test üreticisi oluşturuldu: {producer.company_name}'))
        else:
            # Mevcut üreticiyi güncelle
            producer.is_active = True
            producer.is_verified = True
            producer.save()
            self.stdout.write(self.style.WARNING(f'Test üreticisi güncellendi: {producer.company_name}'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'İşlem tamamlandı!\n'
                f'Kullanıcı: {user.username} ({user.email})\n'
                f'Üretici: {producer.company_name}\n'
                f'Durumu: {"Aktif" if producer.is_active else "Pasif"}, '
                f'{"Doğrulanmış" if producer.is_verified else "Doğrulanmamış"}'
            )
        ) 