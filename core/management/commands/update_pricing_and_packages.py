"""
MoldPark - Fiyatlandırma ve Paket Güncelleme Komutu
Bu komut fiyatlandırmayı günceller ve yeni paketleri oluşturur
"""
from django.core.management.base import BaseCommand
from core.models import PricingConfiguration, PricingPlan
from django.utils import timezone


class Command(BaseCommand):
    help = 'Fiyatlandırmayı günceller ve yeni paketleri oluşturur'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Fiyatlandırma ve paketler güncelleniyor...'))
        
        # 1. Aktif fiyatlandırmayı güncelle veya oluştur
        active_pricing = PricingConfiguration.objects.filter(is_active=True).first()
        
        if active_pricing:
            self.stdout.write(f'Mevcut aktif fiyatlandırma bulundu: {active_pricing.name}')
            active_pricing.monthly_system_fee = 0.00
            active_pricing.physical_mold_price = 450.00
            active_pricing.digital_modeling_price = 19.00
            active_pricing.name = '2025 Güncel Fiyatlandırma'
            active_pricing.description = '''
MoldPark 2025 yılı güncel fiyatlandırma yapılandırması.
- Aylık Sistem Kullanımı: 0,00 TL (ÜCRETSİZ)
- Fiziksel kalıp: 450,00 TL (KDV Dahil)
- 3D Modelleme: 19,00 TL (KDV Dahil)
- MoldPark Komisyonu: %6.5
- Kredi Kartı Komisyonu: %3
- KDV Oranı: %20
            '''.strip()
            active_pricing.save()
            self.stdout.write(self.style.SUCCESS('[OK] Fiyatlandirma guncellendi'))
        else:
            active_pricing = PricingConfiguration.objects.create(
                name='2025 Güncel Fiyatlandırma',
                description='''
MoldPark 2025 yılı güncel fiyatlandırma yapılandırması.
- Aylık Sistem Kullanımı: 0,00 TL (ÜCRETSİZ)
- Fiziksel kalıp: 450,00 TL (KDV Dahil)
- 3D Modelleme: 19,00 TL (KDV Dahil)
- MoldPark Komisyonu: %6.5
- Kredi Kartı Komisyonu: %3
- KDV Oranı: %20
                '''.strip(),
                physical_mold_price=450.00,
                digital_modeling_price=19.00,
                monthly_system_fee=0.00,
                moldpark_commission_rate=6.50,
                credit_card_commission_rate=3.00,
                vat_rate=20.00,
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS('[OK] Yeni fiyatlandirma olusturuldu'))
        
        # 2. Eski paketleri temizle (isteğe bağlı - yorum satırına alabilirsiniz)
        # PricingPlan.objects.all().delete()
        
        # 3. Yeni paketleri oluştur
        packages = [
            {
                'name': 'Paket 1 - 5 Kalıp',
                'description': '5 kalıp için özel paket. Toplam 2100,00 TL. Birim fiyat: 420,00 TL/kalıp.',
                'mold_count': 5,
                'total_price': 2100.00,
                'unit_price': 420.00,
                'order': 1,
                'is_featured': False,
            },
            {
                'name': 'Paket 2 - 10 Kalıp',
                'description': '10 kalıp için özel paket. Toplam 3990,00 TL. Birim fiyat: 399,00 TL/kalıp.',
                'mold_count': 10,
                'total_price': 3990.00,
                'unit_price': 399.00,
                'order': 2,
                'is_featured': True,  # En popüler
            },
            {
                'name': 'Paket 3 - 20 Kalıp',
                'description': '20 kalıp için özel paket. Toplam 7580,00 TL. Birim fiyat: 379,00 TL/kalıp.',
                'mold_count': 20,
                'total_price': 7580.00,
                'unit_price': 379.00,
                'order': 3,
                'is_featured': False,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for pkg in packages:
            plan, created = PricingPlan.objects.update_or_create(
                name=pkg['name'],
                defaults={
                    'plan_type': 'package',
                    'description': pkg['description'],
                    'monthly_fee_try': 0.00,  # Abonelik ücreti yok
                    'per_mold_price_try': pkg['unit_price'],  # Birim fiyat
                    'modeling_service_fee_try': 19.00,  # 3D modelleme
                    'price_try': pkg['total_price'],  # Toplam paket fiyatı
                    'monthly_model_limit': pkg['mold_count'],  # Paket içindeki kalıp sayısı
                    'is_monthly': False,  # Paket sistemi, aylık değil
                    'is_active': True,
                    'is_featured': pkg['is_featured'],
                    'order': pkg['order'],
                    'features': [
                        f'{pkg["mold_count"]} kalıp hakkı',
                        f'Birim fiyat: {pkg["unit_price"]:.2f} TL',
                        '3D modelleme: 19,00 TL',
                        'Ücretsiz abonelik',
                        'Hızlı teslimat',
                        'Premium kalite',
                    ]
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'[OK] Paket olusturuldu: {plan.name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'[OK] Paket guncellendi: {plan.name}'))
        
        # 4. Tek kalıp seçeneği (isteğe bağlı)
        single_mold_plan, created = PricingPlan.objects.update_or_create(
            name='Tek Kalıp',
            defaults={
                'plan_type': 'single',
                'description': 'Tek kalıp için ödeme. Fiyat: 450,00 TL/kalıp.',
                'monthly_fee_try': 0.00,
                'per_mold_price_try': 450.00,
                'modeling_service_fee_try': 19.00,
                'price_try': 450.00,
                'monthly_model_limit': 1,
                'is_monthly': False,
                'is_active': True,
                'is_featured': False,
                'order': 0,
                'features': [
                    'Tek kalıp',
                    'Fiyat: 450,00 TL',
                    '3D modelleme: 19,00 TL',
                    'Ücretsiz abonelik',
                    'Anında işleme',
                ]
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('[OK] Tek kalip secenegi olusturuldu'))
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Tek kalip secenegi guncellendi'))
        
        # Özet
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS('Fiyatlandırma ve Paket Güncellemesi Tamamlandı!'))
        self.stdout.write('=' * 60)
        self.stdout.write('')
        self.stdout.write('Fiyatlandırma:')
        self.stdout.write(f'  • Aylık Sistem Ücreti: {active_pricing.monthly_system_fee:.2f} TL')
        self.stdout.write(f'  • Fiziksel Kalıp: {active_pricing.physical_mold_price:.2f} TL')
        self.stdout.write(f'  • 3D Modelleme: {active_pricing.digital_modeling_price:.2f} TL')
        self.stdout.write('')
        self.stdout.write('Paketler:')
        for plan in PricingPlan.objects.filter(is_active=True).order_by('order'):
            if plan.monthly_model_limit:
                self.stdout.write(f'  • {plan.name}: {plan.monthly_model_limit} kalıp - {plan.price_try:.2f} TL (Birim: {plan.per_mold_price_try:.2f} TL)')
            else:
                self.stdout.write(f'  • {plan.name}: {plan.price_try:.2f} TL')
        self.stdout.write('=' * 60)

