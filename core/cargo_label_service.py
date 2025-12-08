"""
Kargo Etiketi Oluşturma Servisi
PDF, Termal ve Lazer etiketler için kapsamlı destek
"""
import os
import io
import qrcode
import barcode
from barcode.writer import ImageWriter
from decimal import Decimal
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib import colors
from reportlab.graphics.barcode import code128, qr
from reportlab.graphics import renderPDF
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
import base64

from .models import CargoShipment, CargoLabel


class CargoLabelGenerator:
    """Kargo Etiketi Üreteci"""

    def __init__(self, shipment, label_template=None):
        self.shipment = shipment
        self.template = label_template or self.get_default_template()
        self.width_mm = self.template.width_mm
        self.height_mm = self.template.height_mm
        self.font_family = "Helvetica"

        # Türkçe karakter desteği için font kaydı (DejaVuSans varsa)
        self.register_fonts()

        # Sayfa boyutunu hesapla (A4 için)
        self.page_width = 210 * mm  # A4 width
        self.page_height = 297 * mm  # A4 height

        # Etiket boyutunu hesapla
        self.label_width = self.width_mm * mm
        self.label_height = self.height_mm * mm

    def register_fonts(self):
        """Türkçe karakter desteği için DejaVuSans fontunu yükle, yoksa Helvetica kullan"""
        try:
            font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf')
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                self.font_family = 'DejaVuSans'
        except Exception:
            # Font bulunamazsa Helvetica ile devam edilir
            self.font_family = "Helvetica"

    def get_default_template(self):
        """Varsayılan etiket şablonunu getir"""
        return CargoLabel.objects.filter(is_active=True, is_default=True).first() or \
               CargoLabel.objects.filter(is_active=True).first() or \
               self.create_default_template()

    def create_default_template(self):
        """Varsayılan şablon oluştur"""
        template = CargoLabel.objects.create(
            name='Standart Etiket',
            description='Varsayılan kargo etiketi şablonu',
            width_mm=100,
            height_mm=150,
            size_preset='10x15',
            is_default=True,
            is_active=True
        )
        return template

    def generate_label(self, label_type='pdf'):
        """Etiket oluştur"""
        if label_type == 'pdf':
            return self.generate_pdf_label()
        elif label_type == 'thermal':
            return self.generate_thermal_label()
        elif label_type == 'laser':
            return self.generate_laser_label()
        else:
            raise ValueError(f"Desteklenmeyen etiket türü: {label_type}")

    def generate_pdf_label(self):
        """PDF etiket oluştur"""
        buffer = io.BytesIO()

        # Canvas oluştur
        c = canvas.Canvas(buffer, pagesize=A4)

        # Etiket konumunu hesapla (sayfa ortası)
        x_offset = (self.page_width - self.label_width) / 2
        y_offset = (self.page_height - self.label_height) / 2

        # Etiket arka planını çiz
        self.draw_background(c, x_offset, y_offset)

        # Etiket içeriğini çiz
        self.draw_content(c, x_offset, y_offset)

        # PDF'i kaydet
        c.save()
        buffer.seek(0)

        return buffer

    def draw_background(self, c, x, y):
        """Etiket arka planını çiz"""
        # Arka plan rengi
        if self.template.background_color != '#FFFFFF':
            c.setFillColor(HexColor(self.template.background_color))
            c.rect(x, y, self.label_width, self.label_height, fill=1)

        # Çerçeve
        c.setStrokeColor(HexColor(self.template.border_color))
        c.setLineWidth(1)
        c.rect(x, y, self.label_width, self.label_height, fill=0)

    def draw_content(self, c, x, y):
        """Etiket içeriğini çiz"""
        # Başlangıç pozisyonu
        current_y = y + self.label_height - 10*mm

        # Logo (eğer varsa)
        if self.template.include_logo:
            current_y = self.draw_logo(c, x, current_y)

        # Kargo firması bilgisi
        current_y = self.draw_company_info(c, x, current_y)

        # Takip numarası ve barkod
        current_y = self.draw_tracking_info(c, x, current_y)

        # Gönderen bilgileri
        if self.template.sender_info:
            current_y = self.draw_sender_info(c, x, current_y)

        # Alıcı bilgileri
        if self.template.recipient_info:
            current_y = self.draw_recipient_info(c, x, current_y)

        # Paket bilgileri
        if self.template.package_info:
            current_y = self.draw_package_info(c, x, current_y)

    def draw_logo(self, c, x, y):
        """Logo çiz"""
        try:
            logo_path = os.path.join(settings.STATIC_ROOT, 'images', 'moldpark_logo.jpg')
            if os.path.exists(logo_path):
                c.drawImage(logo_path, x + 5*mm, y - 15*mm, width=20*mm, height=10*mm)
        except:
            pass
        return y - 20*mm

    def draw_company_info(self, c, x, y):
        """Kargo firması bilgilerini çiz"""
        c.setFont("Helvetica-Bold", self.template.font_size_large)
        c.setFillColor(HexColor(self.template.text_color))

        company_name = self.shipment.cargo_company.display_name
        c.drawString(x + 5*mm, y, company_name)

        return y - 8*mm

    def draw_tracking_info(self, c, x, y):
        """Takip bilgilerini çiz"""
        # Takip numarası
        c.setFont("Helvetica-Bold", self.template.font_size_medium)
        tracking_text = f"Takip No: {self.shipment.tracking_number or 'Oluşturuluyor'}"
        c.drawString(x + 5*mm, y, tracking_text)

        # Barkod (eğer şablon destekliyorsa)
        if self.template.include_barcode and self.shipment.tracking_number:
            try:
                barcode_data = self.generate_barcode(self.shipment.tracking_number)
                if barcode_data:
                    # Barkod görselini çiz
                    barcode_width = 40*mm
                    barcode_height = 15*mm
                    c.drawImage(barcode_data, x + 5*mm, y - barcode_height - 2*mm,
                              width=barcode_width, height=barcode_height)
            except:
                pass

        # QR Kod (eğer şablon destekliyorsa)
        if self.template.include_qr:
            try:
                qr_data = self.generate_qr_code()
                if qr_data:
                    qr_size = 20*mm
                    c.drawImage(qr_data, x + self.label_width - qr_size - 5*mm,
                              y - qr_size - 2*mm, width=qr_size, height=qr_size)
            except:
                pass

        return y - 25*mm

    def draw_sender_info(self, c, x, y):
        """Gönderen bilgilerini çiz"""
        font_reg = self.font_family
        font_bold = f"{self.font_family}-Bold" if self.font_family != "Helvetica" else "Helvetica-Bold"

        c.setFont(font_reg, self.template.font_size_small)
        c.drawString(x + 5*mm, y, "GÖNDEREN:")
        y -= 4*mm

        c.setFont(font_bold, self.template.font_size_small)
        c.drawString(x + 5*mm, y, self.shipment.sender_name)
        y -= 3*mm

        # Adresi bölerek yaz
        sender_address = self.shipment.sender_address
        if len(sender_address) > 30:
            lines = [sender_address[i:i+30] for i in range(0, len(sender_address), 30)]
            for line in lines[:2]:  # Maksimum 2 satır
                c.drawString(x + 5*mm, y, line)
                y -= 3*mm
        else:
            c.drawString(x + 5*mm, y, sender_address)
            y -= 3*mm

        c.drawString(x + 5*mm, y, self.shipment.sender_phone)
        return y - 8*mm

    def draw_recipient_info(self, c, x, y):
        """Alıcı bilgilerini çiz"""
        font_reg = self.font_family
        font_bold = f"{self.font_family}-Bold" if self.font_family != "Helvetica" else "Helvetica-Bold"

        c.setFont(font_reg, self.template.font_size_small)
        c.drawString(x + 5*mm, y, "ALICI:")
        y -= 4*mm

        c.setFont(font_bold, self.template.font_size_small)
        c.drawString(x + 5*mm, y, self.shipment.recipient_name)
        y -= 3*mm

        # Adresi bölerek yaz
        recipient_address = self.shipment.recipient_address
        if len(recipient_address) > 30:
            lines = [recipient_address[i:i+30] for i in range(0, len(recipient_address), 30)]
            for line in lines[:2]:  # Maksimum 2 satır
            c.drawString(x + 5*mm, y, line)
                y -= 3*mm
        else:
            c.drawString(x + 5*mm, y, recipient_address)
            y -= 3*mm

        c.drawString(x + 5*mm, y, self.shipment.recipient_phone)
        return y - 8*mm

    def draw_package_info(self, c, x, y):
        """Paket bilgilerini çiz"""
        font_reg = self.font_family
        c.setFont(font_reg, self.template.font_size_small)
        c.drawString(x + 5*mm, y, f"Ağırlık: {self.shipment.weight_kg} kg")
        y -= 3*mm
        c.drawString(x + 5*mm, y, f"Paket: {self.shipment.package_count} adet")
        y -= 3*mm

        if self.shipment.description:
            c.drawString(x + 5*mm, y, f"İçerik: {self.shipment.description[:40]}")

        return y - 8*mm

    def generate_barcode(self, data):
        """Barkod oluştur"""
        try:
            # Code128 barkod oluştur
            barcode_obj = code128.Code128(data, barWidth=1, barHeight=30)
            return barcode_obj
        except:
            return None

    def generate_qr_code(self):
        """QR kod oluştur"""
        try:
            # QR kod verisi
            qr_data = f"""
Gönderi Takip: {self.shipment.tracking_number}
Firma: {self.shipment.cargo_company.display_name}
Alıcı: {self.shipment.recipient_name}
Tarih: {self.shipment.created_at.strftime('%d.%m.%Y')}
""".strip()

            # QR kod oluştur
            qr_code = qr.QrCodeWidget(qr_data)
            return qr_code
        except:
            return None

    def generate_thermal_label(self):
        """Termal etiket oluştur (basitleştirilmiş)"""
        # Termal etiketler için daha basit format
        buffer = io.BytesIO()

        # Basit text tabanlı termal etiket
        content = f"""
{self.shipment.cargo_company.display_name}
Takip No: {self.shipment.tracking_number}

GÖNDEREN:
{self.shipment.sender_name}
{self.shipment.sender_address}
{self.shipment.sender_phone}

ALICI:
{self.shipment.recipient_name}
{self.shipment.recipient_address}
{self.shipment.recipient_phone}

Ağırlık: {self.shipment.weight_kg}kg
Tarih: {self.shipment.created_at.strftime('%d.%m.%Y %H:%M')}
""".strip()

        # UTF-8 encoding ile dosyaya yaz
        buffer.write(content.encode('utf-8'))
        buffer.seek(0)

        return buffer

    def generate_laser_label(self):
        """Lazer etiket oluştur"""
        # Lazer etiketler için PDF benzeri format
        return self.generate_pdf_label()

    def save_label(self, label_type='pdf'):
        """Etiketi oluştur ve veritabanına kaydet"""
        try:
            # Etiket oluştur
            label_buffer = self.generate_label(label_type)

            # Dosya adı oluştur
            file_name = f"cargo_label_{self.shipment.id}_{int(timezone.now().timestamp())}"

            if label_type == 'pdf':
                file_name += '.pdf'
                content_type = 'application/pdf'
            elif label_type == 'thermal':
                file_name += '.txt'
                content_type = 'text/plain'
            else:
                file_name += '.pdf'
                content_type = 'application/pdf'

            # Django FileField'a kaydet
            file_content = ContentFile(label_buffer.getvalue())
            self.shipment.label_file.save(file_name, file_content, save=False)
            self.shipment.label_type = label_type
            self.shipment.label_generated = True
            self.shipment.label_generated_at = timezone.now()
            self.shipment.save()

            return True, file_name

        except Exception as e:
            return False, str(e)


