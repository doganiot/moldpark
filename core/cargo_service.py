"""
Türkiye Kargo Firmaları API Entegrasyonları
Türkiye'nin önde gelen kargo firmalarının API servisleri
"""
import requests
import json
import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import CargoCompany, CargoShipment, CargoTracking

logger = logging.getLogger(__name__)


class BaseCargoService:
    """Temel kargo servisi sınıfı"""

    def __init__(self, company):
        self.company = company
        self.api_key = company.api_key
        self.api_secret = company.api_secret
        self.base_url = company.api_base_url
        self.test_mode = getattr(company, 'integration', None) and company.integration.test_mode

    def make_request(self, endpoint, method='GET', data=None, headers=None):
        """API isteği gönder"""
        try:
            url = f"{self.base_url}{endpoint}"
            default_headers = {'Content-Type': 'application/json'}

            if headers:
                default_headers.update(headers)

            if self.test_mode:
                logger.info(f"[TEST MODE] {method} {url} - Data: {data}")

            response = requests.request(
                method=method,
                url=url,
                json=data,
                headers=default_headers,
                timeout=30
            )

            if self.test_mode:
                logger.info(f"[TEST MODE] Response: {response.status_code} - {response.text}")

            return response.json() if response.content else {}

        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return {'error': str(e)}

    def create_shipment(self, shipment_data):
        """Yeni gönderi oluştur"""
        raise NotImplementedError("create_shipment must be implemented")

    def track_shipment(self, tracking_number):
        """Gönderi takibi"""
        raise NotImplementedError("track_shipment must be implemented")

    def cancel_shipment(self, tracking_number):
        """Gönderi iptali"""
        raise NotImplementedError("cancel_shipment must be implemented")


class ArasCargoService(BaseCargoService):
    """Aras Kargo API Entegrasyonu"""

    def create_shipment(self, shipment_data):
        """Aras Kargo gönderi oluşturma"""
        # Aras Kargo API dokümantasyonu'na göre
        payload = {
            "apiKey": self.api_key,
            "sender": {
                "name": shipment_data['sender_name'],
                "address": shipment_data['sender_address'],
                "phone": shipment_data['sender_phone']
            },
            "receiver": {
                "name": shipment_data['recipient_name'],
                "address": shipment_data['recipient_address'],
                "phone": shipment_data['recipient_phone']
            },
            "package": {
                "weight": float(shipment_data['weight_kg']),
                "count": shipment_data['package_count'],
                "description": shipment_data.get('description', '')
            }
        }

        response = self.make_request('/create-shipment', 'POST', payload)
        return response

    def track_shipment(self, tracking_number):
        """Aras Kargo takip"""
        payload = {
            "apiKey": self.api_key,
            "trackingNumber": tracking_number
        }

        response = self.make_request('/track', 'POST', payload)
        return response

    def cancel_shipment(self, tracking_number):
        """Aras Kargo iptal"""
        payload = {
            "apiKey": self.api_key,
            "trackingNumber": tracking_number
        }

        response = self.make_request('/cancel', 'POST', payload)
        return response


class MNGKargoService(BaseCargoService):
    """MNG Kargo API Entegrasyonu"""

    def create_shipment(self, shipment_data):
        """MNG Kargo gönderi oluşturma"""
        payload = {
            "username": self.api_key,
            "password": self.api_secret,
            "senderName": shipment_data['sender_name'],
            "senderAddress": shipment_data['sender_address'],
            "senderPhone": shipment_data['sender_phone'],
            "receiverName": shipment_data['recipient_name'],
            "receiverAddress": shipment_data['recipient_address'],
            "receiverPhone": shipment_data['recipient_phone'],
            "weight": float(shipment_data['weight_kg']),
            "pieceCount": shipment_data['package_count']
        }

        response = self.make_request('/CreateShipment', 'POST', payload)
        return response

    def track_shipment(self, tracking_number):
        """MNG Kargo takip"""
        payload = {
            "username": self.api_key,
            "password": self.api_secret,
            "trackingNumber": tracking_number
        }

        response = self.make_request('/QueryShipment', 'POST', payload)
        return response


