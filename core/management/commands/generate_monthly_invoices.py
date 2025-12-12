"""
Aylık faturaları otomatik oluşturur
Her ayın başında çalıştırılmalıdır
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta
from decimal import Decimal

from core.models import Invoice, UserSubscription, FinancialSummary, PricingPlan
from center.models import Center
from producer.models import Producer, ProducerOrder
from mold.models import EarMold


class Command(BaseCommand):
    help = 'Aylık faturaları otomatik oluşturur'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=int,
            help='Fatura oluşturulacak ay (1-12)',
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Fatura oluşturulacak yıl',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Gerçek fatura oluşturmadan önizleme yapar',
        )

    def handle(self, *args, **options):
        # Tarih belirleme
        now = timezone.now()
        
        if options['month'] and options['year']:
            target_month = options['month']
            target_year = options['year']
        else:
            # Geçen ay
            last_month = now.replace(day=1) - timedelta(days=1)
            target_month = last_month.month
            target_year = last_month.year
        
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS(
            f'\n=== Aylık Fatura Oluşturma Başlatıldı ==='
        ))
        self.stdout.write(f'Dönem: {target_year}/{target_month:02d}')
        self.stdout.write(f'Mod: {"Önizleme (Dry Run)" if dry_run else "Gerçek Fatura Oluşturma"}\n')
        
        # Ay başı ve 28'i (fatura kesim tarihi)
        from datetime import date
        month_start = date(target_year, target_month, 1)
        # Fatura ayın 28'inde kesiliyor
        issue_date = date(target_year, target_month, 28)
        # Eğer ayda 28 gün yoksa (şubat gibi), ayın son günü
        try:
            if target_month == 12:
                next_month = date(target_year + 1, 1, 1)
            else:
                next_month = date(target_year, target_month + 1, 1)
            month_end = next_month - timedelta(days=1)
            if month_end.day < 28:
                issue_date = month_end
        except ValueError:
            # Şubat ayının son günü
            if target_month == 2:
                if (target_year % 4 == 0 and target_year % 100 != 0) or (target_year % 400 == 0):
                    issue_date = date(target_year, 2, 29)
                else:
                    issue_date = date(target_year, 2, 28)
        
        # İşitme Merkezleri için faturalar
        self.stdout.write('\n1. İşitme Merkezleri Faturaları Oluşturuluyor...')
        center_count = 0
        center_total = Decimal('0')
        
        for center in Center.objects.filter(is_active=True):
            user = center.user
            
            # Abonelik kontrolü
            try:
                subscription = UserSubscription.objects.get(user=user, status='active')
            except UserSubscription.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'   ⚠ {user.username} - Aktif abonelik yok, atlanıyor'
                ))
                continue
            
            # Bu ay oluşturulmuş fatura var mı kontrol et
            existing_invoice = Invoice.objects.filter(
                user=user,
                invoice_type='center',
                issue_date__year=target_year,
                issue_date__month=target_month
            ).first()
            
            if existing_invoice and not dry_run:
                self.stdout.write(self.style.WARNING(
                    f'   ⚠ {user.username} - Bu ay için fatura zaten mevcut'
                ))
                continue
            
            # Bu ay için center_admin_invoice tipinde fatura var mı ve aylık ücret içeriyor mu kontrol et
            # Eğer varsa, aylık ücreti tekrar ekleme
            admin_invoice_with_monthly_fee = Invoice.objects.filter(
                user=user,
                invoice_type='center_admin_invoice',
                issue_date__year=target_year,
                issue_date__month=target_month,
                monthly_fee__gt=0
            ).exists()
            
            # Aylık kullanım verilerini al
            molds = EarMold.objects.filter(
                center=center,
                created_at__gte=month_start,
                created_at__lte=month_end
            )
            
            # Fiziksel ve digital sayıları hesapla (şimdilik tümü fiziksel olarak say)
            physical_count = molds.count()
            digital_count = 0  # İleride ek bir alan ile belirlenebilir
            
            if physical_count == 0 and digital_count == 0:
                self.stdout.write(f'   - {user.username} - Bu ay kullanım yok, sadece aylık ücret')
            
            # Fatura oluştur
            if not dry_run:
                invoice = Invoice.objects.create(
                    invoice_type='center',
                    user=user,
                    issue_date=issue_date,
                    due_date=issue_date + timedelta(days=15),
                    status='issued'
                )
                
                # Hesaplama - eğer bu ay için center_admin_invoice'da aylık ücret alınmışsa, tekrar ekleme
                total = invoice.calculate_center_invoice(
                    subscription=subscription,
                    period_start=month_start,
                    period_end=month_end,
                    include_monthly_fee=not admin_invoice_with_monthly_fee
                )
                
                center_count += 1
                center_total += total
                
                self.stdout.write(self.style.SUCCESS(
                    f'   ✓ {user.username} - Fatura: {invoice.invoice_number} - '
                    f'Fiziksel: {physical_count}, Digital: {digital_count} - '
                    f'Toplam: {total} TL'
                ))
            else:
                # Dry run - sadece hesapla
                plan = subscription.plan
                # Eğer bu ay için center_admin_invoice'da aylık ücret alınmışsa, tekrar ekleme
                if admin_invoice_with_monthly_fee:
                    monthly_fee = Decimal('0.00')
                else:
                    monthly_fee = plan.monthly_fee_try
                physical_cost = plan.per_mold_price_try * physical_count
                digital_cost = plan.modeling_service_fee_try * digital_count
                subtotal = monthly_fee + physical_cost + digital_cost
                credit_fee = subtotal * Decimal('0.03')
                total = subtotal + credit_fee
                
                center_count += 1
                center_total += total
                
                self.stdout.write(
                    f'   [Onizleme] {user.username} - '
                    f'Fiziksel: {physical_count}, Digital: {digital_count} - '
                    f'Toplam: {total} TL'
                )
        
        self.stdout.write(self.style.SUCCESS(
            f'\n   Isitme Merkezi Fatura Sayisi: {center_count}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'   Isitme Merkezi Toplam: {center_total} TL'
        ))
        
        # Üretici Merkezler için faturalar
        self.stdout.write('\n2. Üretici Merkezleri Faturaları Oluşturuluyor...')
        producer_count = 0
        producer_total = Decimal('0')
        moldpark_commission_total = Decimal('0')
        
        for producer in Producer.objects.filter(is_active=True):
            user = producer.user
            
            # Bu ay tamamlanmış siparişleri al
            orders = ProducerOrder.objects.filter(
                producer=producer,
                status='completed',
                actual_delivery__gte=month_start,
                actual_delivery__lte=month_end
            )
            
            order_count = orders.count()
            if order_count == 0:
                self.stdout.write(f'   - {user.username} - Bu ay sipariş yok')
                continue
            
            # Bu ay için fatura var mı kontrol et
            existing_invoice = Invoice.objects.filter(
                user=user,
                invoice_type='producer',
                issue_date__year=target_year,
                issue_date__month=target_month
            ).first()
            
            if existing_invoice and not dry_run:
                self.stdout.write(self.style.WARNING(
                    f'   ⚠ {user.username} - Bu ay için fatura zaten mevcut'
                ))
                continue
            
            # Brüt gelir hesapla (siparişlerdeki toplam tutar)
            gross_revenue = sum(order.price for order in orders if order.price)
            
            if not dry_run:
                invoice = Invoice.objects.create(
                    invoice_type='producer',
                    user=user,
                    issue_date=issue_date,
                    due_date=issue_date + timedelta(days=15),
                    status='issued'
                )
                
                # Hesaplama
                total = invoice.calculate_producer_invoice(
                    order_count=order_count,
                    gross_revenue=gross_revenue
                )
                
                producer_count += 1
                producer_total += total
                moldpark_commission_total += invoice.moldpark_commission
                
                self.stdout.write(self.style.SUCCESS(
                    f'   ✓ {user.username} - Fatura: {invoice.invoice_number} - '
                    f'Siparis: {order_count}, Brut: {gross_revenue} TL - '
                    f'Komisyon: {invoice.moldpark_commission} TL - '
                    f'Net: {invoice.net_amount} TL'
                ))
            else:
                # Dry run
                moldpark_commission = gross_revenue * Decimal('0.075')
                credit_fee = gross_revenue * Decimal('0.03')
                net_to_producer = gross_revenue - moldpark_commission - credit_fee
                
                producer_count += 1
                producer_total += gross_revenue
                moldpark_commission_total += moldpark_commission
                
                self.stdout.write(
                    f'   [Onizleme] {user.username} - '
                    f'Siparis: {order_count}, Brut: {gross_revenue} TL - '
                    f'Komisyon: {moldpark_commission} TL - '
                    f'Net: {net_to_producer} TL'
                )
        
        self.stdout.write(self.style.SUCCESS(
            f'\n   Uretici Fatura Sayisi: {producer_count}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'   Uretici Brut Gelir: {producer_total} TL'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'   MoldPark Komisyon: {moldpark_commission_total} TL'
        ))
        
        # Aylık özet oluştur
        if not dry_run:
            self.stdout.write('\n3. Aylık Mali Özet Oluşturuluyor...')
            summary = FinancialSummary.calculate_monthly_summary(target_year, target_month)
            self.stdout.write(self.style.SUCCESS(
                f'   ✓ {target_year}/{target_month:02d} mali ozeti olusturuldu'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   Toplam Brut Gelir: {summary.total_gross_revenue} TL'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   Toplam Net Gelir: {summary.total_net_revenue} TL'
            ))
        
        # Özet
        self.stdout.write(self.style.SUCCESS(
            f'\n=== Fatura Olusturma Tamamlandi ==='
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Toplam Fatura: {center_count + producer_count}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Isitme Merkezi: {center_count} fatura - {center_total} TL'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Uretici: {producer_count} fatura - {producer_total} TL'
        ))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\n[!] Bu bir onizlemeydi. Gercek fatura olusturmak icin --dry-run olmadan calistirin.'
            ))

