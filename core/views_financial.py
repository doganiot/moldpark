"""
Finansal Yönetim Views
Admin paneli için finansal dashboard ve fatura yönetimi
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from datetime import datetime, timedelta
from decimal import Decimal

from .models import Invoice, FinancialSummary, UserSubscription, PricingPlan, PricingConfiguration
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
    # K.K. komisyonu MoldPark'ın hizmet bedelinden düşülerek net kar bulunur
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
            Q(user=request.user) |  # Kendi faturaları
            Q(issued_by_center=request.user.center)  # Kestiği faturalar
        )
    elif hasattr(request.user, 'producer'):
        # Üretici kullanıcıları: kendi faturalarını ve kendi kestiği faturaları görebilir
        invoices = Invoice.objects.filter(
            Q(user=request.user) |  # Kendi faturaları
            Q(issued_by_producer=request.user.producer)  # Kestiği faturalar
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
    """Fatura detayı - Yetkilendirmeli - Basit ve temiz görünüm"""
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
    
    # Merkez adı
    center_name = "Müşteri"
    try:
        if hasattr(invoice, 'issued_by_center') and invoice.issued_by_center:
            center_name = invoice.issued_by_center.name
        elif invoice.user:
            if hasattr(invoice.user, 'center'):
                center_name = invoice.user.center.name
            else:
                center_name = invoice.user.get_full_name() or invoice.user.username
    except Exception:
        pass
    
    # Hesaplamalar
    total_with_vat = invoice.total_amount or Decimal('0.00')
    subtotal_without_vat = total_with_vat / Decimal('1.20')
    vat_amount = total_with_vat - subtotal_without_vat
    
    context = {
        'invoice': invoice,
        'center_name': center_name,
        'subtotal_without_vat': subtotal_without_vat,
        'vat_amount': vat_amount,
        'total_with_vat': total_with_vat,
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
    
    # Aktif fiyatlandırmayı al
    pricing = PricingConfiguration.get_active()
    
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
    total_monthly_system_fees = Decimal('0.00')  # Aylık sistem ücretleri toplamı
    
    for center in all_centers:
        # Bu merkezden gönderilen fiziksel kalıplar
        physical_molds = EarMold.objects.filter(
            center=center,
            is_physical_shipment=True,
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        # Sadece 3D modelleme hizmeti (fiziksel gönderim yok)
        digital_only_molds = EarMold.objects.filter(
            center=center,
            is_physical_shipment=False,
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        physical_count = physical_molds.count()
        digital_count = digital_only_molds.count()
        
        # Her aktif merkez için aylık sistem ücreti hesapla
        monthly_fee = pricing.monthly_system_fee
        total_monthly_system_fees += monthly_fee
        
        if physical_count > 0 or digital_count > 0 or monthly_fee > 0:
            # Fiziksel kalıp: Dinamik fiyat (KDV dahil)
            physical_amount_with_vat = physical_count * pricing.physical_mold_price
            
            # 3D Modelleme: Dinamik fiyat (KDV dahil)
            digital_amount_with_vat = digital_count * pricing.digital_modeling_price
            
            # Toplam tutar (KDV dahil) - Aylık ücret de dahil
            gross_amount_with_vat = physical_amount_with_vat + digital_amount_with_vat + monthly_fee
            
            # KDV hesaplamaları
            vat_multiplier = Decimal('1') + (pricing.vat_rate / Decimal('100'))
            gross_amount_without_vat = gross_amount_with_vat / vat_multiplier
            vat_amount = gross_amount_with_vat - gross_amount_without_vat
            
            # MoldPark hizmet bedeli KDV hariç tutar üzerinden
            moldpark_fee = pricing.calculate_moldpark_fee(gross_amount_without_vat)
            
            # K.K. komisyonu KDV dahil tutar üzerinden ama işitme merkezinden kesilir
            cc_fee = pricing.calculate_credit_card_fee(gross_amount_with_vat)
            
            # Üreticiye giden KDV hariç tutar
            net_to_producer = gross_amount_without_vat - moldpark_fee
            
            total_collections_from_centers += gross_amount_with_vat
            total_moldpark_service_fee += moldpark_fee
            total_credit_card_commission += cc_fee
            
            centers_with_physical_molds.append({
                'center': center,
                'physical_count': physical_count,
                'digital_count': digital_count,
                'physical_amount': physical_amount_with_vat,
                'digital_amount': digital_amount_with_vat,
                'monthly_system_fee': monthly_fee,
                'gross_amount': gross_amount_with_vat,
                'gross_amount_without_vat': gross_amount_without_vat,
                'vat_amount': vat_amount,
                'moldpark_fee': moldpark_fee,
                'cc_fee': cc_fee,
                'net_to_producer': net_to_producer,
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
            # Brüt kazanç (KDV dahil)
            gross_revenue_with_vat = Decimal('0.00')
            gross_revenue_without_vat = Decimal('0.00')
            vat_amount = Decimal('0.00')
            
            for order in completed_orders:
                if order.ear_mold.is_physical_shipment:
                    # Fiziksel kalıp - dinamik fiyat
                    with_vat = pricing.physical_mold_price
                    without_vat = pricing.get_physical_price_without_vat()
                    vat = pricing.calculate_vat(without_vat)
                    
                    gross_revenue_with_vat += with_vat
                    gross_revenue_without_vat += without_vat
                    vat_amount += vat
                else:
                    # 3D Modelleme - dinamik fiyat
                    with_vat = pricing.digital_modeling_price
                    without_vat = pricing.get_digital_price_without_vat()
                    vat = pricing.calculate_vat(without_vat)
                    
                    gross_revenue_with_vat += with_vat
                    gross_revenue_without_vat += without_vat
                    vat_amount += vat
            
            # MoldPark komisyonu BRÜT (KDV dahil) tutar üzerinden
            moldpark_cut = pricing.calculate_moldpark_fee(gross_revenue_with_vat)
            
            # K.K. komisyonu KDV dahil tutar üzerinden (işitme merkezinden kesilmiş)
            cc_cut = pricing.calculate_credit_card_fee(gross_revenue_with_vat)
            
            # Üreticiye net ödeme (Brüt tutar - MoldPark komisyonu)
            net_payment = gross_revenue_with_vat - moldpark_cut
            
            total_payments_to_producers += net_payment
            
            # Ödeme durumunu kontrol et (bu dönem için)
            # SimpleNotification'dan son ödeme kaydını bul
            from core.models import SimpleNotification
            last_payment = SimpleNotification.objects.filter(
                user=producer.user,
                title='✅ Ödeme Onaylandı',
                created_at__gte=start_date,
                created_at__lte=end_date
            ).order_by('-created_at').first()
            
            is_paid = last_payment is not None
            
            producers_payment_summary.append({
                'producer': producer,
                'physical_count': physical_count,
                'digital_count': digital_count,
                'total_orders': completed_orders.count(),
                'gross_revenue': gross_revenue_with_vat,
                'gross_revenue_without_vat': gross_revenue_without_vat,
                'vat_amount': vat_amount,
                'moldpark_cut': moldpark_cut,
                'cc_cut': cc_cut,
                'net_payment': net_payment,
                'is_paid': is_paid,  # Ödeme durumu
            })
    
    # ==========================================
    # 3. MOLDPARK NET KAZANCI
    # ==========================================
    
    # MoldPark'ın toplam geliri = Hizmet bedeli (%6.5)
    moldpark_total_income = total_moldpark_service_fee
    
    # Kredi kartı komisyonu MoldPark'ın hizmet bedelinden düşülür
    # Çünkü bu maliyet MoldPark'a aittir
    
    # MoldPark'ın net kazancı = Hizmet bedeli - Kredi kartı komisyonu
    moldpark_net_profit = moldpark_total_income - total_credit_card_commission
    
    # ==========================================
    # 4. PARA AKIŞI ÖZETİ
    # ==========================================
    
    cash_flow = {
        'total_incoming': total_collections_from_centers,  # İşitme merkezlerinden gelen
        'total_outgoing': total_payments_to_producers,  # Üreticilere giden
        'moldpark_service_income': total_moldpark_service_fee,  # MoldPark hizmet bedeli (brüt)
        'monthly_system_fees': total_monthly_system_fees,  # Aylık sistem kullanım ücretleri
        'credit_card_fees': total_credit_card_commission,  # Kredi kartı komisyonları (MoldPark'ın maliyeti)
        'moldpark_net_profit': moldpark_net_profit,  # MoldPark net kar (hizmet bedeli - KK komisyonu)
        'balance': total_collections_from_centers - total_payments_to_producers - total_credit_card_commission,  # Gerçek kalan bakiye
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
        
        # Ek Bilgiler
        'total_centers': all_centers.count(),  # Aktif merkez sayısı
        'pricing': pricing,  # Fiyatlandırma bilgisi
    }
    
    return render(request, 'core/financial/admin_control_panel.html', context)


@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["POST"])
def create_single_center_invoice(request, center_id):
    """Tek bir işitme merkezine fatura kesme"""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Merkezi al
        center = get_object_or_404(Center, id=center_id, is_active=True)
        
        # Aktif fiyatlandırmayı al
        pricing = PricingConfiguration.get_active()
        
        # Dönem bilgisi
        period = request.POST.get('period', 'this_month')
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
        
        # Bu dönemde zaten fatura kesilmiş mi kontrol et
        existing_invoice = Invoice.objects.filter(
            issued_by_center=center,
            invoice_type='center_admin_invoice',
            issue_date__gte=start_date.date(),
            issue_date__lte=end_date.date()
        ).first()
        
        if existing_invoice:
            return JsonResponse({
                'success': False,
                'error': f'Bu merkez için bu dönemde zaten fatura kesilmiş: {existing_invoice.invoice_number}'
            })
        
        # Bu merkezden gönderilen fiziksel kalıplar
        physical_molds = EarMold.objects.filter(
            center=center,
            is_physical_shipment=True,
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        # Sadece 3D modelleme hizmeti
        digital_only_molds = EarMold.objects.filter(
            center=center,
            is_physical_shipment=False,
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        physical_count = physical_molds.count()
        digital_count = digital_only_molds.count()
        
        # Fatura oluştur
        invoice = Invoice()
        invoice.invoice_type = 'center_admin_invoice'
        invoice.issued_by_center = center
        invoice.user = center.user
        invoice.physical_mold_count = physical_count
        invoice.modeling_count = digital_count
        invoice.physical_mold_unit_price = pricing.physical_mold_price
        invoice.monthly_fee = pricing.monthly_system_fee
        
        # Hesaplamalar
        physical_amount = physical_count * pricing.physical_mold_price
        digital_amount = digital_count * pricing.digital_modeling_price
        monthly_fee_amount = pricing.monthly_system_fee
        gross_amount = physical_amount + digital_amount + monthly_fee_amount
        
        # KDV hariç tutar
        vat_multiplier = Decimal('1') + (pricing.vat_rate / Decimal('100'))
        gross_without_vat = gross_amount / vat_multiplier
        
        # Komisyonlar
        moldpark_fee = pricing.calculate_moldpark_fee(gross_without_vat)
        cc_fee = pricing.calculate_credit_card_fee(gross_amount)
        
        # Fatura detayları
        invoice.physical_mold_cost = physical_amount
        invoice.digital_scan_count = digital_count
        invoice.digital_scan_cost = digital_amount
        invoice.total_amount = gross_amount
        invoice.moldpark_service_fee = moldpark_fee
        invoice.credit_card_fee = cc_fee
        invoice.moldpark_service_fee_rate = pricing.moldpark_commission_rate
        invoice.credit_card_fee_rate = pricing.credit_card_commission_rate
        invoice.issue_date = now.date()
        invoice.due_date = (now + timedelta(days=30)).date()
        invoice.status = 'issued'
        invoice.invoice_number = Invoice.generate_invoice_number('center_admin_invoice')
        
        invoice.save()
        
        # E-posta gönder
        try:
            services_text = []
            services_text.append(f"Aylık Sistem Kullanımı: {monthly_fee_amount} TL")
            if physical_count > 0:
                services_text.append(f"{physical_count} adet fiziksel kalıp ({physical_amount} TL)")
            if digital_count > 0:
                services_text.append(f"{digital_count} adet 3D modelleme ({digital_amount} TL)")
            
            subject = f'MoldPark Fatura - {invoice.invoice_number}'
            message = f"""
