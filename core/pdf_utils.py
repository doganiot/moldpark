"""
PDF Fatura Oluşturma Yardımcı Fonksiyonları
"""
from django.template.loader import render_to_string
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from decimal import Decimal
import io
import os
from django.conf import settings


def generate_invoice_pdf(invoice, center):
    """
    Fatura için PDF oluşturur (Türkçe karakter desteği ile)

    Args:
        invoice: Invoice model instance
        center: Center model instance

    Returns:
        HttpResponse: PDF dosyası
    """
    # PDF buffer oluştur
    buffer = io.BytesIO()

    # PDF document oluştur
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    # Özel stiller
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center alignment
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=10,
    )

    # Content listesi
    content = []

    # Başlık
    content.append(Paragraph("MOLDPARK FATURA", title_style))
    content.append(Spacer(1, 20))

    # Fatura bilgileri
    content.append(Paragraph(f"<b>Fatura No:</b> {invoice.invoice_number}", normal_style))
    content.append(Paragraph(f"<b>Tarih:</b> {invoice.issue_date.strftime('%d/%m/%Y')}", normal_style))
    content.append(Paragraph(f"<b>Vade Tarihi:</b> {invoice.due_date.strftime('%d/%m/%Y')}", normal_style))
    content.append(Paragraph(f"<b>Müşteri:</b> {center.name}", normal_style))
    content.append(Spacer(1, 20))

    # Hesaplama
    total_with_vat = invoice.total_amount or Decimal('0.00')
    subtotal_without_vat = (total_with_vat / Decimal('1.20')).quantize(Decimal('0.01'))
    vat_amount = (total_with_vat - subtotal_without_vat).quantize(Decimal('0.01'))

    # Tablo verisi
    table_data = [
        ['Hizmet', 'Adet', 'Birim Fiyat', 'Toplam'],
        ['Aylık Sistem Ücreti', '1', f'₺{invoice.monthly_fee:.2f}', f'₺{invoice.monthly_fee:.2f}'],
    ]

    if invoice.physical_mold_count > 0:
        table_data.append([
            'Fiziksel Kalıp',
            str(invoice.physical_mold_count),
            f'₺{invoice.physical_mold_cost / invoice.physical_mold_count:.2f}',
            f'₺{invoice.physical_mold_cost:.2f}'
        ])

    if invoice.digital_scan_count > 0:
        table_data.append([
            '3D Modelleme',
            str(invoice.digital_scan_count),
            f'₺{invoice.digital_scan_cost / invoice.digital_scan_count:.2f}',
            f'₺{invoice.digital_scan_cost:.2f}'
        ])

    # Toplam satırı
    table_data.append(['', '', 'Ara Toplam', f'₺{subtotal_without_vat:.2f}'])
    table_data.append(['', '', 'KDV (20%)', f'₺{vat_amount:.2f}'])
    table_data.append(['', '', '<b>GENEL TOPLAM</b>', f'<b>₺{total_with_vat:.2f}</b>'])

    # Tablo oluştur
    table = Table(table_data, colWidths=[6*cm, 2*cm, 3*cm, 3*cm])

    # Tablo stili
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (-1, -4), (-1, -1), 'RIGHT'),
        ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
    ]))

    content.append(table)
    content.append(Spacer(1, 30))

    # Footer
    content.append(Paragraph("MoldPark - Kulak Kalıbı Üretim Yönetim Sistemi", normal_style))
    content.append(Paragraph("www.moldpark.com", normal_style))

    # PDF oluştur
    doc.build(content)

    # HTTP Response oluştur
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
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