class YurticiKargoService(BaseCargoService):
    """Yurtiçi Kargo API Entegrasyonu"""

    def create_shipment(self, shipment_data):
        """Yurtiçi Kargo gönderi oluşturma"""
        payload = {
            "cargoKey": self.api_key,
            "invoiceKey": self.api_secret,
            "receiverCustName": shipment_data['recipient_name'],
            "receiverAddress": shipment_data['recipient_address'],
            "receiverPhone1": shipment_data['recipient_phone'],
            "senderCustName": shipment_data['sender_name'],
            "senderAddress": shipment_data['sender_address'],
            "senderPhone1": shipment_data['sender_phone'],
            "kg": float(shipment_data['weight_kg']),
            "desi": 1,  # Varsayılan
            "cargoCount": shipment_data['package_count']
        }

        headers = {'Authorization': f'Bearer {self.api_key}'}
        response = self.make_request('/createShipment', 'POST', payload, headers)
        return response

    def track_shipment(self, tracking_number):
        """Yurtiçi Kargo takip"""
        payload = {"trackingNumber": tracking_number}
        headers = {'Authorization': f'Bearer {self.api_key}'}

        response = self.make_request('/queryShipment', 'POST', payload, headers)
        return response


class CargoServiceFactory:
    """Kargo servisi factory sınıfı"""

    @staticmethod
    def get_service(company_name, company):
        """Firma adına göre uygun servisi döndür"""
        services = {
            'aras': ArasCargoService,
            'mng': MNGKargoService,
            'yurtici': YurticiKargoService,
        }

        service_class = services.get(company_name)
        if service_class:
            return service_class(company)
        else:
            # Desteklenmeyen firma için temel servis
            return BaseCargoService(company)