Sayın {center.name},

Aşağıdaki hizmetler için faturanız oluşturulmuştur:

{chr(10).join('- ' + s for s in services_text)}

Fatura No: {invoice.invoice_number}
Toplam Tutar: {gross_amount} TL
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
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'center_name': center.name,
            'total_amount': f'{gross_amount:,.2f}',
            'physical_count': physical_count,
            'digital_count': digital_count,
            'monthly_fee': f'{monthly_fee_amount:,.2f}',
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@user_passes_test(lambda u: u.is_superuser)
def bulk_create_center_invoices(request):
    """İşitme merkezlerine toplu fatura kesme"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)
    
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Aktif fiyatlandırmayı al
        pricing = PricingConfiguration.get_active()
        
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
            
            # Sadece 3D modelleme hizmeti
            digital_only_molds = EarMold.objects.filter(
                center=center,
                is_physical_shipment=False,
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            physical_count = physical_molds.count()
            digital_count = digital_only_molds.count()
            
            # Her aktif merkez için fatura oluştur (aylık ücret + kullanım bedelleri)
            # Fatura oluştur
            invoice = Invoice()
            invoice.invoice_type = 'center_admin_invoice'
            invoice.issued_by_center = center
            invoice.user = center.user
            invoice.physical_mold_count = physical_count
            invoice.modeling_count = digital_count
            invoice.physical_mold_unit_price = pricing.physical_mold_price
            invoice.monthly_fee = pricing.monthly_system_fee  # Aylık sistem kullanım ücreti
            
            # Hesaplamalar - dinamik fiyat
            physical_amount = physical_count * pricing.physical_mold_price
            digital_amount = digital_count * pricing.digital_modeling_price
            monthly_fee_amount = pricing.monthly_system_fee
            gross_amount = physical_amount + digital_amount + monthly_fee_amount  # Aylık ücret dahil
            
            # KDV hariç tutar
            vat_multiplier = Decimal('1') + (pricing.vat_rate / Decimal('100'))
            gross_without_vat = gross_amount / vat_multiplier
            
            # Komisyonlar
            moldpark_fee = pricing.calculate_moldpark_fee(gross_without_vat)
            cc_fee = pricing.calculate_credit_card_fee(gross_amount)
            
            # Fatura detaylarını set et
            invoice.physical_mold_cost = physical_amount
            invoice.digital_scan_count = digital_count
            invoice.digital_scan_cost = digital_amount
            invoice.total_amount = gross_amount
            invoice.moldpark_service_fee = moldpark_fee
            invoice.credit_card_fee = cc_fee
            invoice.moldpark_service_fee_rate = pricing.moldpark_commission_rate
            invoice.credit_card_fee_rate = pricing.credit_card_commission_rate
            
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
                # Hizmet detayları
                services_text = []
                services_text.append(f"Aylık Sistem Kullanımı: {monthly_fee_amount} TL")
                if physical_count > 0:
                    services_text.append(f"{physical_count} adet fiziksel kalıp ({physical_amount} TL)")
                if digital_count > 0:
                    services_text.append(f"{digital_count} adet 3D modelleme ({digital_amount} TL)")
                
                subject = f'MoldPark Fatura - {invoice.invoice_number}'
                message = f"""
