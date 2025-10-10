"""
Finansal Yönetim Views
Admin paneli için finansal dashboard ve fatura yönetimi
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from datetime import datetime, timedelta
from decimal import Decimal

from .models import Invoice, FinancialSummary, UserSubscription, PricingPlan
from center.models import Center
from producer.models import Producer, ProducerOrder
from mold.models import EarMold


@user_passes_test(lambda u: u.is_superuser)
def financial_dashboard(request):
    """Ana finansal dashboard - Tüm mali durumu gösterir"""
    
    # Zaman aralığı filtresi
    period = request.GET.get('period', 'this_month')
    now = timezone.now()
    
    if period == 'this_month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        period_name = 'Bu Ay'
    elif period == 'last_month':
        last_month = now.replace(day=1) - timedelta(days=1)
        start_date = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = last_month.replace(day=28, hour=23, minute=59, second=59)
        period_name = 'Geçen Ay'
    elif period == 'this_year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        period_name = 'Bu Yıl'
    else:  # all_time
        start_date = datetime(2020, 1, 1)
        end_date = now
        period_name = 'Tüm Zamanlar'
    
    # Faturalar (Yeni ve Eski Sistem Uyumlu)
    invoices = Invoice.objects.filter(
        issue_date__gte=start_date.date(),
        issue_date__lte=end_date.date(),
        status__in=['issued', 'paid']
    )
    
    # Eski sistem faturaları
    old_center_invoices = invoices.filter(invoice_type='center')
    old_producer_invoices = invoices.filter(invoice_type='producer')
    
    # Yeni sistem faturaları
    new_center_invoices = invoices.filter(invoice_type='center_admin_invoice')
    new_producer_invoices = invoices.filter(invoice_type='producer_invoice')
    
    # === ESKİ SİSTEM GELİRLERİ ===
    old_center_stats = {
        'count': old_center_invoices.count(),
        'monthly_fees': sum(inv.monthly_fee for inv in old_center_invoices),
        'physical_revenue': sum((inv.physical_mold_cost or 0) + (inv.mold_cost or 0) for inv in old_center_invoices),
        'digital_revenue': sum((inv.digital_scan_cost or 0) + (inv.modeling_cost or 0) for inv in old_center_invoices),
        'credit_card_fees': sum(inv.credit_card_fee for inv in old_center_invoices),
    }
    old_center_stats['total_revenue'] = old_center_stats['monthly_fees'] + old_center_stats['physical_revenue'] + old_center_stats['digital_revenue']
    
    old_producer_stats = {
        'count': old_producer_invoices.count(),
        'gross_revenue': sum(getattr(inv, 'producer_revenue', 0) for inv in old_producer_invoices),
        'moldpark_commission': sum(getattr(inv, 'moldpark_commission', 0) for inv in old_producer_invoices),
        'credit_card_fees': sum(inv.credit_card_fee for inv in old_producer_invoices),
    }
    
    # === YENİ SİSTEM GELİRLERİ ===
    # İşitme merkezlerinden tahsilat (fiziksel kalıp ödemeleri)
    new_center_revenue = Decimal('0.00')
    new_center_moldpark_fee = Decimal('0.00')
    new_center_cc_fee = Decimal('0.00')
    
    for invoice in new_center_invoices:
        new_center_revenue += invoice.total_amount or Decimal('0.00')
        new_center_moldpark_fee += invoice.moldpark_service_fee or Decimal('0.00')
        new_center_cc_fee += invoice.credit_card_fee or Decimal('0.00')
    
    # Üretici ödemelerinden MoldPark'ın payı
    new_producer_moldpark_fee = Decimal('0.00')
    new_producer_cc_fee = Decimal('0.00')
    new_producer_gross = Decimal('0.00')
    
    for invoice in new_producer_invoices:
        new_producer_gross += invoice.producer_gross_revenue or Decimal('0.00')
        new_producer_moldpark_fee += (invoice.producer_gross_revenue or Decimal('0.00')) * Decimal('0.065')
        new_producer_cc_fee += invoice.credit_card_fee or Decimal('0.00')
    
    # === BİRLEŞTİRİLMİŞ İSTATİSTİKLER ===
    center_stats = {
        'count': old_center_invoices.count() + new_center_invoices.count(),
        'total_revenue': old_center_stats['total_revenue'] + new_center_revenue,
        'moldpark_earnings': new_center_moldpark_fee,  # Yeni sistemde merkezlerden hizmet bedeli alınıyor
        'credit_card_fees': old_center_stats['credit_card_fees'] + new_center_cc_fee,
    }
    
    producer_stats = {
        'count': old_producer_invoices.count() + new_producer_invoices.count(),
        'gross_revenue': old_producer_stats['gross_revenue'] + new_producer_gross,
        'moldpark_commission': old_producer_stats['moldpark_commission'] + new_producer_moldpark_fee,
        'credit_card_fees': old_producer_stats['credit_card_fees'] + new_producer_cc_fee,
    }
    producer_stats['net_to_producers'] = producer_stats['gross_revenue'] - producer_stats['moldpark_commission'] - producer_stats['credit_card_fees']
    
    # Toplam Gelir
    total_stats = {
        'gross_revenue': center_stats['total_revenue'] + producer_stats['gross_revenue'],
        'moldpark_earnings': center_stats['moldpark_earnings'] + producer_stats['moldpark_commission'],
        'total_credit_card_fees': center_stats['credit_card_fees'] + producer_stats['credit_card_fees'],
    }
    total_stats['net_profit'] = total_stats['moldpark_earnings'] - total_stats['total_credit_card_fees']
    
    # İstatistikler
    stats = {
        'active_centers': Center.objects.filter(is_active=True).count(),
        'active_producers': Producer.objects.filter(is_active=True).count(),
        'active_subscriptions': UserSubscription.objects.filter(status='active').count(),
        'total_invoices': invoices.count(),
        'paid_invoices': invoices.filter(status='paid').count(),
        'pending_invoices': invoices.filter(status='issued').count(),
        'overdue_invoices': invoices.filter(status='overdue').count(),
    }
    
    # Kalıp İstatistikleri (Eski + Yeni Sistem)
    old_physical = sum((inv.physical_mold_count or 0) + (inv.mold_count or 0) for inv in old_center_invoices)
    old_digital = sum((inv.digital_scan_count or 0) + (inv.modeling_count or 0) for inv in old_center_invoices)
    old_producer_orders = sum(getattr(inv, 'producer_order_count', 0) for inv in old_producer_invoices)
    
    new_physical = sum(inv.physical_mold_count or 0 for inv in new_center_invoices)
    new_digital = sum(inv.modeling_count or 0 for inv in new_producer_invoices)
    
    mold_stats = {
        'total_physical': old_physical + new_physical,
        'total_digital': old_digital + new_digital,
        'total_producer_orders': old_producer_orders + new_producer_invoices.count(),
    }
    
    # Son faturalar
    recent_invoices = Invoice.objects.all().order_by('-created_at')[:10]
    
    # Aylık trendler (son 6 ay)
    monthly_trends = []
    for i in range(5, -1, -1):
        month_date = now - timedelta(days=30*i)
        month_summary = FinancialSummary.objects.filter(
            year=month_date.year,
            month=month_date.month
        ).first()
        
        if month_summary:
            monthly_trends.append({
                'month': f'{month_date.year}/{month_date.month:02d}',
                'revenue': float(month_summary.total_gross_revenue),
                'profit': float(month_summary.total_net_revenue),
            })
        else:
            monthly_trends.append({
                'month': f'{month_date.year}/{month_date.month:02d}',
                'revenue': 0,
                'profit': 0,
            })
    
    # Vadesi geçmiş faturalar
    overdue_invoices_list = Invoice.objects.filter(
        status='issued',
        due_date__lt=timezone.now().date()
    ).order_by('due_date')[:5]
    
    context = {
        'period': period,
        'period_name': period_name,
        'start_date': start_date,
        'end_date': end_date,
        'center_stats': center_stats,
        'producer_stats': producer_stats,
        'total_stats': total_stats,
        'stats': stats,
        'mold_stats': mold_stats,
        'recent_invoices': recent_invoices,
        'monthly_trends': monthly_trends,
        'overdue_invoices': overdue_invoices_list,
    }
    
    return render(request, 'core/financial/dashboard.html', context)


def invoice_list(request):
    """Fatura listesi - Yetkilendirmeli"""

    # Kullanıcının rolüne göre fatura filtresi
    if request.user.is_superuser:
        # Admin tüm faturaları görebilir
        invoices = Invoice.objects.all()
    elif hasattr(request.user, 'center'):
        # Merkez kullanıcıları: kendi faturalarını ve kendi kestiği faturaları görebilir
        invoices = Invoice.objects.filter(
            models.Q(user=request.user) |  # Kendi faturaları
            models.Q(issued_by_center=request.user.center)  # Kestiği faturalar
        )
    elif hasattr(request.user, 'producer'):
        # Üretici kullanıcıları: kendi faturalarını ve kendi kestiği faturaları görebilir
        invoices = Invoice.objects.filter(
            models.Q(user=request.user) |  # Kendi faturaları
            models.Q(issued_by_producer=request.user.producer)  # Kestiği faturalar
        )
    else:
        # Diğer kullanıcılar hiçbir fatura göremez
        invoices = Invoice.objects.none()

    invoice_type = request.GET.get('type', 'all')
    status = request.GET.get('status', 'all')
    
    if invoice_type != 'all':
        invoices = invoices.filter(invoice_type=invoice_type)
    
    if status != 'all':
        invoices = invoices.filter(status=status)
    
    invoices = invoices.order_by('-issue_date', '-created_at')
    
    # İstatistikler
    summary = {
        'total_count': invoices.count(),
        'total_amount': sum(inv.total_amount for inv in invoices),
        'paid_amount': sum(inv.total_amount for inv in invoices.filter(status='paid')),
        'pending_amount': sum(inv.total_amount for inv in invoices.filter(status='issued')),
    }
    
    context = {
        'invoices': invoices,
        'invoice_type': invoice_type,
        'status': status,
        'summary': summary,
    }
    
    return render(request, 'core/financial/invoice_list.html', context)


def invoice_detail(request, invoice_id):
    """Fatura detayı - Yetkilendirmeli"""
    invoice = get_object_or_404(Invoice, id=invoice_id)

    # Yetkilendirme kontrolü
    can_view = False
    if request.user.is_superuser:
        can_view = True
    elif hasattr(request.user, 'center'):
        # Kendi faturası mı veya kendi kestiği fatura mı?
        can_view = (
            invoice.user == request.user or
            invoice.issued_by_center == request.user.center
        )
    elif hasattr(request.user, 'producer'):
        # Kendi faturası mı veya kendi kestiği fatura mı?
        can_view = (
            invoice.user == request.user or
            invoice.issued_by_producer == request.user.producer
        )

    if not can_view:
        from django.http import Http404
        raise Http404("Bu faturayı görüntüleme yetkiniz yok")
    
    context = {
        'invoice': invoice,
    }
    
    return render(request, 'core/financial/invoice_detail.html', context)


def create_center_admin_invoice(request, mold_id):
    """Merkez admin için kalıp gönderimi faturası oluştur"""
    from center.models import Center
    from mold.models import EarMold

    # Sadece merkez kullanıcıları fatura kesebilir
    if not hasattr(request.user, 'center'):
        return JsonResponse({'success': False, 'error': 'Bu işlem için yetkiniz yok'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Geçersiz istek'})

    try:
        ear_mold = get_object_or_404(EarMold, id=mold_id, center=request.user.center)

        # Fatura zaten var mı kontrol et
        existing_invoice = Invoice.objects.filter(
            user=ear_mold.center.user,
            invoice_type='center_admin_invoice',
            breakdown_data__mold_details__mold_id=ear_mold.id
        ).exists()

        if existing_invoice:
            return JsonResponse({'success': False, 'error': 'Bu kalıp için zaten fatura kesilmiş'})

        # Yeni fatura oluştur
        invoice = Invoice.objects.create(
            invoice_number=Invoice.generate_invoice_number('center_admin'),
            invoice_type='center_admin_invoice',
            user=ear_mold.center.user,
            issued_by=request.user,
            issued_by_center=request.user.center,
            due_date=timezone.now().date() + timedelta(days=30)
        )

        # Faturayı hesapla
        total_amount = invoice.calculate_center_admin_invoice(ear_mold, request.user.center)

        # Faturayı kesildi olarak işaretle
        invoice.status = 'issued'
        invoice.save()

        return JsonResponse({
            'success': True,
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'total_amount': float(total_amount)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def create_producer_invoice(request, mold_id):
    """Üretici için hizmet bedeli faturası oluştur"""
    from producer.models import Producer
    from mold.models import EarMold

    # Sadece üretici kullanıcıları fatura kesebilir
    if not hasattr(request.user, 'producer'):
        return JsonResponse({'success': False, 'error': 'Bu işlem için yetkiniz yok'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Geçersiz istek'})

    try:
        ear_mold = get_object_or_404(EarMold, id=mold_id)

        # Bu üreticinin bu kalıp için siparişi var mı kontrol et
        order = ProducerOrder.objects.filter(
            producer=request.user.producer,
            ear_mold=ear_mold,
            status='delivered'
        ).first()

        if not order:
            return JsonResponse({'success': False, 'error': 'Bu kalıp için tamamlanmış siparişiniz bulunmuyor'})

        # Fatura zaten var mı kontrol et
        existing_invoice = Invoice.objects.filter(
            user=request.user,
            invoice_type='producer_invoice',
            breakdown_data__mold_details__mold_id=ear_mold.id
        ).exists()

        if existing_invoice:
            return JsonResponse({'success': False, 'error': 'Bu kalıp için zaten fatura kesilmiş'})

        # Yeni fatura oluştur
        invoice = Invoice.objects.create(
            invoice_number=Invoice.generate_invoice_number('producer'),
            invoice_type='producer_invoice',
            user=request.user,
            issued_by=request.user,
            issued_by_producer=request.user.producer,
            due_date=timezone.now().date() + timedelta(days=15)
        )

        # Faturayı hesapla
        net_amount = invoice.calculate_producer_invoice(ear_mold, request.user.producer)

        # Faturayı kesildi olarak işaretle
        invoice.status = 'issued'
        invoice.save()

        return JsonResponse({
            'success': True,
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'net_amount': float(net_amount)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@user_passes_test(lambda u: u.is_superuser)
def invoice_mark_paid(request, invoice_id):
    """Faturayı ödendi olarak işaretle"""
    if request.method == 'POST':
        invoice = get_object_or_404(Invoice, id=invoice_id)
        invoice.mark_as_paid()
        
        return JsonResponse({'success': True, 'message': 'Fatura ödendi olarak işaretlendi'})
    
    return JsonResponse({'success': False, 'message': 'Geçersiz istek'})


@user_passes_test(lambda u: u.is_superuser)
def generate_monthly_summary(request):
    """Aylık mali özet oluştur"""
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    summary = FinancialSummary.calculate_monthly_summary(year, month)
    
    return JsonResponse({
        'success': True,
        'summary': {
            'year': summary.year,
            'month': summary.month,
            'total_revenue': float(summary.total_gross_revenue),
            'total_profit': float(summary.total_net_revenue),
            'total_invoices': summary.total_invoices,
        }
    })


def moldpark_collections_report(request):
    """MoldPark Tahsilat ve Ödemeler Raporu - Detaylı takip sistemi"""

    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Bu sayfaya erişim yetkiniz yok")

    period = request.GET.get('period', 'this_month')

    # Zaman aralığı belirleme
    now = timezone.now()
    if period == 'this_month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == 'last_month':
        last_month = now.replace(day=1) - timedelta(days=1)
        start_date = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = last_month.replace(day=28, hour=23, minute=59, second=59)
    elif period == 'this_year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    else:  # all_time
        start_date = datetime(2020, 1, 1)
        end_date = now

    # Tüm finansal transaction'ları al
    transactions = Transaction.objects.filter(
        transaction_date__gte=start_date,
        transaction_date__lte=end_date
    ).select_related('user', 'center', 'producer', 'invoice', 'ear_mold').order_by('-transaction_date')

    # Toplam istatistikler
    stats = {
        'total_collections': transactions.filter(transaction_type='moldpark_collection').aggregate(total=Sum('amount'))['total'] or 0,
        'total_payments': transactions.filter(transaction_type='moldpark_payment').aggregate(total=Sum('amount'))['total'] or 0,
        'total_moldpark_fees': transactions.aggregate(total=Sum('moldpark_fee_amount'))['total'] or 0,
        'total_credit_card_fees': transactions.aggregate(total=Sum('credit_card_fee_amount'))['total'] or 0,
        'pending_payments': transactions.filter(transaction_type='moldpark_payment', status='pending').count(),
        'completed_payments': transactions.filter(transaction_type='moldpark_payment', status='completed').count(),
    }

    # Net MoldPark kazancı
    stats['net_moldpark_profit'] = stats['total_collections'] - stats['total_payments'] - stats['total_credit_card_fees']

    # Transaction kırılımları
    transaction_breakdown = {
        'by_type': {},
        'by_service_provider': {},
        'by_amount_source': {},
        'by_status': {},
    }

    for transaction in transactions:
        # Tür kırılımı
        trans_type = transaction.get_transaction_type_display()
        if trans_type not in transaction_breakdown['by_type']:
            transaction_breakdown['by_type'][trans_type] = {'count': 0, 'amount': 0}
        transaction_breakdown['by_type'][trans_type]['count'] += 1
        transaction_breakdown['by_type'][trans_type]['amount'] += float(transaction.amount)

        # Hizmet veren kırılımı
        provider = transaction.service_provider or 'Belirtilmemiş'
        if provider not in transaction_breakdown['by_service_provider']:
            transaction_breakdown['by_service_provider'][provider] = {'count': 0, 'amount': 0}
        transaction_breakdown['by_service_provider'][provider]['count'] += 1
        transaction_breakdown['by_service_provider'][provider]['amount'] += float(transaction.amount)

        # Tutar kaynağı kırılımı
        source = transaction.amount_source or 'Belirtilmemiş'
        if source not in transaction_breakdown['by_amount_source']:
            transaction_breakdown['by_amount_source'][source] = {'count': 0, 'amount': 0}
        transaction_breakdown['by_amount_source'][source]['count'] += 1
        transaction_breakdown['by_amount_source'][source]['amount'] += float(transaction.amount)

        # Durum kırılımı
        status = transaction.get_status_display()
        if status not in transaction_breakdown['by_status']:
            transaction_breakdown['by_status'][status] = {'count': 0, 'amount': 0}
        transaction_breakdown['by_status'][status]['count'] += 1
        transaction_breakdown['by_status'][status]['amount'] += float(transaction.amount)

    context = {
        'transactions': transactions[:100],  # Son 100 işlem
        'stats': stats,
        'transaction_breakdown': transaction_breakdown,
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'total_transactions': transactions.count(),
    }

    return render(request, 'core/financial/moldpark_collections_report.html', context)


@user_passes_test(lambda u: u.is_superuser)
def financial_reports(request):
    """Finansal raporlar"""
    # Son 12 ayın özeti
    summaries = FinancialSummary.objects.all().order_by('-year', '-month')[:12]
    
    # Yıllık özet
    current_year = timezone.now().year
    yearly_summaries = FinancialSummary.objects.filter(year=current_year)
    
    yearly_stats = {
        'total_revenue': sum(s.total_gross_revenue for s in yearly_summaries),
        'total_profit': sum(s.total_net_revenue for s in yearly_summaries),
        'total_centers': yearly_summaries.last().total_centers if yearly_summaries.exists() else 0,
        'total_producers': yearly_summaries.last().total_producers if yearly_summaries.exists() else 0,
        'total_molds': sum(s.total_molds for s in yearly_summaries),
        'total_digital': sum(s.total_modelings for s in yearly_summaries),
    }
    
    context = {
        'summaries': summaries,
        'yearly_stats': yearly_stats,
        'current_year': current_year,
    }
    
    return render(request, 'core/financial/reports.html', context)


@user_passes_test(lambda u: u.is_superuser)
def admin_financial_control_panel(request):
    """
    Merkez Admin Finansal Kontrol Paneli
    Tüm para akışını, tahsilatları, ödemeleri ve komisyonları gösterir
    """
    from django.db.models import Q
    
    # Zaman aralığı filtresi
    period = request.GET.get('period', 'this_month')
    now = timezone.now()
    
    if period == 'this_month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        period_name = 'Bu Ay'
    elif period == 'last_month':
        last_month = now.replace(day=1) - timedelta(days=1)
        start_date = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = last_month.replace(day=28, hour=23, minute=59, second=59)
        period_name = 'Geçen Ay'
    elif period == 'this_year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        period_name = 'Bu Yıl'
    else:  # all_time
        start_date = datetime(2020, 1, 1)
        end_date = now
        period_name = 'Tüm Zamanlar'
    
    # ==========================================
    # 1. İŞİTME MERKEZLERİNDEN TAHSİLATLAR
    # ==========================================
    
    # Fiziksel kalıp gönderen işitme merkezleri
    centers_with_physical_molds = []
    all_centers = Center.objects.filter(is_active=True)
    
    total_collections_from_centers = Decimal('0.00')
    total_moldpark_service_fee = Decimal('0.00')
    total_credit_card_commission = Decimal('0.00')
    
    for center in all_centers:
        # Bu merkezden gönderilen fiziksel kalıplar
        physical_molds = EarMold.objects.filter(
            center=center,
            is_physical_shipment=True,
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        physical_count = physical_molds.count()
        
        if physical_count > 0:
            # Her fiziksel kalıp 450 TL
            gross_amount = physical_count * Decimal('450.00')
            moldpark_fee = gross_amount * Decimal('0.065')  # %6.5
            cc_fee = gross_amount * Decimal('0.03')  # %3
            
            total_collections_from_centers += gross_amount
            total_moldpark_service_fee += moldpark_fee
            total_credit_card_commission += cc_fee
            
            centers_with_physical_molds.append({
                'center': center,
                'physical_count': physical_count,
                'gross_amount': gross_amount,
                'moldpark_fee': moldpark_fee,
                'cc_fee': cc_fee,
                'net_to_producer': gross_amount - moldpark_fee - cc_fee,
            })
    
    # ==========================================
    # 2. ÜRETİCİLERE YAPILACAK ÖDEMELER
    # ==========================================
    
    producers_payment_summary = []
    all_producers = Producer.objects.filter(is_active=True)
    
    total_payments_to_producers = Decimal('0.00')
    
    for producer in all_producers:
        # Bu üreticinin tamamladığı işler
        completed_orders = producer.orders.filter(
            Q(status='delivered') | 
            Q(status__in=['received', 'designing', 'production', 'quality_check', 'packaging', 'shipping'], 
              ear_mold__is_physical_shipment=True),
            created_at__gte=start_date,
            created_at__lte=end_date
        ).select_related('ear_mold')
        
        physical_count = completed_orders.filter(ear_mold__is_physical_shipment=True).count()
        digital_count = completed_orders.filter(ear_mold__is_physical_shipment=False).count()
        
        if completed_orders.exists():
            # Brüt kazanç
            gross_revenue = Decimal('0.00')
            for order in completed_orders:
                if order.ear_mold.is_physical_shipment:
                    gross_revenue += Decimal('450.00')
                else:
                    gross_revenue += Decimal('50.00')
            
            # Kesintiler
            moldpark_cut = gross_revenue * Decimal('0.065')
            cc_cut = gross_revenue * Decimal('0.03')
            net_payment = gross_revenue - moldpark_cut - cc_cut
            
            total_payments_to_producers += net_payment
            
            producers_payment_summary.append({
                'producer': producer,
                'physical_count': physical_count,
                'digital_count': digital_count,
                'total_orders': completed_orders.count(),
                'gross_revenue': gross_revenue,
                'moldpark_cut': moldpark_cut,
                'cc_cut': cc_cut,
                'net_payment': net_payment,
            })
    
    # ==========================================
    # 3. MOLDPARK NET KAZANCI
    # ==========================================
    
    # MoldPark'ın toplam geliri
    moldpark_total_income = total_moldpark_service_fee
    
    # MoldPark'ın kredi kartı komisyonu gideri (üreticilere ödenecek miktardan kesilen)
    moldpark_cc_expense = total_credit_card_commission
    
    # Net kazanç (hizmet bedeli - KK komisyonu)
    moldpark_net_profit = moldpark_total_income - moldpark_cc_expense
    
    # ==========================================
    # 4. PARA AKIŞI ÖZETİ
    # ==========================================
    
    cash_flow = {
        'total_incoming': total_collections_from_centers,  # İşitme merkezlerinden gelen
        'total_outgoing': total_payments_to_producers,  # Üreticilere giden
        'moldpark_service_income': total_moldpark_service_fee,  # MoldPark hizmet bedeli
        'credit_card_fees': total_credit_card_commission,  # Kredi kartı komisyonları
        'moldpark_net_profit': moldpark_net_profit,  # MoldPark net kar
        'balance': total_collections_from_centers - total_payments_to_producers - total_credit_card_commission,  # Kalan bakiye
    }
    
    # ==========================================
    # 5. FATURA DURUMLARI
    # ==========================================
    
    # İşitme merkezlerine kesilen faturalar
    center_invoices = Invoice.objects.filter(
        invoice_type='center_admin_invoice',
        issue_date__gte=start_date.date(),
        issue_date__lte=end_date.date()
    ).select_related('issued_by_center')
    
    center_invoice_stats = {
        'total': center_invoices.count(),
        'paid': center_invoices.filter(status='paid').count(),
        'pending': center_invoices.filter(status__in=['issued', 'sent']).count(),
        'total_amount': center_invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00'),
    }
    
    # Üreticilere kesilen faturalar  
    producer_invoices = Invoice.objects.filter(
        invoice_type='producer_invoice',
        issue_date__gte=start_date.date(),
        issue_date__lte=end_date.date()
    ).select_related('producer')
    
    producer_invoice_stats = {
        'total': producer_invoices.count(),
        'paid': producer_invoices.filter(status='paid').count(),
        'pending': producer_invoices.filter(status__in=['issued', 'sent']).count(),
        'total_amount': producer_invoices.aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00'),
    }
    
    context = {
        'period': period,
        'period_name': period_name,
        'start_date': start_date,
        'end_date': end_date,
        
        # Tahsilatlar
        'centers_with_physical_molds': centers_with_physical_molds,
        'total_collections_from_centers': total_collections_from_centers,
        
        # Ödemeler
        'producers_payment_summary': producers_payment_summary,
        'total_payments_to_producers': total_payments_to_producers,
        
        # Komisyonlar
        'total_moldpark_service_fee': total_moldpark_service_fee,
        'total_credit_card_commission': total_credit_card_commission,
        'moldpark_net_profit': moldpark_net_profit,
        
        # Para akışı
        'cash_flow': cash_flow,
        
        # Fatura durumları
        'center_invoice_stats': center_invoice_stats,
        'producer_invoice_stats': producer_invoice_stats,
    }
    
    return render(request, 'core/financial/admin_control_panel.html', context)


@user_passes_test(lambda u: u.is_superuser)
def bulk_create_center_invoices(request):
    """İşitme merkezlerine toplu fatura kesme"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)
    
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        period = request.GET.get('period', 'this_month')
        now = timezone.now()
        
        # Dönem hesaplama
        if period == 'this_month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'last_month':
            last_month = now.replace(day=1) - timedelta(days=1)
            start_date = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = last_month.replace(day=28, hour=23, minute=59, second=59)
        elif period == 'this_year':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        else:  # all_time
            start_date = datetime(2020, 1, 1)
            end_date = now
        
        created_invoices = []
        total_amount = Decimal('0.00')
        
        # Tüm aktif merkezler
        all_centers = Center.objects.filter(is_active=True)
        
        for center in all_centers:
            # Bu merkezden gönderilen fiziksel kalıplar
            physical_molds = EarMold.objects.filter(
                center=center,
                is_physical_shipment=True,
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            physical_count = physical_molds.count()
            
            if physical_count > 0:
                # Fatura oluştur
                invoice = Invoice()
                invoice.invoice_type = 'center_admin_invoice'
                invoice.issued_by_center = center
                invoice.user = center.user
                invoice.physical_mold_count = physical_count
                invoice.physical_mold_unit_price = Decimal('450.00')
                
                # Hesaplamalar
                gross_amount = physical_count * Decimal('450.00')
                moldpark_fee = gross_amount * Decimal('0.065')
                cc_fee = gross_amount * Decimal('0.03')
                
                invoice.total_amount = gross_amount
                invoice.moldpark_service_fee = moldpark_fee
                invoice.credit_card_fee = cc_fee
                invoice.moldpark_service_fee_rate = Decimal('0.065')
                invoice.credit_card_fee_rate = Decimal('0.03')
                
                invoice.issue_date = now.date()
                invoice.due_date = (now + timedelta(days=30)).date()
                invoice.status = 'issued'
                
                # Fatura numarası oluştur
                invoice.invoice_number = Invoice.generate_invoice_number('center_admin_invoice')
                
                invoice.save()
                created_invoices.append(invoice)
                total_amount += gross_amount
                
                # E-posta gönder
                try:
                    subject = f'MoldPark Fatura - {invoice.invoice_number}'
                    message = f"""
Sayın {center.name},

{physical_count} adet fiziksel kalıp hizmeti için faturanız oluşturulmuştur.

Fatura No: {invoice.invoice_number}
Tutar: ₺{gross_amount}
Vade Tarihi: {invoice.due_date.strftime('%d.%m.%Y')}

Detaylar için MoldPark paneline giriş yapabilirsiniz.

İyi günler dileriz,
MoldPark Ekibi
                    """
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [center.user.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"E-posta gönderme hatası: {e}")
        
        return JsonResponse({
            'success': True,
            'created_count': len(created_invoices),
            'total_amount': f'{total_amount:,.2f}',
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@user_passes_test(lambda u: u.is_superuser)
def bulk_create_producer_invoices(request):
    """Üreticilere toplu fatura kesme"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)
    
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        period = request.GET.get('period', 'this_month')
        now = timezone.now()
        
        # Dönem hesaplama
        if period == 'this_month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'last_month':
            last_month = now.replace(day=1) - timedelta(days=1)
            start_date = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = last_month.replace(day=28, hour=23, minute=59, second=59)
        elif period == 'this_year':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        else:  # all_time
            start_date = datetime(2020, 1, 1)
            end_date = now
        
        created_invoices = []
        total_net_amount = Decimal('0.00')
        
        # Tüm aktif üreticiler
        all_producers = Producer.objects.filter(is_active=True)
        
        for producer in all_producers:
            # Bu üreticinin tamamladığı işler
            completed_orders = producer.orders.filter(
                Q(status='delivered') | 
                Q(status__in=['received', 'designing', 'production', 'quality_check', 'packaging', 'shipping'], 
                  ear_mold__is_physical_shipment=True),
                created_at__gte=start_date,
                created_at__lte=end_date
            ).select_related('ear_mold')
            
            if completed_orders.exists():
                # Brüt kazanç hesapla
                gross_revenue = Decimal('0.00')
                physical_count = 0
                digital_count = 0
                
                for order in completed_orders:
                    if order.ear_mold.is_physical_shipment:
                        gross_revenue += Decimal('450.00')
                        physical_count += 1
                    else:
                        gross_revenue += Decimal('50.00')
                        digital_count += 1
                
                # Fatura oluştur
                invoice = Invoice()
                invoice.invoice_type = 'producer_invoice'
                invoice.issued_by_producer = producer
                invoice.producer = producer
                invoice.user = producer.user
                
                invoice.producer_gross_revenue = gross_revenue
                invoice.physical_mold_count = physical_count
                invoice.modeling_count = digital_count
                
                # Kesintiler
                moldpark_cut = gross_revenue * Decimal('0.065')
                cc_cut = gross_revenue * Decimal('0.03')
                net_payment = gross_revenue - moldpark_cut - cc_cut
                
                invoice.moldpark_service_fee = moldpark_cut
                invoice.credit_card_fee = cc_cut
                invoice.net_amount = net_payment
                invoice.total_amount = gross_revenue
                
                invoice.issue_date = now.date()
                invoice.due_date = (now + timedelta(days=30)).date()
                invoice.status = 'issued'
                
                # Fatura numarası oluştur
                invoice.invoice_number = Invoice.generate_invoice_number('producer_invoice')
                
                invoice.save()
                created_invoices.append(invoice)
                total_net_amount += net_payment
                
                # E-posta gönder
                try:
                    subject = f'MoldPark Ödeme Bildirimi - {invoice.invoice_number}'
                    message = f"""
Sayın {producer.company_name},

Hizmet bedeliniz için ödeme bildirimi oluşturulmuştur.

Fatura No: {invoice.invoice_number}
Brüt Tutar: ₺{gross_revenue}
MoldPark Hizmet Bedeli: ₺{moldpark_cut}
Kredi Kartı Komisyonu: ₺{cc_cut}
Net Ödeme: ₺{net_payment}
Ödeme Tarihi: {invoice.due_date.strftime('%d.%m.%Y')}

Detaylar için MoldPark paneline giriş yapabilirsiniz.

İyi günler dileriz,
MoldPark Ekibi
                    """
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [producer.user.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"E-posta gönderme hatası: {e}")
        
        return JsonResponse({
            'success': True,
            'created_count': len(created_invoices),
            'total_amount': f'{total_net_amount:,.2f}',
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