class CargoManager:
    """Kargo işlemleri yöneticisi"""

    @staticmethod
    def create_shipment(invoice, cargo_company, shipment_data):
        """
        Yeni kargo gönderisi oluştur

        Args:
            invoice: Invoice instance
            cargo_company: CargoCompany instance
            shipment_data: dict - Gönderi bilgileri

        Returns:
            dict: Oluşturma sonucu
        """
        try:
            # Servis oluştur
            service = CargoServiceFactory.get_service(cargo_company.name, cargo_company)

            # Gönderi oluştur
            api_result = service.create_shipment(shipment_data)

            if api_result.get('success') or not api_result.get('error'):
                # Veritabanına kaydet
                shipment = CargoShipment.objects.create(
                    invoice=invoice,
                    cargo_company=cargo_company,
                    tracking_number=api_result.get('trackingNumber', ''),
                    sender_name=shipment_data['sender_name'],
                    sender_address=shipment_data['sender_address'],
                    sender_phone=shipment_data['sender_phone'],
                    recipient_name=shipment_data['recipient_name'],
                    recipient_address=shipment_data['recipient_address'],
                    recipient_phone=shipment_data['recipient_phone'],
                    weight_kg=shipment_data['weight_kg'],
                    package_count=shipment_data['package_count'],
                    description=shipment_data.get('description', ''),
                    shipping_cost=cargo_company.base_price + (Decimal(str(shipment_data['weight_kg'])) * cargo_company.kg_price),
                    status='pending',
                    api_response=api_result
                )

                # İlk takip kaydı
                CargoTracking.objects.create(
                    shipment=shipment,
                    status='pending',
                    description='Gönderi oluşturuldu',
                    raw_data=api_result
                )

                return {
                    'success': True,
                    'shipment': shipment,
                    'tracking_number': shipment.tracking_number
                }
            else:
                return {
                    'success': False,
                    'error': api_result.get('error', 'Gönderi oluşturulamadı')
                }

        except Exception as e:
            logger.error(f"Kargo gönderi oluşturma hatası: {str(e)}")
            return {
                'success': False,
                'error': f'Bir hata oluştu: {str(e)}'
            }

    @staticmethod
    def track_shipment(shipment):
        """
        Gönderi takibi güncelle

        Args:
            shipment: CargoShipment instance

        Returns:
            dict: Takip sonucu
        """
        try:
            service = CargoServiceFactory.get_service(shipment.cargo_company.name, shipment.cargo_company)

            if not shipment.tracking_number:
                return {'success': False, 'error': 'Takip numarası bulunamadı'}

            api_result = service.track_shipment(shipment.tracking_number)

            if api_result.get('success') or not api_result.get('error'):
                # Durum güncellemeleri
                status_mapping = {
                    'Hazırlanıyor': 'pending',
                    'Alındı': 'picked_up',
                    'Yolda': 'in_transit',
                    'Dağıtıma Çıktı': 'out_for_delivery',
                    'Teslim Edildi': 'delivered',
                    'İade Edildi': 'returned',
                    'İptal Edildi': 'cancelled',
                    'Teslim Edilemedi': 'failed'
                }

                new_status = status_mapping.get(api_result.get('status'), shipment.status)

                # Takip geçmişi ekle
                if api_result.get('trackingHistory'):
                    for track_item in api_result['trackingHistory']:
                        CargoTracking.objects.get_or_create(
                            shipment=shipment,
                            status=new_status,
                            description=track_item.get('description', ''),
                            location=track_item.get('location', ''),
                            timestamp=track_item.get('timestamp', timezone.now()),
                            defaults={'raw_data': track_item}
                        )

                # Gönderi durumunu güncelle
                shipment.update_status(
                    new_status,
                    api_result.get('description', ''),
                    api_result
                )

                return {
                    'success': True,
                    'status': new_status,
                    'description': api_result.get('description', '')
                }
            else:
                return {
                    'success': False,
                    'error': api_result.get('error', 'Takip bilgisi alınamadı')
                }

        except Exception as e:
            logger.error(f"Kargo takip hatası: {str(e)}")
            return {
                'success': False,
                'error': f'Takip hatası: {str(e)}'
            }

    @staticmethod
    def get_cargo_companies():
        """Aktif kargo firmalarını döndür"""
        return CargoCompany.objects.filter(is_active=True)

    @staticmethod
    def calculate_shipping_cost(company, weight_kg):
        """Kargo maliyetini hesapla"""
        return company.base_price + (Decimal(str(weight_kg)) * company.kg_price)

    @staticmethod
    def get_default_company():
        """Varsayılan kargo firmasını döndür"""
        return CargoCompany.objects.filter(is_active=True, is_default=True).first()

    @staticmethod
    def initialize_default_companies():
        """Varsayılan kargo firmalarını oluştur"""
        default_companies = [
            {
                'name': 'aras',
                'display_name': 'Aras Kargo',
                'website': 'https://www.araskargo.com.tr',
                'base_price': 25.00,
                'kg_price': 5.00,
                'estimated_delivery_days': 1,
                'is_default': True
            },
            {
                'name': 'mng',
                'display_name': 'MNG Kargo',
                'website': 'https://www.mngkargo.com.tr',
                'base_price': 20.00,
                'kg_price': 4.50,
                'estimated_delivery_days': 1,
            },
            {
                'name': 'yurtici',
                'display_name': 'Yurtiçi Kargo',
                'website': 'https://www.yurticikargo.com.tr',
                'base_price': 22.00,
                'kg_price': 4.80,
                'estimated_delivery_days': 1,
            },
            {
                'name': 'ptt',
                'display_name': 'PTT Kargo',
                'website': 'https://www.ptt.gov.tr',
                'base_price': 18.00,
                'kg_price': 4.00,
                'estimated_delivery_days': 2,
            }
        ]

        for company_data in default_companies:
            CargoCompany.objects.get_or_create(
                name=company_data['name'],
                defaults=company_data
            )