Sayın {center.name},

Aşağıdaki hizmetler için faturanız oluşturulmuştur:

{chr(10).join('- ' + s for s in services_text)}

Fatura No: {invoice.invoice_number}
Toplam Tutar: {gross_amount} TL
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
        
        # Aktif fiyatlandırmayı al
        pricing = PricingConfiguration.get_active()
        
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
                        gross_revenue += pricing.physical_mold_price
                        physical_count += 1
                    else:
                        gross_revenue += pricing.digital_modeling_price
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
                
                # KDV hariç tutar
                vat_multiplier = Decimal('1') + (pricing.vat_rate / Decimal('100'))
                gross_without_vat = gross_revenue / vat_multiplier
                
                # Kesintiler - dinamik komisyon
                moldpark_cut = pricing.calculate_moldpark_fee(gross_without_vat)
                cc_cut = pricing.calculate_credit_card_fee(gross_revenue)
                net_payment = gross_without_vat - moldpark_cut
                
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


@user_passes_test(lambda u: u.is_superuser)
def invoice_delete(request, invoice_id):
    """Fatura silme işlemi - Sadece admin yetkisi ile"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Geçersiz istek metodu'}, status=405)
    
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Fatura bilgilerini kaydet (log için)
        invoice_number = invoice.invoice_number
        invoice_type = invoice.get_invoice_type_display()
        
        # Faturayı sil
        invoice.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'{invoice_number} numaralı {invoice_type} faturası başarıyla silindi.'
        })
        
    except Invoice.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Fatura bulunamadı'
        }, status=404)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Fatura silinirken hata oluştu: {str(e)}'
        }, status=500)


@user_passes_test(lambda u: u.is_superuser)
def bulk_delete_invoices(request):
    """Toplu fatura silme işlemi - Sadece admin yetkisi ile"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Geçersiz istek metodu'}, status=405)
    
    try:
        import json
        
        # JSON verisini al
        data = json.loads(request.body)
        invoice_ids = data.get('invoice_ids', [])
        
        if not invoice_ids:
            return JsonResponse({
                'success': False,
                'error': 'Silinecek fatura seçilmedi'
            })
        
        # Faturaları al ve bilgilerini topla
        invoices = Invoice.objects.filter(id__in=invoice_ids)
        count = invoices.count()
        
        if count == 0:
            return JsonResponse({
                'success': False,
                'error': 'Seçilen faturalar bulunamadı'
            })
        
        # Fatura numaralarını logla
        invoice_numbers = [inv.invoice_number for inv in invoices]
        
        # Toplu silme işlemi
        invoices.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'{count} adet fatura başarıyla silindi.',
            'deleted_count': count,
            'invoice_numbers': invoice_numbers
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Geçersiz JSON verisi'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Faturalar silinirken hata oluştu: {str(e)}'
        }, status=500)


