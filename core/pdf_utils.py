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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from decimal import Decimal
import io
import os
from django.conf import settings

# Türkçe karakter desteği için font kaydı
# ReportLab'in built-in font'ları (Helvetica, Times-Roman) Türkçe karakterleri desteklemez
# Bu yüzden Unicode destekli font (DejaVu Sans veya Arial Unicode MS) yüklemeye çalışıyoruz
TURKISH_FONT = 'Helvetica'
TURKISH_FONT_BOLD = 'Helvetica-Bold'
FONT_LOADED = False

def _register_turkish_fonts():
    """Türkçe karakter desteği için font kaydet"""
    global TURKISH_FONT, TURKISH_FONT_BOLD, FONT_LOADED
    
    # Font yolları (öncelik sırasına göre)
    font_configs = [
        # 1. DejaVu Sans (en iyi Unicode desteği)
        {
            'name': 'DejaVuSans',
            'regular': os.path.join(os.path.dirname(__file__), '..', 'static', 'fonts', 'DejaVuSans.ttf'),
            'bold': os.path.join(os.path.dirname(__file__), '..', 'static', 'fonts', 'DejaVuSans-Bold.ttf'),
        },
        # 2. Windows Arial Unicode MS (geniş Unicode desteği)
        {
            'name': 'ArialUnicodeMS',
            'regular': 'C:/Windows/Fonts/ARIALUNI.TTF',
            'bold': 'C:/Windows/Fonts/ARIALUNI.TTF',  # Arial Unicode MS'in bold versiyonu yok, aynı fontu kullan
        },
        # 3. Windows Arial (Türkçe karakterleri destekler)
        {
            'name': 'Arial',
            'regular': 'C:/Windows/Fonts/arial.ttf',
            'bold': 'C:/Windows/Fonts/arialbd.ttf',
        },
        # 4. Windows Tahoma (Türkçe karakterleri destekler)
        {
            'name': 'Tahoma',
            'regular': 'C:/Windows/Fonts/tahoma.ttf',
            'bold': 'C:/Windows/Fonts/tahomabd.ttf',
        },
    ]
    
    for font_config in font_configs:
        try:
            regular_path = font_config['regular']
            bold_path = font_config['bold']
            
            # Regular font kontrolü
            if os.path.exists(regular_path):
                try:
                    # Font dosyasını yükle
                    pdfmetrics.registerFont(TTFont(font_config['name'], regular_path))
                    TURKISH_FONT = font_config['name']
                    
                    # Bold font kontrolü
                    if os.path.exists(bold_path) and bold_path != regular_path:
                        try:
                            pdfmetrics.registerFont(TTFont(f'{font_config["name"]}-Bold', bold_path))
                            TURKISH_FONT_BOLD = f'{font_config["name"]}-Bold'
                        except Exception as bold_error:
                            # Bold font yüklenemezse regular fontu bold olarak kullan
                            TURKISH_FONT_BOLD = font_config['name']
                    else:
                        # Bold font yoksa regular fontu bold olarak kullan
                        TURKISH_FONT_BOLD = font_config['name']
                    
                    FONT_LOADED = True
                    # Başarılı font yüklemesinde dur
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Türkçe karakter desteği için font yüklendi: {TURKISH_FONT} (Bold: {TURKISH_FONT_BOLD})")
                    break
                except Exception as e:
                    # Font yükleme hatası, bir sonraki fontu dene
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Font yükleme hatası ({font_config['name']}): {str(e)}")
                    continue
        except:
            continue

# Font kayıt işlemini başlat
try:
    _register_turkish_fonts()
    # Debug: Font yükleme durumunu logla (production'da kaldırılabilir)
    import logging
    logger = logging.getLogger(__name__)
    if FONT_LOADED:
        logger.info(f"Türkçe karakter desteği için font yüklendi: {TURKISH_FONT} (Bold: {TURKISH_FONT_BOLD})")
    else:
        logger.warning("Türkçe karakter desteği için font yüklenemedi. Windows sistem fontlarını kontrol edin.")
except Exception as e:
    # Hata durumunda varsayılan font
    TURKISH_FONT = 'Helvetica'
    TURKISH_FONT_BOLD = 'Helvetica-Bold'
    FONT_LOADED = False
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Font yükleme hatası: {str(e)}")


def link_callback(uri, rel):
    """xhtml2pdf için link callback fonksiyonu"""
    return uri


