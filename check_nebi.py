#!/usr/bin/env python
import os
import django

# Django ayarlarını yükle
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from center.models import Center
from mold.models import EarMold
from producer.models import ProducerOrder, ProducerNetwork

print('=== NEBI CENTER ANALIZI ===')

# Nebi center'ını bul
centers = Center.objects.filter(user__username__icontains='nebi')
if not centers:
    print('Nebi center bulunamadı')
    exit()

for c in centers:
    print(f'Center: {c.name}, User: {c.user.username}')

    # Bu center'ın kalıplarını kontrol et
    molds = EarMold.objects.filter(center=c)
    print(f'Kalıp sayısı: {molds.count()}')

    physical_count = 0
    digital_count = 0

    for mold in molds:
        if mold.is_physical_shipment:
            physical_count += 1
        else:
            digital_count += 1

        print(f'  Kalıp: {mold.patient_name} {mold.patient_surname}')
        print(f'    Durum: {mold.status}')
        print(f'    Fiziksel: {mold.is_physical_shipment}')

        # Bu kalıp için order var mı?
        orders = ProducerOrder.objects.filter(ear_mold=mold)
        if orders:
            for order in orders:
                print(f'    Sipariş: {order.order_number}, Durum: {order.status}')
                print(f'    Üretici: {order.producer.company_name if order.producer else "Atanmamış"}')
        else:
            print(f'    Sipariş: Yok')

    print(f'Toplam: {physical_count} fiziksel, {digital_count} dijital')

    # Network bağlantıları
    networks = ProducerNetwork.objects.filter(center=c)
    print(f'Network bağlantısı: {networks.count()}')
    for n in networks:
        print(f'  Network: {n.status}, Üretici: {n.producer.company_name}')
        if n.status != 'active':
            print('  *** UYARI: Network aktif değil! ***')