@login_required
def download_invoice_pdf(request, invoice_id):
    """Faturayı PDF olarak indir"""
    from core.pdf_utils import generate_invoice_pdf
    
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Yetki kontrolü: Sadece kendi faturasını veya admin indirebilir
        if not request.user.is_superuser:
            # Merkezin kendi faturası mı kontrol et
            if hasattr(request.user, 'center'):
                if invoice.user != request.user and invoice.issued_by_center != request.user.center:
                    return HttpResponse("Bu faturayı görüntüleme yetkiniz yok", status=403)
            else:
                return HttpResponse("Fatura indirme yetkiniz yok", status=403)
        
        # Merkez bilgisini al
        if invoice.user:
            if hasattr(invoice.user, 'center'):
                center = invoice.user.center
            else:
                return HttpResponse("Fatura için merkez bilgisi bulunamadı", status=400)
        elif invoice.issued_by_center:
            center = invoice.issued_by_center
        else:
            return HttpResponse("Fatura için merkez bilgisi bulunamadı", status=400)
        
        # PDF oluştur ve indir
        return generate_invoice_pdf(invoice, center)
        
    except Exception as e:
        return HttpResponse(f"PDF oluşturulurken hata: {str(e)}", status=500)


@user_passes_test(lambda u: u.is_superuser)
def send_invoice_email(request, invoice_id):
    """Faturayı email ile gönder"""
    from django.core.mail import EmailMessage
    from core.pdf_utils import generate_invoice_pdf
    from django.conf import settings
    import io
    
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Merkez bilgisini al
        if invoice.user:
            center = invoice.user.center
            recipient_email = invoice.user.email
        elif invoice.issued_by_center:
            center = invoice.issued_by_center
            recipient_email = center.user.email
        else:
            return JsonResponse({
                'success': False,
                'error': 'Fatura için merkez bilgisi bulunamadı'
            })
        
        # PDF oluştur
        from django.template.loader import render_to_string
        from xhtml2pdf import pisa
        from decimal import Decimal
        import io
        
        # KDV hesapla
        total_with_vat = invoice.total_amount or Decimal('0.00')
        subtotal_without_vat = (total_with_vat / Decimal('1.20')).quantize(Decimal('0.01'))
        vat_amount = (total_with_vat - subtotal_without_vat).quantize(Decimal('0.01'))
        
        context = {
            'invoice': invoice,
            'center_name': center.name,
            'subtotal_without_vat': subtotal_without_vat,
            'vat_amount': vat_amount,
            'total_with_vat': total_with_vat,
        }
        
        html_string = render_to_string('core/financial/invoice_pdf_template.html', context)
        
        # PDF oluştur (Türkçe karakter desteği ile)
        from core.pdf_utils import link_callback
        result = io.BytesIO()
        pdf = pisa.pisaDocument(
            src=io.BytesIO(html_string.encode("utf-8")),
            dest=result,
            encoding='utf-8',
            link_callback=link_callback
        )
        
        if pdf.err:
            return JsonResponse({
                'success': False,
                'error': 'PDF oluşturulurken hata oluştu'
            })
        
        pdf_content = result.getvalue()
        
        # Email oluştur
        subject = f'MoldPark Fatura - {invoice.invoice_number}'
        message = f"""
Sayın {center.name},

{invoice.issue_date.strftime('%d.%m.%Y')} tarihli {invoice.invoice_number} numaralı faturanız ektedir.

Fatura Özeti:
- Toplam Tutar: {total_with_vat} TL (KDV Dahil)
- Vade Tarihi: {invoice.due_date.strftime('%d.%m.%Y') if invoice.due_date else '-'}

Ekteki PDF faturanızı inceleyebilirsiniz.

İyi günler dileriz,
MoldPark Ekibi
"""
        
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email]
        )
        
        # PDF'i ekle
        email.attach(
            f'fatura_{invoice.invoice_number}.pdf',
            pdf_content,
            'application/pdf'
        )
        
        # Gönder
        email.send()
        
        # Fatura durumunu güncelle
        if invoice.status == 'draft':
            invoice.status = 'issued'
            invoice.sent_date = timezone.now()
            invoice.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Fatura {recipient_email} adresine gönderildi'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Email gönderilirken hata: {str(e)}'
        })


