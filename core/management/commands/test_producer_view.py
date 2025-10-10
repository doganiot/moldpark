from django.core.management.base import BaseCommand
from django.test import RequestFactory
from producer.views import order_list
from producer.models import Producer
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Producer order_list view\'ını test eder'

    def handle(self, *args, **options):
        self.stdout.write('=== PRODUCER ORDER_LIST VIEW TEST ===\n')

        try:
            # MoldPark producer'ını bul
            producer = Producer.objects.get(company_name__icontains='moldpark')
            user = producer.user

            self.stdout.write(f'Producer: {producer.company_name}')
            self.stdout.write(f'User: {user.username}')

            # Request factory ile view'ı test et
            factory = RequestFactory()
            request = factory.get('/producer/orders/')
            request.user = user

            # View'ı çağır
            response = order_list(request)

            # Context'ten orders'ı al
            if hasattr(response, 'context_data'):
                orders = response.context_data.get('orders', [])
            else:
                # Response direkt olarak render edilmiş olabilir
                self.stdout.write('Response type: direct render')
                orders = producer.orders.all()

            self.stdout.write(f'View\'dan dönen sipariş sayısı: {len(orders) if hasattr(orders, "__len__") else "N/A"}')

            # Manuel olarak producer.orders.all() ile karşılaştır
            all_orders = producer.orders.all()
            self.stdout.write(f'Manuel producer.orders.all() sayısı: {all_orders.count()}')

            for order in all_orders:
                center_name = order.center.name if order.center else "Bilinmiyor"
                if 'nebi' in center_name.lower() or 'nebi' in order.center.user.username.lower():
                    self.stdout.write(self.style.SUCCESS(
                        f'  Nebi Siparişi: {order.order_number} - {order.ear_mold.patient_name} {order.ear_mold.patient_surname} - Durum: {order.status}'
                    ))

        except Producer.DoesNotExist:
            self.stdout.write(self.style.ERROR('MoldPark üreticisi bulunamadı'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Hata: {e}'))
            import traceback
            traceback.print_exc()
