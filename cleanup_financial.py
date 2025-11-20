#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Finansal veriler temizleme scripti
"""
import os
import sys
import django

# Encoding ayarla
sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import FinancialSummary, Invoice
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum

# Tüm FinancialSummary kayıtlarını sıfırla
deleted_count, _ = FinancialSummary.objects.all().delete()
print(f"[OK] {deleted_count} FinancialSummary kaydı silindi")

# Tüm Invoice verilerini kontrol et
invoice_count = Invoice.objects.count()
center_invoices = Invoice.objects.filter(invoice_type='center_admin_invoice').count()
print(f"[OK] Toplam fatura: {invoice_count}")
print(f"[OK] İşitme merkezi faturaları: {center_invoices}")

# Geçerli ayın faturalarını kontrol et
now = timezone.now()
start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
end_date = now
month_invoices = Invoice.objects.filter(
    issue_date__gte=start_date.date(),
    issue_date__lte=end_date.date()
).count()
print(f"[OK] Bu ayın faturaları: {month_invoices}")

# Invoice fatura tutarlarını kontrol et
total_data = Invoice.objects.filter(
    invoice_type='center_admin_invoice',
    issue_date__gte=start_date.date(),
    issue_date__lte=end_date.date()
).aggregate(total=Sum('total_amount'))
total_amount = total_data['total'] or 0

print(f"[OK] Bu ayın fatura tutarı: {total_amount} TL")

# Tüm faturaları listele
print("\n=== Tüm Faturalar ===")
for inv in Invoice.objects.all():
    print(f"ID: {inv.id}, Tip: {inv.invoice_type}, Tuttar: {inv.total_amount}, Tarih: {inv.issue_date}")

print("\n=== Şu Ayın Faturaları ===")
for inv in Invoice.objects.filter(
    issue_date__gte=start_date.date(),
    issue_date__lte=end_date.date()
):
    print(f"ID: {inv.id}, Tip: {inv.invoice_type}, Tuttar: {inv.total_amount}, Tarih: {inv.issue_date}")