@user_passes_test(lambda u: u.is_superuser)
def generate_monthly_invoices(request):
    """Tüm merkezler için aylık fatura oluştur"""
    from core.pdf_utils import generate_monthly_invoices_batch
    from datetime import date
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Geçersiz istek'})
    
    try:
        # Parametreleri al
        year = int(request.POST.get('year', date.today().year))
        month = int(request.POST.get('month', date.today().month))
        
        # Aktif merkezleri al
        centers = Center.objects.filter(is_active=True)
        
        # Toplu fatura oluştur
        created_invoices = generate_monthly_invoices_batch(centers, year, month)
        
        return JsonResponse({
            'success': True,
            'message': f'{len(created_invoices)} adet fatura oluşturuldu',
            'count': len(created_invoices)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Faturalar oluşturulurken hata: {str(e)}'
        })


@user_passes_test(lambda u: u.is_superuser)
def pricing_management(request):
    """
    Fiyatlandırma Yönetimi Sayfası
    Süperuser'ların sistem fiyatlarını görüntülemesi ve yönetmesi için
    """
    from core.models import PricingConfiguration
    
    # Aktif fiyatlandırma
    active_pricing = PricingConfiguration.get_active()
    
    # Tüm fiyatlandırmalar
    all_pricings = PricingConfiguration.objects.all().order_by('-effective_date', '-created_at')
    
    # Aktif fiyatlandırmanın özeti
    pricing_summary = active_pricing.get_pricing_summary() if active_pricing else None
    
    context = {
        'active_pricing': active_pricing,
        'all_pricings': all_pricings,
        'pricing_summary': pricing_summary,
    }
    
    return render(request, 'core/financial/pricing_management.html', context)


