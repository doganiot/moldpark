"""
PDF Fatura Oluşturma Yardımcı Fonksiyonları
"""
from django.template.loader import render_to_string
from django.http import HttpResponse
from xhtml2pdf import pisa
from decimal import Decimal
import io
import os
from django.conf import settings


def link_callback(uri, rel):
    """
    xhtml2pdf için statik dosyaları ve fontları yüklemek için callback fonksiyonu
    """
    # Statik dosyalar için
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT or settings.STATICFILES_DIRS[0], 
                          uri.replace(settings.STATIC_URL, ""))
    else:
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    
    # Dosya kontrolü
    if not os.path.isfile(path):
        return uri
    
    return path


def generate_invoice_pdf(invoice, center):
    """
    Fatura için PDF oluşturur (Türkçe karakter desteği ile)
    
    Args:
        invoice: Invoice model instance
        center: Center model instance
        
    Returns:
        HttpResponse: PDF dosyası
    """
    # KDV'siz ve KDV tutarlarını hesapla
    total_with_vat = invoice.total_amount or Decimal('0.00')
    subtotal_without_vat = (total_with_vat / Decimal('1.20')).quantize(Decimal('0.01'))
    vat_amount = (total_with_vat - subtotal_without_vat).quantize(Decimal('0.01'))
    
    # Context hazırla
    context = {
        'invoice': invoice,
        'center_name': center.name,
        'subtotal_without_vat': subtotal_without_vat,
        'vat_amount': vat_amount,
        'total_with_vat': total_with_vat,
    }
    
    # HTML render et
    html_string = render_to_string('core/financial/invoice_pdf_template.html', context)
    
    # PDF'e dönüştür (Türkçe karakter desteği için UTF-8 encoding)
    result = io.BytesIO()
    
    # xhtml2pdf için özel konfigürasyon
    pdf = pisa.pisaDocument(
        src=io.BytesIO(html_string.encode("utf-8")),
        dest=result,
        encoding='utf-8',
        link_callback=link_callback
    )
    
    if pdf.err:
        return HttpResponse('PDF oluşturulurken hata oluştu', status=500)
    
    # HTTP Response oluştur
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="fatura_{invoice.invoice_number}.pdf"'
    
    return response


def generate_monthly_invoices_batch(centers, year, month):
    """
    Birden fazla merkez için toplu fatura oluşturur
    
    Args:
        centers: QuerySet of Center objects
        year: int
        month: int
        
    Returns:
        list: Oluşturulan fatura listesi
    """
    from core.models import Invoice, PricingConfiguration
    from mold.models import EarMold
    from datetime import date, timedelta
    from decimal import Decimal
    
    created_invoices = []
    
    # Aktif fiyatlandırmayı al
    pricing = PricingConfiguration.get_active()
    
    # Ay başı ve sonu
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)
    
    for center in centers:
        # Bu ay oluşturulan kalıplar
        molds = EarMold.objects.filter(
            center=center,
            created_at__gte=month_start,
            created_at__lt=month_end
        )
        
        # Kalıp sayıları
        physical_count = molds.filter(is_physical_shipment=True).count()
        digital_count = molds.filter(is_physical_shipment=False).count()
        
        # Fatura zaten var mı kontrol et
        existing = Invoice.objects.filter(
            user=center.user,
            invoice_type='center_admin_invoice',
            issue_date__year=year,
            issue_date__month=month
        ).exists()
        
        if existing:
            continue
        
        # Yeni fatura oluştur - Her aktif merkez için aylık ücret + kullanım bedelleri
        invoice_number = Invoice.generate_invoice_number('center_monthly')
        
        # Dinamik fiyatlandırma ile hesapla (KDV dahil)
        monthly_fee = pricing.monthly_system_fee
        physical_cost = physical_count * pricing.physical_mold_price
        digital_cost = digital_count * pricing.digital_modeling_price
        total_amount = monthly_fee + physical_cost + digital_cost
        
        # KDV'siz tutar
        subtotal_without_vat = (total_amount / Decimal('1.20')).quantize(Decimal('0.01'))
        
        # Fatura oluştur
        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            invoice_type='center_admin_invoice',
            user=center.user,
            issued_by_center=center,
            issue_date=month_start,
            due_date=month_start + timedelta(days=30),
            monthly_fee=monthly_fee,
            physical_mold_count=physical_count,
            physical_mold_cost=physical_cost,
            digital_scan_count=digital_count,
            digital_scan_cost=digital_cost,
            subtotal=total_amount,
            subtotal_without_vat=subtotal_without_vat,
            credit_card_fee=Decimal('0.00'),
            total_amount=total_amount,
            status='issued'
        )
        
        created_invoices.append(invoice)
    
    return created_invoices

