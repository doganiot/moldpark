"""
Kargo Etiketi Oluşturma Servisi
PDF, Termal ve Lazer etiketler için kapsamlı destek
"""
import os
import io
import logging
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

logger = logging.getLogger(__name__)


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
    
    def _get_font_name(self, style='regular'):
        """Font adını stil ile al"""
        if style == 'bold':
            if self.font_family == "Helvetica":
                return "Helvetica-Bold"
            elif self.font_family in ["Arial", "Tahoma", "DejaVuSans"]:
                # Kayıtlı bold font varsa kullan
                bold_name = f"{self.font_family}-Bold"
                # Font'un kayıtlı olup olmadığını kontrol et
                try:
                    from reportlab.pdfbase import pdfmetrics
                    if bold_name in pdfmetrics.getRegisteredFontNames():
                        return bold_name
                except:
                    pass
                # Bold font yoksa regular font kullan
                return self.font_family
            else:
                return f"{self.font_family}-Bold"
        else:
            return self.font_family
    
    def _draw_text_safe(self, c, text, x, y, font_name, font_size):
        """Türkçe karakter desteği ile güvenli metin çizimi"""
        # Font'u ayarla
        c.setFont(font_name, font_size)
        
        # Text'i string'e çevir (eğer değilse)
        if not isinstance(text, str):
            try:
                text = str(text)
            except:
                text = ""
        
        try:
            # drawString ile çiz (font yüklüyse Türkçe karakterler çalışır)
            c.drawString(x, y, text)
        except Exception as e:
            # Eğer hata olursa, text'i güvenli hale getir
            try:
                # Türkçe karakterleri koruyarak encode et
                text_encoded = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                c.drawString(x, y, text_encoded)
            except Exception as e2:
                # Son çare: Problematik karakterleri değiştir
                try:
                    replacements = {
                        'ş': 's', 'Ş': 'S',
                        'ı': 'i', 'İ': 'I', 
                        'ğ': 'g', 'Ğ': 'G',
                        'ü': 'u', 'Ü': 'U',
                        'ö': 'o', 'Ö': 'O',
                        'ç': 'c', 'Ç': 'C'
                    }
                    text_safe = text
                    for tr_char, ascii_char in replacements.items():
                        text_safe = text_safe.replace(tr_char, ascii_char)
                    c.drawString(x, y, text_safe)
                except:
                    # En son çare: Hata mesajı
                    try:
                        c.drawString(x, y, "Encoding error")
                    except:
                        pass

    def register_fonts(self):
        """Türkçe karakter desteği için font yükle"""
        import platform
        
        # Font yolları (öncelik sırasına göre)
        font_configs = [
            # DejaVuSans (en iyi Unicode desteği)
            {
                'name': 'DejaVuSans',
                'paths': [
                    os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf'),
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                ],
                'bold_paths': [
                    os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans-Bold.ttf'),
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                ]
            },
            # Windows Arial (Türkçe karakterleri destekler)
            {
                'name': 'Arial',
                'paths': ['C:/Windows/Fonts/arial.ttf'],
                'bold_paths': ['C:/Windows/Fonts/arialbd.ttf']
            },
            # Windows Tahoma (Türkçe karakterleri destekler)
            {
                'name': 'Tahoma',
                'paths': ['C:/Windows/Fonts/tahoma.ttf'],
                'bold_paths': ['C:/Windows/Fonts/tahomabd.ttf']
            },
        ]
        
        font_registered = False
        for font_config in font_configs:
            font_name = font_config['name']
            for font_path in font_config['paths']:
                try:
                    if os.path.exists(font_path):
                        # Regular font'u kaydet
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        
                        # Bold font'u da kaydet (varsa)
                        for bold_path in font_config['bold_paths']:
                            if os.path.exists(bold_path):
                                try:
                                    pdfmetrics.registerFont(TTFont(f'{font_name}-Bold', bold_path))
                                except:
                                    pass
                        
                        self.font_family = font_name
                        font_registered = True
                        logger.info(f"Font yüklendi: {font_name} ({font_path})")
                        break
                except Exception as e:
                    logger.error(f"Font yükleme hatası ({font_path}): {e}")
                    continue
            
            if font_registered:
                break
        
        # Hiçbir font bulunamazsa Helvetica kullan (Türkçe karakterler görünmeyebilir)
        if not font_registered:
            self.font_family = "Helvetica"
            logger.warning("Türkçe karakter desteği için font bulunamadı. Helvetica kullanılıyor (Türkçe karakterler görünmeyebilir).")

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
        font_bold = self._get_font_name('bold')
        c.setFillColor(HexColor(self.template.text_color))
        company_name = self.shipment.cargo_company.display_name
        self._draw_text_safe(c, company_name, x + 5*mm, y, font_bold, self.template.font_size_large)
        return y - 8*mm

    def draw_tracking_info(self, c, x, y):
        """Takip bilgilerini çiz"""
        # Takip numarası
        font_bold = self._get_font_name('bold')
        c.setFont(font_bold, self.template.font_size_medium)
        tracking_text = f"Takip No: {self.shipment.tracking_number or 'Oluşturuluyor'}"
        self._draw_text_safe(c, tracking_text, x + 5*mm, y, font_bold, self.template.font_size_medium)
        y = y - 4*mm

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
        font_reg = self._get_font_name('regular')
        font_bold = self._get_font_name('bold')

        # Gönderen bilgilerini güncel modelden al (işitme merkezi veya üretici ise)
        sender_name = self.shipment.sender_name
        sender_address = self.shipment.sender_address
        sender_phone = self.shipment.sender_phone
        
        # Eğer gönderen bir işitme merkezi ise, güncel bilgilerini al
        try:
            from center.models import Center
            center = Center.objects.filter(name__iexact=sender_name.strip()).first()
            if not center:
                center = Center.objects.filter(name__icontains=sender_name.strip()).first()
            if center:
                # Güncel adres ve telefon bilgilerini kullan
                sender_address = center.address if center.address else sender_address
                sender_phone = center.phone if center.phone else sender_phone
                sender_name = center.name  # Adı da güncel olsun
        except:
            pass
        
        # Eğer gönderen bir üretici merkezi ise, güncel bilgilerini al
        try:
            from producer.models import Producer
            producer = Producer.objects.filter(company_name__iexact=sender_name.strip()).first()
            if not producer:
                producer = Producer.objects.filter(company_name__icontains=sender_name.strip()).first()
            if producer:
                # Güncel adres ve telefon bilgilerini kullan
                sender_address = producer.address if producer.address else sender_address
                sender_phone = producer.phone if producer.phone else sender_phone
                sender_name = producer.company_name  # Adı da güncel olsun
        except:
            pass

        c.setFont(font_reg, self.template.font_size_small)
        self._draw_text_safe(c, "GÖNDEREN:", x + 5*mm, y, font_reg, self.template.font_size_small)
        y -= 4*mm

        c.setFont(font_bold, self.template.font_size_small)
        self._draw_text_safe(c, sender_name, x + 5*mm, y, font_bold, self.template.font_size_small)
        y -= 3*mm

        # Adresi bölerek yaz
        if len(sender_address) > 30:
            lines = [sender_address[i:i+30] for i in range(0, len(sender_address), 30)]
            for line in lines[:2]:  # Maksimum 2 satır
                self._draw_text_safe(c, line, x + 5*mm, y, font_reg, self.template.font_size_small)
                y -= 3*mm
        else:
            self._draw_text_safe(c, sender_address, x + 5*mm, y, font_reg, self.template.font_size_small)
            y -= 3*mm

        self._draw_text_safe(c, sender_phone, x + 5*mm, y, font_reg, self.template.font_size_small)
        return y - 8*mm

    def draw_recipient_info(self, c, x, y):
        """Alıcı bilgilerini çiz"""
        font_reg = self._get_font_name('regular')
        font_bold = self._get_font_name('bold')

        # Alıcı bilgilerini güncel modelden al (işitme merkezi veya üretici ise)
        recipient_name = self.shipment.recipient_name
        recipient_address = self.shipment.recipient_address
        recipient_phone = self.shipment.recipient_phone
        
        # Eğer alıcı bir işitme merkezi ise, güncel bilgilerini al
        try:
            from center.models import Center
            center = Center.objects.filter(name__iexact=recipient_name.strip()).first()
            if not center:
                center = Center.objects.filter(name__icontains=recipient_name.strip()).first()
            if center:
                # Güncel adres ve telefon bilgilerini kullan
                recipient_address = center.address if center.address else recipient_address
                recipient_phone = center.phone if center.phone else recipient_phone
                recipient_name = center.name  # Adı da güncel olsun
        except:
            pass
        
        # Eğer alıcı bir üretici merkezi ise, güncel bilgilerini al
        try:
            from producer.models import Producer
            producer = Producer.objects.filter(company_name__iexact=recipient_name.strip()).first()
            if not producer:
                producer = Producer.objects.filter(company_name__icontains=recipient_name.strip()).first()
            if producer:
                # Güncel adres ve telefon bilgilerini kullan
                recipient_address = producer.address if producer.address else recipient_address
                recipient_phone = producer.phone if producer.phone else recipient_phone
                recipient_name = producer.company_name  # Adı da güncel olsun
        except:
            pass

        c.setFont(font_reg, self.template.font_size_small)
        self._draw_text_safe(c, "ALICI:", x + 5*mm, y, font_reg, self.template.font_size_small)
        y -= 4*mm

        c.setFont(font_bold, self.template.font_size_small)
        self._draw_text_safe(c, recipient_name, x + 5*mm, y, font_bold, self.template.font_size_small)
        y -= 3*mm

        # Adresi bölerek yaz
        if len(recipient_address) > 30:
            lines = [recipient_address[i:i+30] for i in range(0, len(recipient_address), 30)]
            for line in lines[:2]:  # Maksimum 2 satır
                self._draw_text_safe(c, line, x + 5*mm, y, font_reg, self.template.font_size_small)
                y -= 3*mm
        else:
            self._draw_text_safe(c, recipient_address, x + 5*mm, y, font_reg, self.template.font_size_small)
            y -= 3*mm

        self._draw_text_safe(c, recipient_phone, x + 5*mm, y, font_reg, self.template.font_size_small)
        return y - 8*mm

    def draw_package_info(self, c, x, y):
        """Paket bilgilerini çiz"""
        font_reg = self._get_font_name('regular')
        c.setFont(font_reg, self.template.font_size_small)
        self._draw_text_safe(c, f"Ağırlık: {self.shipment.weight_kg} kg", x + 5*mm, y, font_reg, self.template.font_size_small)
        y -= 3*mm
        self._draw_text_safe(c, f"Paket: {self.shipment.package_count} adet", x + 5*mm, y, font_reg, self.template.font_size_small)
        y -= 3*mm

        if self.shipment.description:
            desc_text = f"İçerik: {self.shipment.description[:40]}"
            self._draw_text_safe(c, desc_text, x + 5*mm, y, font_reg, self.template.font_size_small)

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
            # Alıcı bilgilerini güncel modelden al (işitme merkezi veya üretici ise)
            recipient_name = self.shipment.recipient_name
            
            # Eğer alıcı bir işitme merkezi ise, güncel adını al
            try:
                from center.models import Center
                center = Center.objects.filter(name__iexact=recipient_name.strip()).first()
                if not center:
                    center = Center.objects.filter(name__icontains=recipient_name.strip()).first()
                if center:
                    recipient_name = center.name
            except:
                pass
            
            # Eğer alıcı bir üretici merkezi ise, güncel adını al
            try:
                from producer.models import Producer
                producer = Producer.objects.filter(company_name__iexact=recipient_name.strip()).first()
                if not producer:
                    producer = Producer.objects.filter(company_name__icontains=recipient_name.strip()).first()
                if producer:
                    recipient_name = producer.company_name
            except:
                pass
            
            # QR kod verisi
            qr_data = f"""
Gönderi Takip: {self.shipment.tracking_number}
Firma: {self.shipment.cargo_company.display_name}
Alıcı: {recipient_name}
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

        # Alıcı bilgilerini güncel modelden al (işitme merkezi veya üretici ise)
        recipient_name = self.shipment.recipient_name
        recipient_address = self.shipment.recipient_address
        recipient_phone = self.shipment.recipient_phone
        
        # Eğer alıcı bir işitme merkezi ise, güncel bilgilerini al
        try:
            from center.models import Center
            center = Center.objects.filter(name__iexact=recipient_name.strip()).first()
            if not center:
                center = Center.objects.filter(name__icontains=recipient_name.strip()).first()
            if center:
                # Güncel adres ve telefon bilgilerini kullan
                recipient_address = center.address if center.address else recipient_address
                recipient_phone = center.phone if center.phone else recipient_phone
                recipient_name = center.name  # Adı da güncel olsun
        except:
            pass
        
        # Eğer alıcı bir üretici merkezi ise, güncel bilgilerini al
        try:
            from producer.models import Producer
            producer = Producer.objects.filter(company_name__iexact=recipient_name.strip()).first()
            if not producer:
                producer = Producer.objects.filter(company_name__icontains=recipient_name.strip()).first()
            if producer:
                # Güncel adres ve telefon bilgilerini kullan
                recipient_address = producer.address if producer.address else recipient_address
                recipient_phone = producer.phone if producer.phone else recipient_phone
                recipient_name = producer.company_name  # Adı da güncel olsun
        except:
            pass

        # Gönderen bilgilerini güncel modelden al (işitme merkezi veya üretici ise)
        sender_name = self.shipment.sender_name
        sender_address = self.shipment.sender_address
        sender_phone = self.shipment.sender_phone
        
        # Eğer gönderen bir işitme merkezi ise, güncel bilgilerini al
        try:
            from center.models import Center
            center = Center.objects.filter(name__iexact=sender_name.strip()).first()
            if not center:
                center = Center.objects.filter(name__icontains=sender_name.strip()).first()
            if center:
                # Güncel adres ve telefon bilgilerini kullan
                sender_address = center.address if center.address else sender_address
                sender_phone = center.phone if center.phone else sender_phone
                sender_name = center.name  # Adı da güncel olsun
        except:
            pass
        
        # Eğer gönderen bir üretici merkezi ise, güncel bilgilerini al
        try:
            from producer.models import Producer
            producer = Producer.objects.filter(company_name__iexact=sender_name.strip()).first()
            if not producer:
                producer = Producer.objects.filter(company_name__icontains=sender_name.strip()).first()
            if producer:
                # Güncel adres ve telefon bilgilerini kullan
                sender_address = producer.address if producer.address else sender_address
                sender_phone = producer.phone if producer.phone else sender_phone
                sender_name = producer.company_name  # Adı da güncel olsun
        except:
            pass

        # Basit text tabanlı termal etiket
        content = f"""
{self.shipment.cargo_company.display_name}
Takip No: {self.shipment.tracking_number}

GÖNDEREN:
{sender_name}
{sender_address}
{sender_phone}

ALICI:
{recipient_name}
{recipient_address}
{recipient_phone}

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

