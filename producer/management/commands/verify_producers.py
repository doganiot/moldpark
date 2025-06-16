from django.core.management.base import BaseCommand
from django.utils import timezone
from producer.models import Producer


class Command(BaseCommand):
    help = 'Mevcut üreticileri doğrular'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Tüm üreticileri doğrula',
        )
        parser.add_argument(
            '--company',
            type=str,
            help='Belirli bir firma adına göre doğrula',
        )

    def handle(self, *args, **options):
        if options['all']:
            # Tüm üreticileri doğrula
            producers = Producer.objects.filter(is_verified=False)
            count = 0
            for producer in producers:
                producer.is_verified = True
                producer.verification_date = timezone.now()
                producer.save()
                count += 1
                self.stdout.write(f'✓ {producer.company_name} doğrulandı')
            
            self.stdout.write(
                self.style.SUCCESS(f'Toplam {count} üretici doğrulandı.')
            )
        
        elif options['company']:
            # Belirli firma adına göre doğrula
            try:
                producer = Producer.objects.get(company_name__icontains=options['company'])
                if not producer.is_verified:
                    producer.is_verified = True
                    producer.verification_date = timezone.now()
                    producer.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ {producer.company_name} doğrulandı')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠ {producer.company_name} zaten doğrulanmış')
                    )
            except Producer.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'✗ "{options["company"]}" bulunamadı')
                )
            except Producer.MultipleObjectsReturned:
                producers = Producer.objects.filter(company_name__icontains=options['company'])
                self.stdout.write(f'Birden fazla üretici bulundu:')
                for producer in producers:
                    status = "Doğrulanmış" if producer.is_verified else "Beklemede"
                    self.stdout.write(f'  - {producer.company_name} ({status})')
        
        else:
            # Mevcut durum raporu
            total = Producer.objects.count()
            verified = Producer.objects.filter(is_verified=True).count()
            unverified = Producer.objects.filter(is_verified=False).count()
            active = Producer.objects.filter(is_active=True).count()
            
            self.stdout.write('\n📊 Üretici Durumu:')
            self.stdout.write(f'   Toplam: {total}')
            self.stdout.write(f'   Doğrulanmış: {verified}')
            self.stdout.write(f'   Beklemede: {unverified}')
            self.stdout.write(f'   Aktif: {active}')
            
            if unverified > 0:
                self.stdout.write('\n⏳ Doğrulanmamış üreticiler:')
                for producer in Producer.objects.filter(is_verified=False):
                    self.stdout.write(f'   - {producer.company_name} ({producer.user.email})')
                
                self.stdout.write('\n💡 Tüm üreticileri doğrulamak için: --all parametresini kullanın')
                self.stdout.write('💡 Belirli üreticiyi doğrulamak için: --company "Firma Adı" kullanın') 