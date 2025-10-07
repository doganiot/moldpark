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
    
    # Faturalar
    invoices = Invoice.objects.filter(
        issue_date__gte=start_date.date(),
        issue_date__lte=end_date.date(),
        status__in=['issued', 'paid']
    )
    
    center_invoices = invoices.filter(invoice_type='center')
    producer_invoices = invoices.filter(invoice_type='producer')
    
    # İşitme Merkezi Gelirleri
    center_stats = {
        'count': center_invoices.count(),
        'monthly_fees': sum(inv.monthly_fee for inv in center_invoices),
        'physical_revenue': sum((inv.physical_mold_cost or 0) + (inv.mold_cost or 0) for inv in center_invoices),
        'digital_revenue': sum((inv.digital_scan_cost or 0) + (inv.modeling_cost or 0) for inv in center_invoices),
        'credit_card_fees': sum(inv.credit_card_fee for inv in center_invoices),
    }
    center_stats['total_revenue'] = center_stats['monthly_fees'] + center_stats['physical_revenue'] + center_stats['digital_revenue']
    center_stats['net_revenue'] = center_stats['total_revenue']  # Merkezlerden komisyon almıyoruz
    
    # Üretici Gelirleri ve Komisyonlar
    producer_stats = {
        'count': producer_invoices.count(),
        'gross_revenue': sum(inv.producer_revenue for inv in producer_invoices),
        'moldpark_commission': sum(inv.moldpark_commission for inv in producer_invoices),
        'credit_card_fees': sum(inv.credit_card_fee for inv in producer_invoices),
    }
    producer_stats['net_to_producers'] = sum(inv.net_amount for inv in producer_invoices)
    
    # Toplam Gelir
    total_stats = {
        'gross_revenue': center_stats['total_revenue'] + producer_stats['gross_revenue'],
        'moldpark_earnings': center_stats['net_revenue'] + producer_stats['moldpark_commission'],
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
    
    # Kalıp İstatistikleri
    mold_stats = {
        'total_physical': sum((inv.physical_mold_count or 0) + (inv.mold_count or 0) for inv in center_invoices),
        'total_digital': sum((inv.digital_scan_count or 0) + (inv.modeling_count or 0) for inv in center_invoices),
        'total_producer_orders': sum(inv.producer_order_count for inv in producer_invoices),
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


@user_passes_test(lambda u: u.is_superuser)
def invoice_list(request):
    """Fatura listesi"""
    invoice_type = request.GET.get('type', 'all')
    status = request.GET.get('status', 'all')
    
    invoices = Invoice.objects.all()
    
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


@user_passes_test(lambda u: u.is_superuser)
def invoice_detail(request, invoice_id):
    """Fatura detayı"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    context = {
        'invoice': invoice,
    }
    
    return render(request, 'core/financial/invoice_detail.html', context)


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

