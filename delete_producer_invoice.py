#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yanlış producer_invoice faturasını sil
"""
import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Invoice

# producer_invoice faturasını sil
producer_invoices = Invoice.objects.filter(invoice_type='producer_invoice')
print(f"[INFO] Silinecek producer_invoice sayısı: {producer_invoices.count()}")

for inv in producer_invoices:
    print(f"  - ID: {inv.id}, Tuttar: {inv.total_amount} TL, Tarih: {inv.issue_date}")

deleted_count, _ = producer_invoices.delete()
print(f"\n[OK] {deleted_count} producer_invoice silindi")

# Sonuç kontrol et
remaining = Invoice.objects.count()
print(f"[OK] Kalan fatura sayısı: {remaining}")

