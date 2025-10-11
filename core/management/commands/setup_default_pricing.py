"""
MoldPark - Varsayılan Fiyatlandırma Kurulum Komutu
Bu komut sistemde varsayılan fiyatlandırma yapılandırmasını oluşturur
"""
from django.core.management.base import BaseCommand
from core.models import PricingConfiguration


class Command(BaseCommand):
    help = 'Varsayılan fiyatlandırma yapılandırmasını oluşturur'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Varsayılan fiyatlandırma yapılandırması oluşturuluyor...'))
        
        # Mevcut aktif fiyatlandırmayı kontrol et
        existing_active = PricingConfiguration.objects.filter(is_active=True).first()
        
        if existing_active:
            self.stdout.write(
                self.style.WARNING(
                    f'Zaten aktif bir fiyatlandırma mevcut: {existing_active.name}'
                )
            )
            self.stdout.write('Yeni fiyatlandırma oluşturulmadı.')
            return
        
        # Varsayılan fiyatlandırma oluştur
        pricing = PricingConfiguration.objects.create(
            name='2025 Standart Fiyatlandırma',
            description='''
MoldPark 2025 yılı standart fiyatlandırma yapılandırması.
- Aylık Sistem Kullanımı: 100 TL
- Fiziksel kalıp: 450 TL (KDV Dahil)
- 3D Modelleme: 50 TL (KDV Dahil)
- MoldPark Komisyonu: %6.5
- Kredi Kartı Komisyonu: %3
- KDV Oranı: %20
            '''.strip(),
            physical_mold_price=450.00,
            digital_modeling_price=50.00,
            monthly_system_fee=100.00,
            moldpark_commission_rate=6.50,
            credit_card_commission_rate=3.00,
            vat_rate=20.00,
            is_active=True
        )
        
        self.stdout.write(self.style.SUCCESS('[OK] Varsayilan fiyatlandirma basariyla olusturuldu!'))
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Fiyatlandırma Adı: {pricing.name}')
        self.stdout.write(f'Geçerlilik Tarihi: {pricing.effective_date}')
        self.stdout.write('')
        self.stdout.write('Fiyatlar:')
        self.stdout.write(f'  • Fiziksel Kalıp: {pricing.physical_mold_price} TL')
        self.stdout.write(f'  • 3D Modelleme: {pricing.digital_modeling_price} TL')
        self.stdout.write(f'  • Aylık Sistem Ücreti: {pricing.monthly_system_fee} TL')
        self.stdout.write('')
        self.stdout.write('Komisyon Oranları:')
        self.stdout.write(f'  • MoldPark: %{pricing.moldpark_commission_rate}')
        self.stdout.write(f'  • Kredi Kartı: %{pricing.credit_card_commission_rate}')
        self.stdout.write(f'  • KDV: %{pricing.vat_rate}')
        self.stdout.write('=' * 60)
        self.stdout.write('')
        
        # Hesaplama özeti
        summary = pricing.get_pricing_summary()
        self.stdout.write('Hesaplama Özeti:')
        self.stdout.write('')
        self.stdout.write('Fiziksel Kalıp:')
        self.stdout.write(f'  • KDV Dahil: {summary["physical"]["with_vat"]:.2f} TL')
        self.stdout.write(f'  • KDV Hariç: {summary["physical"]["without_vat"]:.2f} TL')
        self.stdout.write(f'  • MoldPark Komisyonu: {summary["physical"]["moldpark_fee"]:.2f} TL')
        self.stdout.write(f'  • Üreticiye Net: {summary["physical"]["net_to_producer"]:.2f} TL')
        self.stdout.write('')
        self.stdout.write('3D Modelleme:')
        self.stdout.write(f'  • KDV Dahil: {summary["digital"]["with_vat"]:.2f} TL')
        self.stdout.write(f'  • KDV Hariç: {summary["digital"]["without_vat"]:.2f} TL')
        self.stdout.write(f'  • MoldPark Komisyonu: {summary["digital"]["moldpark_fee"]:.2f} TL')
        self.stdout.write(f'  • Üreticiye Net: {summary["digital"]["net_to_producer"]:.2f} TL')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Fiyatlandirma sistemi kullanima hazir!'))

