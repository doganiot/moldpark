"""
İyzico Ödeme Gateway Entegrasyonu
Türkiye'de geçerli test ödeme alt yapısı
"""
import json
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from iyzipay import CheckoutFormInitialize, Payment
import logging

logger = logging.getLogger(__name__)


class IyzicoPaymentService:
    """İyzico ödeme servisi - Test ve Production modları"""
    
    def __init__(self):
        # İyzico API yapılandırması
        self.api_key = getattr(settings, 'IYZICO_API_KEY', 'sandbox-xxx')
        self.secret_key = getattr(settings, 'IYZICO_SECRET_KEY', 'sandbox-xxx')
        base_url = getattr(settings, 'IYZICO_BASE_URL', 'https://sandbox-api.iyzipay.com')
        # URL'den sonundaki slash'ı temizle
        base_url = base_url.rstrip('/')
        # İyzico SDK HTTPSConnection kullanıyor, bu yüzden sadece hostname gerekli
        # URL'den scheme'i kaldır (https:// veya http://)
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        # Eğer scheme varsa sadece hostname'i al, yoksa direkt kullan
        if parsed.netloc:
            self.base_url = parsed.netloc
        else:
            # Scheme yoksa direkt kullan (zaten hostname)
            self.base_url = base_url
        self.is_test_mode = getattr(settings, 'IYZICO_TEST_MODE', True)
        
        # API anahtarlarını kontrol et
        if self.api_key == 'sandbox-xxx' or self.secret_key == 'sandbox-xxx' or not self.api_key or not self.secret_key:
            raise ValueError(
                "İyzico API anahtarları yapılandırılmamış. "
                "Lütfen .env dosyasına IYZICO_API_KEY ve IYZICO_SECRET_KEY ekleyin. "
                "Test API anahtarları için: https://dev.iyzipay.com/tr"
            )
        
        # İyzico API istemcisi - İyzico SDK'nın beklediği format
        self.options = {
            'api_key': self.api_key,
            'secret_key': self.secret_key,
            'base_url': self.base_url
        }
    
    def create_payment_request(self, invoice, user, request):
        """
        İyzico ödeme isteği oluştur
        
        Args:
            invoice: Invoice model instance
            user: User model instance
            request: Django request object
            
        Returns:
            dict: Ödeme formu HTML ve iyzico response
        """
        try:
            # İyzico ödeme isteği için dictionary oluştur
            payment_request = {
                'locale': 'tr',
                'conversationId': f"INV-{invoice.id}-{int(timezone.now().timestamp())}",
                'price': str(invoice.total_amount),
                'paidPrice': str(invoice.total_amount),
                'currency': 'TRY',
                'basketId': f"BASKET-{invoice.id}",
                'paymentChannel': 'WEB',
                'paymentGroup': 'PRODUCT',
                'callbackUrl': request.build_absolute_uri(f'/payment/iyzico/callback/{invoice.id}/'),
                'buyer': {
                    'id': str(user.id),
                    'name': user.first_name or 'İsim',
                    'surname': user.last_name or 'Soyisim',
                    'gsmNumber': '5555555555',
                    'email': user.email,
                    'identityNumber': '11111111111',  # Test için
                    'lastLoginDate': str(timezone.now().date()),
                    'registrationDate': str(user.date_joined.date()),
                    'registrationAddress': 'Test Adres',
                    'ip': request.META.get('REMOTE_ADDR', '127.0.0.1'),
                    'city': 'Istanbul',
                    'country': 'Turkey',
                    'zipCode': '34000'
                },
                'billingAddress': {
                    'contactName': f"{user.first_name} {user.last_name}",
                    'city': 'Istanbul',
                    'country': 'Turkey',
                    'address': 'Test Adres',
                    'zipCode': '34000'
                },
                'shippingAddress': {
                    'contactName': f"{user.first_name} {user.last_name}",
                    'city': 'Istanbul',
                    'country': 'Turkey',
                    'address': 'Test Adres',
                    'zipCode': '34000'
                },
                'basketItems': []
            }
            
            # Sepet öğeleri ekle
            # Fiziksel kalıp varsa
            if invoice.physical_mold_count and invoice.physical_mold_count > 0:
                payment_request['basketItems'].append({
                    'id': f"PHYSICAL-{invoice.id}",
                    'name': 'Fiziksel Kalıp Hizmeti',
                    'category1': 'İşitme Cihazı',
                    'category2': 'Kalıp Üretimi',
                    'itemType': 'PHYSICAL',
                    'price': str(invoice.physical_mold_cost or Decimal('0.00'))
                })
            
            # Dijital modelleme varsa
            if invoice.digital_scan_count and invoice.digital_scan_count > 0:
                payment_request['basketItems'].append({
                    'id': f"DIGITAL-{invoice.id}",
                    'name': '3D Modelleme Hizmeti',
                    'category1': 'İşitme Cihazı',
                    'category2': 'Dijital Modelleme',
                    'itemType': 'VIRTUAL',
                    'price': str(invoice.digital_scan_cost or Decimal('0.00'))
                })
            
            # Aylık sistem ücreti varsa
            if invoice.monthly_fee and invoice.monthly_fee > 0:
                payment_request['basketItems'].append({
                    'id': f"MONTHLY-{invoice.id}",
                    'name': 'Aylık Sistem Kullanım Ücreti',
                    'category1': 'Abonelik',
                    'category2': 'Sistem Ücreti',
                    'itemType': 'VIRTUAL',
                    'price': str(invoice.monthly_fee)
                })
            
            # Ödeme formu oluştur
            checkout_form = CheckoutFormInitialize()
            checkout_form_initialize = checkout_form.create(payment_request, self.options)
            
            # Response'u parse et
            response_dict = json.loads(checkout_form_initialize.read().decode('utf-8'))
            
            if response_dict.get('status') == 'success':
                return {
                    'success': True,
                    'checkout_form_content': response_dict.get('checkoutFormContent', ''),
                    'payment_page_url': response_dict.get('paymentPageUrl', ''),
                    'conversation_id': payment_request['conversationId'],
                }
            else:
                error_message = response_dict.get('errorMessage', 'Ödeme formu oluşturulamadı')
                logger.error(f"İyzico ödeme formu oluşturulamadı: {error_message}")
                return {
                    'success': False,
                    'error_message': error_message
                }
                
        except Exception as e:
            logger.error(f"İyzico ödeme hatası: {str(e)}")
            return {
                'success': False,
                'error_message': f'Ödeme işlemi sırasında hata oluştu: {str(e)}'
            }
    
    def verify_payment(self, token, invoice):
        """
        İyzico ödeme doğrulama
        
        Args:
            token: İyzico payment token
            invoice: Invoice model instance
            
        Returns:
            dict: Ödeme doğrulama sonucu
        """
        try:
            payment_request = {
                'locale': 'tr',
                'conversationId': f"INV-{invoice.id}",
                'token': token
            }
            
            payment = Payment()
            payment_result = payment.retrieve(payment_request, self.options)
            
            # Response'u parse et
            response_dict = json.loads(payment_result.read().decode('utf-8'))
            
            if response_dict.get('status') == 'success':
                return {
                    'success': True,
                    'payment_id': response_dict.get('paymentId', ''),
                    'fraud_status': response_dict.get('fraudStatus', 0),
                    'payment_status': response_dict.get('paymentStatus', ''),
                    'paid_price': response_dict.get('paidPrice', '0'),
                    'currency': response_dict.get('currency', 'TRY'),
                    'conversation_id': response_dict.get('conversationId', ''),
                    'raw_response': response_dict,
                }
            else:
                return {
                    'success': False,
                    'error_message': response_dict.get('errorMessage', 'Ödeme doğrulanamadı'),
                    'raw_response': response_dict,
                }
                
        except Exception as e:
            logger.error(f"İyzico ödeme doğrulama hatası: {str(e)}")
            return {
                'success': False,
                'error_message': f'Ödeme doğrulama sırasında hata oluştu: {str(e)}'
            }

