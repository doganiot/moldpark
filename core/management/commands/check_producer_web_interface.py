from django.core.management.base import BaseCommand
from producer.models import Producer, ProducerOrder
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Producer web arayüzünde Nebi siparişlerinin görünürlüğünü test eder'

    def handle(self, *args, **options):
        self.stdout.write('=== PRODUCER WEB ARAYÜZ TEST ===\n')

        # Tüm producer hesaplarını kontrol et
        producers = Producer.objects.all()
        for producer in producers:
            self.stdout.write(f'\n--- Producer: {producer.company_name} ({producer.user.username}) ---')

            # Bu producer'ın siparişleri
            orders = producer.orders.all()
            self.stdout.write(f'Toplam sipariş: {orders.count()}')

            nebi_count = 0
            for order in orders:
                center_name = order.center.name if order.center else "Bilinmiyor"
                center_user = order.center.user.username if order.center else "Bilinmiyor"

                if 'nebi' in center_name.lower() or 'nebi' in center_user.lower():
                    nebi_count += 1
                    self.stdout.write(f'  [OK] Nebi siparişi: {order.order_number} - {order.ear_mold.patient_name} {order.ear_mold.patient_surname}')

            if nebi_count == 0:
                self.stdout.write('  [X] Nebi siparişi bulunamadı')
            else:
                self.stdout.write(f'  Toplam Nebi siparişi: {nebi_count}')

        # Genel özet
        self.stdout.write('\n=== GENEL ÖZET ===')
        total_nebi_orders = ProducerOrder.objects.filter(
            center__user__username__icontains='nebi'
        ).count()
        self.stdout.write(f'Veritabanında toplam Nebi siparişi: {total_nebi_orders}')

        assigned_nebi_orders = ProducerOrder.objects.filter(
            center__user__username__icontains='nebi',
            producer__isnull=False
        ).count()
        self.stdout.write(f'Atanmış Nebi siparişi: {assigned_nebi_orders}')

        unassigned_nebi_orders = ProducerOrder.objects.filter(
            center__user__username__icontains='nebi',
            producer__isnull=True
        ).count()
        self.stdout.write(f'Atanmamış Nebi siparişi: {unassigned_nebi_orders}')
