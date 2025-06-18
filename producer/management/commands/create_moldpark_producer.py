from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from producer.models import Producer


class Command(BaseCommand):
    help = 'MoldPark kendi üretim merkezi oluşturur'

    def handle(self, *args, **options):
        # MoldPark üretim merkezi kullanıcısı oluştur
        username = 'moldpark_producer'
        email = 'uretim@moldpark.com'
        
        # Kullanıcı zaten varsa, onu kullan
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': 'MoldPark',
                'last_name': 'Üretim'
            }
        )
        
        if created:
            user.set_password('moldpark2024!')
            user.save()
            self.stdout.write(f'MoldPark kullanıcısı oluşturuldu: {username}')
        else:
            self.stdout.write(f'MoldPark kullanıcısı zaten mevcut: {username}')
        
        # MoldPark üretim merkezi oluştur
        producer, created = Producer.objects.get_or_create(
            user=user,
            defaults={
                'company_name': 'MoldPark Üretim Merkezi',
                'brand_name': 'MoldPark',
                'description': 'MoldPark platformunun resmi üretim merkezi. Dijital kulak kalıbı üretimi ve 3D modelleme hizmetleri.',
                'producer_type': 'hybrid',  # Hem üretici hem laboratuvar
                'address': 'Teknoloji Geliştirme Bölgesi, İnovasyon Caddesi No:15, 34906 Pendik/İstanbul',
                'phone': '(216) 555-0100',
                'contact_email': 'uretim@moldpark.com',
                'website': 'https://www.moldpark.com',
                'tax_number': '9876543210',
                'trade_registry': 'İstanbul-987654',
                'established_year': 2024,
                'mold_limit': 1000,  # Yüksek limit
                'monthly_limit': 5000,  # Çok yüksek limit
                'is_active': True,
                'is_verified': True,  # Otomatik doğrulanmış
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'MoldPark üretim merkezi oluşturuldu: {producer.company_name}'))
        else:
            # Mevcut üreticiyi güncelle
            producer.company_name = 'MoldPark Üretim Merkezi'
            producer.brand_name = 'MoldPark'
            producer.description = 'MoldPark platformunun resmi üretim merkezi. Dijital kulak kalıbı üretimi ve 3D modelleme hizmetleri.'
            producer.producer_type = 'hybrid'
            producer.address = 'Teknoloji Geliştirme Bölgesi, İnovasyon Caddesi No:15, 34906 Pendik/İstanbul'
            producer.phone = '(216) 555-0100'
            producer.contact_email = 'uretim@moldpark.com'
            producer.website = 'https://www.moldpark.com'
            producer.tax_number = '9876543210'
            producer.trade_registry = 'İstanbul-987654'
            producer.established_year = 2024
            producer.mold_limit = 1000
            producer.monthly_limit = 5000
            producer.is_active = True
            producer.is_verified = True
            producer.save()
            self.stdout.write(self.style.WARNING(f'MoldPark üretim merkezi güncellendi: {producer.company_name}'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'İşlem tamamlandı!\n'
                f'Kullanıcı: {user.username} ({user.email})\n'
                f'Üretici: {producer.company_name}\n'
                f'Tür: {producer.get_producer_type_display()}\n'
                f'Aylık Limit: {producer.mold_limit} kalıp\n'
                f'Durumu: {"Aktif" if producer.is_active else "Pasif"}, '
                f'{"Doğrulanmış" if producer.is_verified else "Doğrulanmamış"}\n'
                f'Bu üretici merkez artık kullanıcı kayıt formunda görünecek!'
            )
        ) 