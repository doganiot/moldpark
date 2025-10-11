"""
PDF Fatura Oluşturma Yardımcı Fonksiyonları
"""
from django.template.loader import render_to_string
from django.http import HttpResponse
from xhtml2pdf import pisa
from decimal import Decimal
import io


def generate_invoice_pdf(invoice, center):
    """
    Fatura için PDF oluşturur
    
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
    
    # PDF'e dönüştür
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html_string.encode("UTF-8")), result)
    
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
    from core.models import Invoice
    from mold.models import EarMold
    from datetime import date, timedelta
    from decimal import Decimal
    
    created_invoices = []
    
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
        
        # Eğer hiç kalıp yoksa ve sadece aylık ücret varsa
        if physical_count == 0 and digital_count == 0:
            # Aylık ücret için fatura oluştur
            total_molds = molds.count()
            if total_molds > 0:  # Eğer kalıp varsa aylık ücret al
                pass
            else:
                continue  # Hiç kalıp yoksa fatura kesme
        
        # Fatura zaten var mı kontrol et
        existing = Invoice.objects.filter(
            user=center.user,
            invoice_type='center_admin_invoice',
            issue_date__year=year,
            issue_date__month=month
        ).exists()
        
        if existing:
            continue
        
        # Yeni fatura oluştur
        invoice_number = Invoice.generate_invoice_number('center_monthly')
        
        # Fiyat hesapla (KDV dahil)
        MONTHLY_FEE = Decimal('100.00')
        PHYSICAL_PRICE = Decimal('450.00')
        DIGITAL_PRICE = Decimal('50.00')
        
        monthly_fee = MONTHLY_FEE
        physical_cost = physical_count * PHYSICAL_PRICE
        digital_cost = digital_count * DIGITAL_PRICE
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

