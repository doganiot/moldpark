#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KDV hesaplamalarını test et
"""
import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from center.models import Center
from core.models import Invoice
from decimal import Decimal

# Test faturası bul
centers = Center.objects.filter(is_active=True)
print(f"[INFO] Aktif merkez sayısı: {centers.count()}")

for center in centers[:1]:  # İlk merkezi test et
    invoices = Invoice.objects.filter(issued_by_center=center, invoice_type='center_admin_invoice')
    print(f"\n[INFO] Merkez: {center.name}")
    print(f"[INFO] Fatura sayısı: {invoices.count()}")
    
    for invoice in invoices[:1]:  # İlk faturayı test et
        print(f"\n=== Fatura: {invoice.invoice_number} ===")
        print(f"Toplam Tutar (KDV Dahil): {invoice.total_amount} TL")
        
        # KDV hesapla
        total_with_vat = invoice.total_amount or Decimal('0.00')
        vat_rate = Decimal('20')
        vat_multiplier = Decimal('1') + (vat_rate / Decimal('100'))
        subtotal_without_vat = total_with_vat / vat_multiplier
        vat_amount = total_with_vat - subtotal_without_vat
        
        print(f"\n=== KDV Hesaplamaları ===")
        print(f"KDV Hariç Tutarı: {subtotal_without_vat:.2f} TL")
        print(f"KDV Miktarı (%20): {vat_amount:.2f} TL")
        print(f"KDV Dahil Tutarı: {total_with_vat:.2f} TL")
        
        # Doğrulama
        total_check = subtotal_without_vat + vat_amount
        print(f"\n=== Doğrulama ===")
        print(f"KDV Hariç + KDV = {subtotal_without_vat:.2f} + {vat_amount:.2f} = {total_check:.2f} TL")
        print(f"Orijinal Tutarı = {total_with_vat:.2f} TL")
        print(f"Eşit mi? {abs(total_check - total_with_vat) < Decimal('0.01')}")
        
        # Fisiksel kalıp örneği: 450 TL = 375 TL + 75 TL KDV
        print(f"\n=== Örnek Hesaplama ===")
        example = Decimal('450')  # Fiziksel kalıp fiyatı
        example_net = example / vat_multiplier
        example_vat = example - example_net
        print(f"450 TL (KDV Dahil) = {example_net:.2f} TL (Net) + {example_vat:.2f} TL (KDV)")
        
        break  # Sadece ilk faturayı test et
    break  # Sadece ilk merkezi test et

