#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Invoice
from decimal import Decimal

# Son 5 paket faturasını listele
print('=== SON PAKET FATURALARI (Center) ===')
package_invoices = Invoice.objects.filter(invoice_number__startswith='PKG-').order_by('-created_at')[:5]
for inv in package_invoices:
    print(f'{inv.invoice_number} - {inv.total_amount} TL - {inv.user.username}')

print('\n=== İLGİLİ ÜRETICI FATURALARI (Producer) ===')
producer_invoices = Invoice.objects.filter(
    invoice_type='producer_invoice',
    breakdown_data__package_invoice_number__isnull=False
).order_by('-created_at')[:5]

if producer_invoices.exists():
    for inv in producer_invoices:
        package_no = inv.breakdown_data.get('package_invoice_number', 'N/A') if inv.breakdown_data else 'N/A'
        print(f'{inv.invoice_number} - Paket: {package_no}')
        print(f'  Brüt (producer_gross_revenue): {inv.producer_gross_revenue} TL')
        print(f'  MoldPark Fee: {inv.moldpark_service_fee} TL')
        print(f'  Net (producer_net_revenue): {inv.producer_net_revenue} TL')
        print()
else:
    print('Paket tabanlı üretici faturası bulunamadı')

print('\n=== TOPLAM PAKET SAYISI ===')
total_packages = Invoice.objects.filter(invoice_number__startswith='PKG-').count()
print(f'Toplam paket faturası: {total_packages}')

total_producer = Invoice.objects.filter(
    invoice_type='producer_invoice',
    breakdown_data__package_invoice_number__isnull=False
).count()
print(f'Paket tabanlı üretici faturası: {total_producer}')

