"""
Kargo sistemi kurulum komutu
Türkiye'deki temel kargo firmalarını ve ayarları oluşturur
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import CargoCompany
from core.cargo_service import CargoManager


class Command(BaseCommand):
    help = 'Türkiye kargo sistemi için varsayılan firmaları ve ayarları oluşturur'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Mevcut kargo firmalarını sıfırla ve yeniden oluştur',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚛 Kargo Sistemi Kurulumu Başlatılıyor...\n')
        )

        if options['reset']:
            self.stdout.write('🔄 Mevcut kargo firmaları temizleniyor...')
            CargoCompany.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ Temizlik tamamlandı.\n'))

        # Varsayılan kargo firmalarını oluştur
        self.create_default_cargo_companies()

        # Test mesajı
        self.stdout.write(
            self.style.SUCCESS(
                '\n🎉 Kargo sistemi kurulumu başarıyla tamamlandı!\n'
                '📋 Kurulan firmalar:\n'
                '   • Aras Kargo\n'
                '   • MNG Kargo\n'
                '   • Yurtiçi Kargo\n'
                '   • PTT Kargo\n\n'
                '💡 Admin panelinden API anahtarlarını ayarlayabilirsiniz.'
            )
        )

    @transaction.atomic
    def create_default_cargo_companies(self):
        """Varsayılan kargo firmalarını oluştur"""

        default_companies = [
            {
                'name': 'aras',
                'display_name': 'Aras Kargo',
                'website': 'https://www.araskargo.com.tr',
                'logo_url': 'https://www.araskargo.com.tr/assets/images/logo.png',
                'base_price': 25.00,
                'kg_price': 5.00,
                'estimated_delivery_days': 1,
                'is_default': True,
                'is_active': True,
            },
            {
                'name': 'mng',
                'display_name': 'MNG Kargo',
                'website': 'https://www.mngkargo.com.tr',
                'logo_url': 'https://www.mngkargo.com.tr/assets/images/logo.png',
                'base_price': 20.00,
                'kg_price': 4.50,
                'estimated_delivery_days': 1,
                'is_default': False,
                'is_active': True,
            },
            {
                'name': 'yurtici',
                'display_name': 'Yurtiçi Kargo',
                'website': 'https://www.yurticikargo.com.tr',
                'logo_url': 'https://www.yurticikargo.com.tr/assets/images/logo.png',
                'base_price': 22.00,
                'kg_price': 4.80,
                'estimated_delivery_days': 1,
                'is_default': False,
                'is_active': True,
            },
            {
                'name': 'ptt',
                'display_name': 'PTT Kargo',
                'website': 'https://www.ptt.gov.tr',
                'logo_url': 'https://www.ptt.gov.tr/assets/images/logo.png',
                'base_price': 18.00,
                'kg_price': 4.00,
                'estimated_delivery_days': 2,
                'is_default': False,
                'is_active': True,
            },
            {
                'name': 'surat',
                'display_name': 'Sürat Kargo',
                'website': 'https://www.suratkargo.com.tr',
                'logo_url': 'https://www.suratkargo.com.tr/assets/images/logo.png',
                'base_price': 23.00,
                'kg_price': 4.20,
                'estimated_delivery_days': 1,
                'is_default': False,
                'is_active': True,
            },
            {
                'name': 'ups',
                'display_name': 'UPS',
                'website': 'https://www.ups.com/tr',
                'logo_url': 'https://www.ups.com/assets/resources/images/UPS_logo.svg',
                'base_price': 35.00,
                'kg_price': 6.50,
                'estimated_delivery_days': 2,
                'is_default': False,
                'is_active': True,
            },
            {
                'name': 'dhl',
                'display_name': 'DHL',
                'website': 'https://www.dhl.com/tr',
                'logo_url': 'https://www.dhl.com/assets/img/dhl-logo.svg',
                'base_price': 40.00,
                'kg_price': 7.00,
                'estimated_delivery_days': 2,
                'is_default': False,
                'is_active': True,
            }
        ]

        created_count = 0
        updated_count = 0

        for company_data in default_companies:
            company, created = CargoCompany.objects.get_or_create(
                name=company_data['name'],
                defaults=company_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    f'  ✅ {company_data["display_name"]} oluşturuldu'
                )
            else:
                # Güncelleme gerekli mi kontrol et
                updated = False
                for key, value in company_data.items():
                    if getattr(company, key) != value:
                        setattr(company, key, value)
                        updated = True

                if updated:
                    company.save()
                    updated_count += 1
                    self.stdout.write(
                        f'  🔄 {company_data["display_name"]} güncellendi'
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n📊 İşlem Özeti:\n'
                f'   • {created_count} firma oluşturuldu\n'
                f'   • {updated_count} firma güncellendi'
            )
        )