class CargoLabelManager:
    """Kargo Etiketi Yönetim Sistemi"""

    @staticmethod
    def generate_label(shipment, label_type='pdf', template=None):
        """Gönderi için etiket oluştur"""
        try:
            generator = CargoLabelGenerator(shipment, template)
            success, result = generator.save_label(label_type)

            if success:
                return {
                    'success': True,
                    'message': 'Etiket başarıyla oluşturuldu',
                    'file_name': result,
                    'file_url': shipment.label_file.url if shipment.label_file else None
                }
            else:
                return {
                    'success': False,
                    'message': f'Etiket oluşturma hatası: {result}'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Etiket oluşturma hatası: {str(e)}'
            }

    @staticmethod
    def print_label(shipment):
        """Etiketi yazdır (JavaScript ile tarayıcıda)"""
        if not shipment.label_generated or not shipment.label_file:
            return {
                'success': False,
                'message': 'Önce etiket oluşturmalısınız'
            }

        shipment.label_print_count += 1
        shipment.save()

        return {
            'success': True,
            'message': 'Etiket yazdırma için hazır',
            'file_url': shipment.label_file.url
        }

    @staticmethod
    def get_available_templates():
        """Kullanılabilir etiket şablonlarını getir"""
        return CargoLabel.objects.filter(is_active=True).order_by('-is_default', 'name')

    @staticmethod
    def create_default_templates():
        """Varsayılan etiket şablonlarını oluştur"""
        templates = [
            {
                'name': 'Standart PDF Etiket',
                'description': 'A4 boyutunda standart kargo etiketi',
                'width_mm': 100,
                'height_mm': 150,
                'size_preset': '10x15',
                'is_default': True,
            },
            {
                'name': 'Termal Etiket Küçük',
                'description': '4x6 cm termal etiket',
                'width_mm': 40,
                'height_mm': 60,
                'size_preset': 'thermal_small',
                'font_size_small': 6,
                'font_size_medium': 8,
                'font_size_large': 10,
            },
            {
                'name': 'Termal Etiket Büyük',
                'description': '8x12 cm termal etiket',
                'width_mm': 80,
                'height_mm': 120,
                'size_preset': 'thermal_large',
                'font_size_small': 8,
                'font_size_medium': 12,
                'font_size_large': 14,
            }
        ]

        for template_data in templates:
            CargoLabel.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )

