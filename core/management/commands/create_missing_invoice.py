"""
Eksik fatura oluşturma komutu
Faturalandırılmamış hizmet alımları için otomatik fatura oluşturur
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta, date as dt_date, time as dt_time
from decimal import Decimal
from center.models import Center
from mold.models import EarMold
from core.models import Invoice, PricingConfiguration, UserSubscription, SimpleNotification
from django.db.models import Q
from core.views_financial import get_mold_price_at_date


class Command(BaseCommand):
    help = 'Faturalandırılmamış hizmet alımları için otomatik fatura oluşturur'

    def add_arguments(self, parser):
        parser.add_argument(
            '--center',
            type=str,
            help='Belirli bir merkez için fatura oluştur (merkez adı)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Tüm merkezler için eksik faturaları oluştur',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Sadece önizleme yap, fatura oluşturma',
        )

    def handle(self, *args, **options):
        center_name = options.get('center')
        all_centers = options.get('all', False)
        dry_run = options.get('dry_run', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODU - Fatura oluşturulmayacak\n'))

        # Aktif fiyatlandırmayı al
        pricing = PricingConfiguration.get_active()
        if not pricing:
            self.stdout.write(self.style.ERROR('Aktif fiyatlandırma yapılandırması bulunamadı!'))
            return

        # Merkezleri belirle
        if center_name:
            centers = Center.objects.filter(name__icontains=center_name, is_active=True)
            if not centers.exists():
                self.stdout.write(self.style.ERROR(f'"{center_name}" adında merkez bulunamadı!'))
                return
        elif all_centers:
            centers = Center.objects.filter(is_active=True)
        else:
            self.stdout.write(self.style.ERROR('--center VEYA --all parametresi gerekli!'))
            return

        # Bu ay için tarih aralığını belirle
        now = timezone.now()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now

        created_count = 0
        total_amount = Decimal('0.00')

        for center in centers:
            self.stdout.write(f'\n{center.name} merkezi kontrol ediliyor...')

            # Bu dönemde zaten fatura kesilmiş mi kontrol et
            existing_invoice = Invoice.objects.filter(
                issued_by_center=center,
                invoice_type='center_admin_invoice',
                issue_date__gte=start_date.date(),
                issue_date__lte=end_date.date()
            ).exclude(invoice_number__startswith='PKG-').first()

            if existing_invoice:
                # Fatura var, ama fatura tarihinden sonra eklenen hizmetler olabilir
                invoice_date = existing_invoice.issue_date
                
                # Fatura tarihinden sonra eklenen hizmetler
                later_physical = EarMold.objects.filter(
                    center=center,
                    is_physical_shipment=True,
                    created_at__date__gt=invoice_date,
                    created_at__lte=end_date,
                    status__in=['completed', 'delivered', 'shipped_to_center']
                )
                
                later_digital = EarMold.objects.filter(
                    center=center,
                    created_at__date__gt=invoice_date,
                    created_at__lte=end_date,
                    status__in=['completed', 'delivered']
                ).filter(
                    Q(is_physical_shipment=False) | Q(modeled_files__isnull=False)
                ).distinct()
                
                if later_physical.count() == 0 and later_digital.count() == 0:
                    self.stdout.write(f'  >> Bu donem icin zaten fatura var ve yeni hizmet yok: {existing_invoice.invoice_number}')
                    continue
                
                # Fatura tarihinden sonra hizmet var, yeni fatura oluştur
                self.stdout.write(f'  >> Bu donem icin fatura var ama fatura tarihinden sonra yeni hizmetler var')
                self.stdout.write(f'  >> Mevcut fatura: {existing_invoice.invoice_number} ({existing_invoice.issue_date})')
                # Fatura tarihinden sonraki hizmetler için fatura oluştur
                if isinstance(invoice_date, dt_date):
                    invoice_date_next = invoice_date + timedelta(days=1)
                    start_date = timezone.make_aware(datetime.combine(invoice_date_next, dt_time.min))
                else:
                    start_date = invoice_date + timedelta(days=1)

            # Bu dönemde bu merkezden gönderilen fiziksel kalıplar
            physical_molds = EarMold.objects.filter(
                center=center,
                is_physical_shipment=True,
                created_at__gte=start_date,
                created_at__lte=end_date,
                status__in=['completed', 'delivered', 'shipped_to_center']
            )

            # Bu dönemde bu merkezden yapılan dijital modellemeler
            digital_molds = EarMold.objects.filter(
                center=center,
                created_at__gte=start_date,
                created_at__lte=end_date,
                status__in=['completed', 'delivered']
            ).filter(
                Q(is_physical_shipment=False) | Q(modeled_files__isnull=False)
            ).distinct()

            physical_count = physical_molds.count()
            digital_count = digital_molds.count()

            if physical_count == 0 and digital_count == 0:
                self.stdout.write(f'  >> Bu donemde hizmet alimi yok')
                continue

            # Merkez aboneliğini al
            subscription = UserSubscription.objects.filter(
                user=center.user,
                status='active'
            ).first()

            # Aylık ücret
            if subscription and subscription.plan and subscription.plan.plan_type in ['package', 'standard']:
                monthly_fee = subscription.plan.monthly_fee_try
            else:
                monthly_fee = pricing.monthly_system_fee

            # Fiziksel ve dijital tutarları hesapla
            physical_amount = Decimal('0.00')
            for mold in physical_molds:
                if mold.unit_price is not None:
                    physical_amount += mold.unit_price
                else:
                    mold_price = get_mold_price_at_date(mold, center.user, pricing)
                    physical_amount += mold_price

            digital_amount = Decimal('0.00')
            for mold in digital_molds:
                if mold.digital_modeling_price is not None:
                    digital_amount += mold.digital_modeling_price
                else:
                    mold_price = get_mold_price_at_date(mold, center.user, pricing)
                    digital_amount += mold_price

            # Toplam tutar
            gross_amount = physical_amount + digital_amount + monthly_fee

            # KDV hesaplaması
            vat_multiplier = Decimal('1') + (pricing.vat_rate / Decimal('100'))
            gross_without_vat = gross_amount / vat_multiplier
            vat_amount = gross_amount - gross_without_vat

            # MoldPark komisyonu (aylık ücret hariç)
            amount_after_monthly_fee = physical_amount + digital_amount
            amount_after_monthly_fee_without_vat = amount_after_monthly_fee / vat_multiplier
            moldpark_fee = pricing.calculate_moldpark_fee(amount_after_monthly_fee_without_vat)

            # Üreticiye giden tutar
            net_to_producer = amount_after_monthly_fee - moldpark_fee

            self.stdout.write(f'  - Fiziksel: {physical_count} adet - {physical_amount:.2f} TL')
            self.stdout.write(f'  - Dijital: {digital_count} adet - {digital_amount:.2f} TL')
            self.stdout.write(f'  - Aylik Ucret: {monthly_fee:.2f} TL')
            self.stdout.write(f'  - Toplam: {gross_amount:.2f} TL')

            if dry_run:
                self.stdout.write(f'  [DRY RUN] Fatura olusturulacak ama kaydedilmeyecek')
                created_count += 1
                total_amount += gross_amount
                continue

            # Fatura oluştur
            try:
                invoice = Invoice.objects.create(
                    invoice_number=Invoice.generate_invoice_number('center_admin'),
                    invoice_type='center_admin_invoice',
                    user=center.user,
                    issued_by_center=center,
                    issue_date=timezone.now().date(),
                    due_date=(timezone.now() + timedelta(days=30)).date(),
                    status='issued',
                    # Fiziksel kalıp bilgileri
                    physical_mold_count=physical_count,
                    physical_mold_cost=physical_amount,
                    # Dijital modelleme bilgileri
                    digital_scan_count=digital_count,
                    digital_scan_cost=digital_amount,
                    # Aylık ücret
                    monthly_fee=monthly_fee,
                    # Tutarlar
                    subtotal=amount_after_monthly_fee,
                    subtotal_without_vat=gross_without_vat - (monthly_fee / vat_multiplier),
                    total_amount=gross_amount,
                    total_with_vat=gross_amount,
                    vat_rate=pricing.vat_rate,
                    vat_amount=vat_amount,
                    # Komisyonlar
                    moldpark_service_fee=moldpark_fee,
                    moldpark_service_fee_rate=pricing.moldpark_commission_rate,
                    credit_card_fee_rate=pricing.credit_card_commission_rate,
                    net_amount=net_to_producer,
                )

                # Breakdown data oluştur
                breakdown_data = {
                    'period': {
                        'start': start_date.date().isoformat(),
                        'end': end_date.date().isoformat(),
                    },
                    'services': {
                        'physical_molds': {
                            'count': physical_count,
                            'amount': str(physical_amount),
                            'unit_price': str(physical_amount / physical_count) if physical_count > 0 else '0.00',
                        },
                        'digital_modeling': {
                            'count': digital_count,
                            'amount': str(digital_amount),
                            'unit_price': str(digital_amount / digital_count) if digital_count > 0 else '0.00',
                        },
                        'monthly_system_fee': str(monthly_fee),
                    },
                    'summary': {
                        'gross_amount': str(gross_amount),
                        'vat_amount': str(vat_amount),
                        'gross_without_vat': str(gross_without_vat),
                        'moldpark_fee': str(moldpark_fee),
                        'producer_receives': str(net_to_producer),
                    },
                    'auto_created': True,
                    'created_by_command': True,
                }

                invoice.breakdown_data = breakdown_data
                invoice.save()

                # Faturayı gönderildi olarak işaretle
                # mark_as_sent içinde transaction oluşturulurken user.molds hatası olabilir
                # Bu yüzden direkt status güncelleyelim
                invoice.status = 'sent'
                invoice.sent_date = timezone.now()
                invoice.issued_by = center.user
                invoice.save()
                
                # Transaction'ı manuel oluştur
                from core.models import Transaction
                Transaction.objects.create(
                    user=center.user,
                    center=center,
                    invoice=invoice,
                    transaction_type='center_invoice_payment',
                    amount=invoice.total_amount,
                    description=f'Kalıp gönderimi faturası: {invoice.invoice_number}',
                    reference_id=invoice.invoice_number,
                    service_provider=center.name,
                    service_type='Fiziksel Kalıp Üretimi',
                    amount_source=f'Merkez: {center.name}',
                    amount_destination=f'MoldPark (Tahsilat)',
                    moldpark_fee_amount=invoice.moldpark_service_fee,
                    status='pending'
                )

                # İşitme merkezine bildirim gönder
                SimpleNotification.objects.create(
                    user=center.user,
                    title='💰 Yeni Fatura Oluşturuldu',
                    message=f'{invoice.invoice_number} numaralı fatura otomatik olarak oluşturuldu. Fiziksel: {physical_count}, Dijital: {digital_count}, Toplam: ₺{gross_amount:.2f}',
                    notification_type='info',
                    related_url=f'/financial/invoices/{invoice.id}/'
                )

                self.stdout.write(self.style.SUCCESS(
                    f'  [OK] Fatura olusturuldu: {invoice.invoice_number} - {gross_amount:.2f} TL'
                ))

                created_count += 1
                total_amount += gross_amount

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [HATA] {str(e)}'))
                import traceback
                traceback.print_exc()

        self.stdout.write('\n' + '=' * 60)
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f'[OK] {created_count} fatura olusturuldu - Toplam: {total_amount:.2f} TL'
            ))
        else:
            self.stdout.write(self.style.WARNING('Olusturulacak fatura bulunamadi'))

