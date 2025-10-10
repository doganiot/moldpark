from django.core.management.base import BaseCommand
from producer.models import Producer

class Command(BaseCommand):
    help = 'MoldPark üreticisinin siparişlerini detaylı gösterir'

    def handle(self, *args, **options):
        self.stdout.write('=== MOLDPARK ÜRETİCİ SİPARİŞ ANALİZİ ===\n')

        try:
            producer = Producer.objects.get(company_name__icontains='moldpark')
            self.stdout.write(self.style.SUCCESS(f'Üretici: {producer.company_name}'))

            # Tüm siparişleri listele
            orders = producer.orders.all()
            self.stdout.write(f'Toplam sipariş sayısı: {orders.count()}')

            nebi_orders = 0
            for order in orders:
                center_name = order.center.name if order.center else "Bilinmiyor"
                if 'nebi' in center_name.lower() or 'nebi' in order.center.user.username.lower():
                    nebi_orders += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'  Nebi Siparişi: {order.order_number} - {order.ear_mold.patient_name} {order.ear_mold.patient_surname}'
                    ))
                    self.stdout.write(f'    Durum: {order.status}')
                    self.stdout.write(f'    Fiziksel: {order.ear_mold.is_physical_shipment}')
                    self.stdout.write(f'    Tutar: {"450 TL" if order.ear_mold.is_physical_shipment else "50 TL"}')
                    self.stdout.write('')

            if nebi_orders == 0:
                self.stdout.write(self.style.WARNING('Nebi\'den hiç sipariş bulunamadı!'))

            # Tüm siparişlerin durum dağılımı
            self.stdout.write('\n=== SİPARİŞ DURUM DAĞILIMI ===')
            status_counts = {}
            for order in orders:
                status = order.status
                if status not in status_counts:
                    status_counts[status] = 0
                status_counts[status] += 1

            for status, count in status_counts.items():
                self.stdout.write(f'{status}: {count}')

        except Producer.DoesNotExist:
            self.stdout.write(self.style.ERROR('MoldPark üreticisi bulunamadı'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Hata: {e}'))
