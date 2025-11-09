#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Invoice
from center.models import Center
from django.contrib.auth.models import User
from datetime import datetime

# Tüm centerları listele
print('=== TÜM MERKEZLER ===')
for center in Center.objects.all():
    print(f'Merkez: {center.name} (User: {center.user.username})')
    
    # Bu merkez için paket faturası var mı?
    package_invoices = Invoice.objects.filter(
        issued_by_center=center,
        invoice_type='center_admin_invoice',
        invoice_number__startswith='PKG-'
    )
    
    if package_invoices.exists():
        print(f'  [OK] Paket Faturası Var:')
        for inv in package_invoices:
            print(f'    - {inv.invoice_number}: {inv.total_amount} TL (Tarih: {inv.issue_date})')
            if inv.breakdown_data:
                print(f'      Paket Adı: {inv.breakdown_data.get("package_name")}')
                print(f'      Kalıp Sayısı: {inv.breakdown_data.get("mold_count")}')
    else:
        print(f'  [NO] Paket Faturası Yok')
    
    # Bu merkez için normal faturalar
    normal_invoices = Invoice.objects.filter(
        issued_by_center=center,
        invoice_type='center_admin_invoice',
        invoice_number__startswith='CAD-'
    )
    if normal_invoices.exists():
        print(f'  Normal Faturalar: {normal_invoices.count()} adet')
    
    print()

print('\n=== TÜM PAKET FATURALARI ===')
all_packages = Invoice.objects.filter(
    invoice_type='center_admin_invoice',
    invoice_number__startswith='PKG-'
)
if all_packages.exists():
    for inv in all_packages:
        print(f'{inv.invoice_number} - {inv.total_amount} TL - Merkez: {inv.issued_by_center.name if inv.issued_by_center else "N/A"}')
else:
    print('Paket faturası bulunamadı')

print('\n=== TÜM ÜRETİCİ PAKET FATURALARI ===')
producer_packages = Invoice.objects.filter(
    invoice_type='producer_invoice',
    breakdown_data__package_invoice_number__isnull=False
)
if producer_packages.exists():
    for inv in producer_packages:
        print(f'{inv.invoice_number}')
        print(f'  Brüt: {inv.producer_gross_revenue} TL')
        print(f'  Net: {inv.producer_net_revenue} TL')
else:
    print('Üretici paket faturası bulunamadı')