@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["POST"])
def send_producer_payment_notification(request):
    """
    Üreticiye ödeme bilgilendirme mesajı gönder
    """
    import json
    from producer.models import Producer
    from core.models import SimpleNotification
    from datetime import datetime
    
    try:
        data = json.loads(request.body)
        producer_id = data.get('producer_id')
        payment_amount = data.get('payment_amount')
        payment_date = data.get('payment_date')
        payment_method = data.get('payment_method')
        notes = data.get('notes', '')
        
        producer = Producer.objects.get(id=producer_id)
        
        # Ödeme yöntemi açıklaması
        payment_methods = {
            'bank_transfer': 'Banka Havalesi',
            'eft': 'EFT',
            'check': 'Çek',
            'cash': 'Nakit'
        }
        method_text = payment_methods.get(payment_method, payment_method)
        
        # Bildirim oluştur
        notification_message = f"""
🎉 Ödeme Bildirimi

Sayın {producer.company_name},

{payment_date} tarihinde {payment_amount} TL tutarında ödeme yapılmıştır.

Ödeme Yöntemi: {method_text}
{f'Not: {notes}' if notes else ''}

Ödemenizin hesabınıza geçmesi banka işlem süresine bağlı olarak değişebilir.

Sorularınız için bizimle iletişime geçebilirsiniz.

İyi çalışmalar dileriz.
MoldPark Ekibi
        """.strip()
        
        SimpleNotification.objects.create(
            user=producer.user,
            title='💰 Ödeme Yapıldı',
            message=notification_message,
            notification_type='success',
            related_url='/producer/payments/'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Ödeme bilgilendirme mesajı gönderildi'
        })
        
    except Producer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Üretici bulunamadı'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["POST"])
def mark_producer_as_paid(request):
    """
    Üreticiyi ödendi olarak işaretle
    """
    import json
    from producer.models import Producer
    from core.models import SimpleNotification
    from datetime import datetime
    
    try:
        data = json.loads(request.body)
        producer_id = data.get('producer_id')
        payment_amount = data.get('payment_amount')
        
        producer = Producer.objects.get(id=producer_id)
        
        # Bildirim oluştur
        SimpleNotification.objects.create(
            user=producer.user,
            title='✅ Ödeme Onaylandı',
            message=f"""
Sayın {producer.company_name},

{payment_amount} TL tutarındaki ödemeniz onaylanmıştır.

Ödeme detaylarını "Ödemelerim" sayfasından görüntüleyebilirsiniz.

İyi çalışmalar dileriz.
MoldPark Ekibi
            """.strip(),
            notification_type='success',
            related_url='/producer/payments/'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Ödeme onayı kaydedildi'
        })
        
    except Producer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Üretici bulunamadı'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

