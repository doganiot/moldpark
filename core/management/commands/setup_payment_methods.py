"""
Odeme yontemlerini kuran management command
"""
import sys
from django.core.management.base import BaseCommand
from core.models import BankTransferConfiguration, PaymentMethod

# UTF-8 encoding icin
sys.stdout.reconfigure(encoding='utf-8')


class Command(BaseCommand):
    help = 'Test icin kredi karti ve havale odeme yontemlerini kur'

    def handle(self, *args, **options):
        self.stdout.write('[INFO] Odeme yontemleri kuruluyor...\n')
        
        # 1. Havale yapılandırması oluştur
        bank_config, created = BankTransferConfiguration.objects.update_or_create(
            iban='5698542147852332',
            defaults={
                'bank_name': 'XYZ Bankası',
                'account_holder': 'MoldPark Yazılım A.Ş.',
                'swift_code': 'XYZBTRISXXX',
                'branch_code': '0123',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Havale Yapilandirmasi Olusturuldu:\n'
                    f'  - IBAN: {bank_config.iban}\n'
                    f'  - Banka: {bank_config.bank_name}\n'
                    f'  - Hesap Sahibi: {bank_config.account_holder}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Havale Yapilandirmasi Guncellesti rildi:\n'
                    f'  - IBAN: {bank_config.iban}'
                )
            )
        
        # 2. Kredi Kartı ödeme yöntemi oluştur
        credit_card_method, created = PaymentMethod.objects.update_or_create(
            method_type='credit_card',
            defaults={
                'name': 'Kredi Kartı (Test)',
                'description': 'Kredi kartı ile ödeme yapabilirsiniz. Ödeme anında işlenir.',
                'is_active': True,
                'is_default': True,
                'order': 1
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n[OK] Kredi Karti Odeme Yontemi Olusturuldu:\n'
                    f'  - Ad: {credit_card_method.name}\n'
                    f'  - Durum: Aktif'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n[OK] Kredi Karti Odeme Yontemi Guncellesti rildi'
                )
            )
        
        # 3. Havale ödeme yöntemi oluştur
        bank_transfer_method, created = PaymentMethod.objects.update_or_create(
            method_type='bank_transfer',
            defaults={
                'name': 'Havale/EFT',
                'description': 'Banka havalesı veya EFT ile ödeme yapabilirsiniz. Ödemeniz onaylandıktan sonra işlenir.',
                'bank_transfer_config': bank_config,
                'is_active': True,
                'is_default': False,
                'order': 2
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n[OK] Havale/EFT Odeme Yontemi Olusturuldu:\n'
                    f'  - Ad: {bank_transfer_method.name}\n'
                    f'  - IBAN: {bank_transfer_method.bank_transfer_config.iban}\n'
                    f'  - Durum: Aktif'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n[OK] Havale/EFT Odeme Yontemi Guncellesti rildi'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                '\n[BASARILI] Tum odeme yontemleri basarili kuruldu!\n'
            )
        )
        
        self.stdout.write(
            self.style.WARNING(
                '[BILGI] Bilgilendirme:\n'
                '  - Kredi Karti: http://localhost:8002/admin/core/paymentmethod/ adresinde gorulebilir\n'
                '  - Havale IBAN: 5698542147852332\n'
                '  - Test icin admin paneline giderek odemeleri yonetebilirsiniz.\n'
            )
        )