def safe_paragraph_text(text):
    """
    ReportLab Paragraph için güvenli metin hazırla
    ReportLab Paragraph Unicode karakterleri destekler, ancak font yüklü olmalı
    Font yüklü değilse, Türkçe karakterler görünmeyebilir
    Bu yüzden font yüklemesini zorunlu hale getirmek veya alternatif çözüm kullanmak gerekir
    """
    if not text:
        return text
    
    # Metni string'e çevir ve Unicode olarak kullan
    # ReportLab Paragraph Unicode karakterleri destekler, font yüklüyse çalışır
    text = str(text)
    
    # HTML entity kullanmak yerine, doğrudan Unicode karakterleri kullanıyoruz
    # Çünkü ReportLab Paragraph Unicode'u destekliyor, sadece font gerekli
    # Font yüklü değilse karakterler görünmeyebilir ama en azından bozulmaz
    
    return text


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

    # Özel stiller - Türkçe karakter desteği ile
    # ReportLab Paragraph HTML encoding kullanır, bu yüzden encoding parametresi yok
    # Türkçe karakterler için Paragraph içinde HTML entity veya doğrudan Unicode kullanılabilir
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=TURKISH_FONT_BOLD,
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center alignment
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=TURKISH_FONT,
        fontSize=10,
        spaceAfter=10
    )

    # Content listesi
    content = []

    # Başlık
    content.append(Paragraph("MOLDPARK FATURA", title_style))
    content.append(Spacer(1, 20))

    # Fatura bilgileri - Türkçe karakterler için güvenli metin kullan
    # ReportLab Paragraph HTML encoding destekler, font yüklüyse Türkçe karakterler doğrudan çalışır
    invoice_number_text = safe_paragraph_text(invoice.invoice_number)
    date_text = invoice.issue_date.strftime('%d/%m/%Y')
    center_name_text = safe_paragraph_text(center.name)
    
    content.append(Paragraph(f"<b>Fatura No:</b> {invoice_number_text}", normal_style))
    content.append(Paragraph(f"<b>Tarih:</b> {date_text}", normal_style))
    if invoice.due_date:
        due_date_text = invoice.due_date.strftime('%d/%m/%Y')
        content.append(Paragraph(f"<b>Vade Tarihi:</b> {due_date_text}", normal_style))
    # Müşteri adında Türkçe karakterler olabilir
    content.append(Paragraph(f"<b>Müşteri:</b> {center_name_text}", normal_style))
    content.append(Spacer(1, 20))

    # Hesaplama
    total_with_vat = invoice.total_amount or Decimal('0.00')
    subtotal_without_vat = (total_with_vat / Decimal('1.20')).quantize(Decimal('0.01'))
    vat_amount = (total_with_vat - subtotal_without_vat).quantize(Decimal('0.01'))

    # Tablo verisi - Türkçe karakter desteği için Paragraph kullan
    # ReportLab Paragraph HTML encoding destekler, font yüklüyse Türkçe karakterler doğrudan çalışır
    table_data = [
        [
            Paragraph(safe_paragraph_text('Hizmet'), normal_style),
            Paragraph(safe_paragraph_text('Adet'), normal_style),
            Paragraph(safe_paragraph_text('Birim Fiyat'), normal_style),
            Paragraph(safe_paragraph_text('Toplam'), normal_style)
        ],
        [
            Paragraph(safe_paragraph_text('Aylık Sistem Ücreti'), normal_style),
            Paragraph('1', normal_style),
            Paragraph(f'₺{invoice.monthly_fee:.2f}', normal_style),
            Paragraph(f'₺{invoice.monthly_fee:.2f}', normal_style)
        ],
    ]

    if invoice.physical_mold_count > 0:
        table_data.append([
            Paragraph(safe_paragraph_text('Fiziksel Kalıp'), normal_style),
            Paragraph(str(invoice.physical_mold_count), normal_style),
            Paragraph(f'₺{invoice.physical_mold_cost / invoice.physical_mold_count:.2f}', normal_style),
            Paragraph(f'₺{invoice.physical_mold_cost:.2f}', normal_style)
        ])

    if invoice.digital_scan_count > 0:
        table_data.append([
            Paragraph(safe_paragraph_text('3D Modelleme'), normal_style),
            Paragraph(str(invoice.digital_scan_count), normal_style),
            Paragraph(f'₺{invoice.digital_scan_cost / invoice.digital_scan_count:.2f}', normal_style),
            Paragraph(f'₺{invoice.digital_scan_cost:.2f}', normal_style)
        ])

    # Toplam satırı
    table_data.append([
        Paragraph('', normal_style),
        Paragraph('', normal_style),
        Paragraph(safe_paragraph_text('Ara Toplam'), normal_style),
        Paragraph(f'₺{subtotal_without_vat:.2f}', normal_style)
    ])
    table_data.append([
        Paragraph('', normal_style),
        Paragraph('', normal_style),
        Paragraph(safe_paragraph_text('KDV (20%)'), normal_style),
        Paragraph(f'₺{vat_amount:.2f}', normal_style)
    ])
    table_data.append([
        Paragraph('', normal_style),
        Paragraph('', normal_style),
        Paragraph(f'<b>{safe_paragraph_text("GENEL TOPLAM")}</b>', normal_style),
        Paragraph(f'<b>₺{total_with_vat:.2f}</b>', normal_style)
    ])

    # Tablo oluştur
    table = Table(table_data, colWidths=[6*cm, 2*cm, 3*cm, 3*cm])

    # Tablo stili - Türkçe karakter desteği ile
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), TURKISH_FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (-1, -4), (-1, -1), 'RIGHT'),
        ('FONTNAME', (-1, -1), (-1, -1), TURKISH_FONT_BOLD),
    ]))

    content.append(table)
    content.append(Spacer(1, 30))

    # Footer - Türkçe karakterler için güvenli metin kullan
    footer_text = safe_paragraph_text("MoldPark - Kulak Kalıbı Üretim Yönetim Sistemi")
    content.append(Paragraph(footer_text, normal_style))
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

