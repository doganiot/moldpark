#!/usr/bin/env python
"""
Eski faturaların monthly_fee değerini günceller
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Invoice, PricingConfiguration
from decimal import Decimal

# Aktif fiyatlandırmayı al
pricing = PricingConfiguration.get_active()

# İşitme merkezi faturalarını bul
invoices = Invoice.objects.filter(
    invoice_type='center_admin_invoice'
)

print(f"Toplam {invoices.count()} adet işitme merkezi faturası bulundu.")

# monthly_fee olmayan veya 0 olan faturaları güncelle
updated_count = 0
for invoice in invoices:
    if not invoice.monthly_fee or invoice.monthly_fee == 0:
        old_total = invoice.total_amount
        
        # Monthly fee ekle
        invoice.monthly_fee = pricing.monthly_system_fee
        
        # Toplam tutarı güncelle
        new_total = old_total + pricing.monthly_system_fee
        invoice.total_amount = new_total
        
        # KDV'siz tutarı güncelle
        invoice.subtotal_without_vat = (new_total / Decimal('1.20')).quantize(Decimal('0.01'))
        
        invoice.save()
        updated_count += 1
        print(f"✓ Fatura {invoice.invoice_number}: {old_total} TL -> {new_total} TL (Aylık ücret eklendi)")

print(f"\n{updated_count} adet fatura güncellendi.")
print("İşlem tamamlandı!")

