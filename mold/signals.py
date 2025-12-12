"""
EarMold model signals - Otomatik fatura oluşturma
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def create_invoice_on_mold_completion(sender, instance, created, **kwargs):
    """
    Kalıp tamamlandığında veya teslim edildiğinde otomatik fatura oluştur
    
    Fatura oluşturma koşulları:
    1. Kalıp durumu 'completed' veya 'delivered' olmalı
    2. Bu dönem için bu merkeze henüz fatura kesilmemiş olmalı
    3. Fiziksel kalıp gönderimi veya dijital modelleme hizmeti olmalı
    """
    from mold.models import EarMold
    from core.models import Invoice, PricingConfiguration
    
    # Sadece güncelleme durumunda çalış (yeni oluşturulmada değil)
    if created:
        return
    
    # Sadece completed veya delivered durumunda fatura oluştur
    if instance.status not in ['completed', 'delivered']:
        return
    
    # Fiziksel kalıp gönderimi veya dijital modelleme hizmeti değilse fatura kesme
    if not instance.is_physical_shipment and not instance.modeled_files.exists():
        return
    
    try:
        # Aktif fiyatlandırmayı al
        pricing = PricingConfiguration.get_active()
        if not pricing:
            logger.warning(f"Fiyatlandırma yapılandırması bulunamadı. Merkez: {instance.center.name}")
            return
        
        # Bu ay için tarih aralığını belirle
        now = timezone.now()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        
        # Bu dönemde bu merkez için zaten fatura kesilmiş mi kontrol et
        existing_invoice = Invoice.objects.filter(
            issued_by_center=instance.center,
            invoice_type='center_admin_invoice',
            issue_date__gte=start_date.date(),
            issue_date__lte=end_date.date()
        ).exclude(invoice_number__startswith='PKG-').order_by('-issue_date').first()
        
        # Eğer bu dönem için fatura varsa, fatura tarihinden SONRA oluşturulan hizmetler var mı kontrol et
        if existing_invoice:
            # Fatura tarihinden sonra oluşturulan kalıpları kontrol et
            invoice_date = existing_invoice.issue_date
            
            # Fatura tarihinden sonra eklenen hizmetler
            later_physical = EarMold.objects.filter(
                center=instance.center,
                is_physical_shipment=True,
                created_at__date__gt=invoice_date,
                created_at__lte=end_date,
                status__in=['completed', 'delivered', 'shipped_to_center']
            )
            
            later_digital = EarMold.objects.filter(
                center=instance.center,
                created_at__date__gt=invoice_date,
                created_at__lte=end_date,
                status__in=['completed', 'delivered']
            ).filter(
                Q(is_physical_shipment=False) | Q(modeled_files__isnull=False)
            ).distinct()
            
            # Eğer fatura tarihinden sonra yeni hizmet yoksa, fatura oluşturma
            if later_physical.count() == 0 and later_digital.count() == 0:
                return
            # Eğer varsa, sadece yeni hizmetler için fatura oluştur
            # Fatura tarihinden SONRA oluşturulan hizmetleri al
            invoice_date = existing_invoice.issue_date
            # Fatura tarihinden bir gün sonrasından başla
            invoice_date_next = invoice_date + timedelta(days=1)
            start_date_for_molds = timezone.make_aware(
                datetime.combine(invoice_date_next, datetime.min.time())
            ) if isinstance(invoice_date, datetime.date) else invoice_date + timedelta(days=1)
        else:
            # Fatura yoksa, bu ayın başından itibaren tüm hizmetleri al
            start_date_for_molds = start_date
        
        # Faturalandırılmamış hizmetleri al (fatura tarihinden sonra veya bu ayın başından)
        from django.db.models import Q
        physical_molds = EarMold.objects.filter(
            center=instance.center,
            is_physical_shipment=True,
            created_at__gte=start_date_for_molds,
            created_at__lte=end_date,
            status__in=['completed', 'delivered', 'shipped_to_center']
        )
        
        digital_molds = EarMold.objects.filter(
            center=instance.center,
            created_at__gte=start_date_for_molds,
            created_at__lte=end_date,
            status__in=['completed', 'delivered']
        ).filter(
            Q(is_physical_shipment=False) | Q(modeled_files__isnull=False)
        ).distinct()
        
        physical_count = physical_molds.count()
        digital_count = digital_molds.count()
        
        # Eğer bu dönemde hizmet yoksa fatura kesme
        if physical_count == 0 and digital_count == 0:
            return
        
        # Merkez aboneliğini al
        from core.models import UserSubscription
        subscription = UserSubscription.objects.filter(
            user=instance.center.user, 
            status='active'
        ).first()
        
        # Bu ay için zaten aylık fatura (center veya center_monthly) oluşturulmuş mu kontrol et
        # Eğer oluşturulmuşsa, aylık ücreti tekrar ekleme
        monthly_invoice_exists = Invoice.objects.filter(
            user=instance.center.user,
            invoice_type__in=['center', 'center_monthly'],
            issue_date__year=now.year,
            issue_date__month=now.month
        ).exists()
        
        # Aylık ücret - sadece aylık fatura yoksa ekle
        if monthly_invoice_exists:
            # Bu ay için zaten aylık fatura oluşturulmuş, aylık ücreti ekleme
            monthly_fee = Decimal('0.00')
        else:
            # Aylık fatura yoksa, aylık ücreti ekle
            if subscription and subscription.plan and subscription.plan.plan_type in ['package', 'standard']:
                monthly_fee = subscription.plan.monthly_fee_try
            else:
                monthly_fee = pricing.monthly_system_fee
        
        # Fiziksel ve dijital tutarları hesapla
        from core.views_financial import get_mold_price_at_date
        physical_amount = Decimal('0.00')
        for mold in physical_molds:
            if mold.unit_price is not None:
                physical_amount += mold.unit_price
            else:
                mold_price = get_mold_price_at_date(mold, instance.center.user, pricing)
                physical_amount += mold_price
        
        digital_amount = Decimal('0.00')
        for mold in digital_molds:
            if mold.digital_modeling_price is not None:
                digital_amount += mold.digital_modeling_price
            else:
                mold_price = get_mold_price_at_date(mold, instance.center.user, pricing)
                digital_amount += mold_price
        
        # Toplam tutar
        gross_amount = physical_amount + digital_amount + monthly_fee
        
        # KDV hesaplaması
        vat_multiplier = Decimal('1') + (pricing.vat_rate / Decimal('100'))
        gross_without_vat = gross_amount / vat_multiplier
        vat_amount = gross_amount - gross_without_vat
        
        # MoldPark komisyonu (aylık ücret hariç) - KDV hariç tutar üzerinden hesaplanır
        amount_after_monthly_fee = physical_amount + digital_amount
        # KDV hariç tutar üzerinden komisyon hesapla
        amount_after_monthly_fee_without_vat = amount_after_monthly_fee / vat_multiplier
        moldpark_fee = pricing.calculate_moldpark_fee(amount_after_monthly_fee_without_vat)
        
        # Üreticiye giden tutar
        net_to_producer = amount_after_monthly_fee - moldpark_fee
        
        # Fatura oluştur
        invoice = Invoice.objects.create(
            invoice_number=Invoice.generate_invoice_number('center_admin'),
            invoice_type='center_admin_invoice',
            user=instance.center.user,
            issued_by_center=instance.center,
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
        from datetime import time as dt_time
        if hasattr(start_date_for_molds, 'date'):
            period_start = start_date_for_molds.date()
        elif isinstance(start_date_for_molds, datetime):
            period_start = start_date_for_molds.date()
        else:
            period_start = start_date_for_molds if isinstance(start_date_for_molds, datetime.date) else start_date.date()
        
        breakdown_data = {
            'period': {
                'start': period_start.isoformat() if hasattr(period_start, 'isoformat') else str(period_start),
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
            'auto_created': True,  # Otomatik oluşturulduğunu belirt
            'created_by_mold_id': instance.id,  # Hangi kalıp nedeniyle oluşturulduğunu kaydet
        }
        
        invoice.breakdown_data = breakdown_data
        invoice.save()
        
        # Faturayı gönderildi olarak işaretle (admin onayı gerekmez)
        invoice.mark_as_sent(instance.center.user)
        
        logger.info(f"Otomatik fatura oluşturuldu: {invoice.invoice_number} - Merkez: {instance.center.name}")
        
        # İşitme merkezine bildirim gönder
        from core.models import SimpleNotification
        SimpleNotification.objects.create(
            user=instance.center.user,
            title='💰 Yeni Fatura Oluşturuldu',
            message=f'{invoice.invoice_number} numaralı fatura otomatik olarak oluşturuldu. Fiziksel: {physical_count}, Dijital: {digital_count}, Toplam: ₺{gross_amount:.2f}',
            notification_type='info',
            related_url=f'/financial/invoices/{invoice.id}/'
        )
        
    except Exception as e:
        logger.error(f"Otomatik fatura oluşturma hatası: {e}", exc_info=True)

