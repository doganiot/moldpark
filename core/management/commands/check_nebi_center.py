from django.core.management.base import BaseCommand
from center.models import Center
from mold.models import EarMold
from producer.models import ProducerOrder, ProducerNetwork

class Command(BaseCommand):
    help = 'Nebi center\'ının durumunu kontrol eder'

    def handle(self, *args, **options):
        self.stdout.write('=== NEBI CENTER ANALIZI ===\n')

        # Nebi center'ını bul
        centers = Center.objects.filter(user__username__icontains='nebi')
        if not centers:
            self.stdout.write(self.style.ERROR('Nebi center bulunamadı'))
            return

        for c in centers:
            self.stdout.write(self.style.SUCCESS(f'Center: {c.name}, User: {c.user.username}'))

            # Bu center'ın kalıplarını kontrol et
            molds = EarMold.objects.filter(center=c)
            self.stdout.write(f'Kalıp sayısı: {molds.count()}')

            physical_count = 0
            digital_count = 0
            total_amount = 0

            for mold in molds:
                if mold.is_physical_shipment:
                    physical_count += 1
                    total_amount += 450  # Fiziksel kalıp ücreti
                else:
                    digital_count += 1
                    total_amount += 50  # 3D modelleme ücreti

                self.stdout.write(f'  Kalıp: {mold.patient_name} {mold.patient_surname}')
                self.stdout.write(f'    Durum: {mold.status}')
                self.stdout.write(f'    Fiziksel: {mold.is_physical_shipment}')

                # Bu kalıp için order var mı?
                orders = ProducerOrder.objects.filter(ear_mold=mold)
                if orders:
                    for order in orders:
                        self.stdout.write(f'    Sipariş: {order.order_number}, Durum: {order.status}')
                        self.stdout.write(f'    Üretici: {order.producer.company_name if order.producer else "Atanmamış"}')
                        if not order.producer:
                            self.stdout.write(self.style.WARNING('    *** UYARI: Siparişe üretici atanmamış! ***'))
                else:
                    self.stdout.write(self.style.WARNING(f'    *** UYARI: Sipariş yok! ***'))

            self.stdout.write(f'Toplam: {physical_count} fiziksel, {digital_count} dijital')
            self.stdout.write(f'Tahmini Tutar: {total_amount} TL')

            # Network bağlantıları
            networks = ProducerNetwork.objects.filter(center=c)
            self.stdout.write(f'Network bağlantısı: {networks.count()}')
            for n in networks:
                self.stdout.write(f'  Network: {n.status}, Üretici: {n.producer.company_name}')
                if n.status != 'active':
                    self.stdout.write(self.style.WARNING('  *** UYARI: Network aktif değil! ***'))

            if not networks:
                self.stdout.write(self.style.ERROR('*** KRITIK: Hiç network bağlantısı yok! ***'))
