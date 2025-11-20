"""
İşitme Merkezi Ödeme İşlemleri View'ları
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User

from core.models import (
    Invoice, Payment, PaymentMethod, BankTransferConfiguration,
    SimpleNotification
)
from core.forms import (
    InvoicePaymentForm, CreditCardPaymentForm, BankTransferPaymentForm
)


@login_required
def invoice_payment(request, invoice_id):
    """Fatura ödeme seçim sayfası"""
    
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # İzin kontrolü
    if not request.user.is_superuser:
        if not hasattr(request.user, 'center') or invoice.issued_by_center != request.user.center:
            raise Http404("Bu faturayı görüntüleme yetkiniz yok")
    
    # Ödenen faturalar için hata
    if invoice.status == 'paid':
        messages.info(request, 'Bu fatura zaten ödenmiş.')
        return redirect('core:invoice_detail', invoice_id=invoice_id)
    
    if request.method == 'POST':
        form = InvoicePaymentForm(request.POST)
        if form.is_valid():
            payment_method = form.cleaned_data['payment_method']
            
            # Kredi Kartı seçildiyse
            if payment_method.method_type == 'credit_card':
                return redirect('core:invoice_payment_credit_card', invoice_id=invoice_id)
            
            # Havale seçildiyse
            elif payment_method.method_type == 'bank_transfer':
                return redirect('core:invoice_payment_bank_transfer', invoice_id=invoice_id)
    else:
        form = InvoicePaymentForm()
    
    context = {
        'invoice': invoice,
        'form': form,
    }
    
    return render(request, 'core/payment/invoice_payment.html', context)


@login_required
def invoice_payment_credit_card(request, invoice_id):
    """Kredi kartı ile ödeme"""
    
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # İzin kontrolü
    if not request.user.is_superuser:
        if not hasattr(request.user, 'center') or invoice.issued_by_center != request.user.center:
            raise Http404("Bu faturayı görüntüleme yetkiniz yok")
    
    if invoice.status == 'paid':
        messages.info(request, 'Bu fatura zaten ödenmiş.')
        return redirect('core:invoice_detail', invoice_id=invoice_id)
    
    payment_method = get_object_or_404(PaymentMethod, method_type='credit_card', is_active=True)
    
    if request.method == 'POST':
        form = CreditCardPaymentForm(request.POST)
        if form.is_valid():
            # Demo modda doğrudan ödendi olarak işaretle
            # Gerçek uygulamada Stripe, PayPal vb. gateway kullanılacak
            
            payment = Payment.objects.create(
                invoice=invoice,
                user=request.user,
                payment_method=payment_method,
                amount=invoice.total_amount,
                status='completed',
                last_four_digits=form.cleaned_data.get('card_number', '')[-4:] if form.cleaned_data.get('card_number') else 'XXXX',
                transaction_id=f'DEMO-{invoice_id}-{timezone.now().timestamp()}',
                notes=f'Kredi kartı ile ödeme yapıldı. ({form.cleaned_data.get("cardholder_name", "İsim belirtilmedi")})'
            )
            
            # Faturayı ödendi olarak işaretle
            invoice.mark_as_paid(
                payment_method='Kredi Kartı',
                transaction_id=payment.transaction_id
            )
            
            # Bildirim gönder
            SimpleNotification.objects.create(
                user=request.user,
                title='Ödeme Basarili',
                message=f'₺{invoice.total_amount} tutarındaki faturanız kredi kartı ile ödenmiştir.',
                notification_type='success',
                related_url=f'/financial/invoices/{invoice_id}/'
            )
            
            messages.success(request, f'Ödemeniz başarıyla yapılmıştır. Fatura Numarası: {invoice.invoice_number}')
            return redirect('core:invoice_detail', invoice_id=invoice_id)
    else:
        form = CreditCardPaymentForm()
    
    context = {
        'invoice': invoice,
        'form': form,
        'payment_method': payment_method,
    }
    
    return render(request, 'core/payment/credit_card_payment.html', context)


@login_required
def invoice_payment_bank_transfer(request, invoice_id):
    """Havale/EFT ile ödeme"""
    
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # İzin kontrolü
    if not request.user.is_superuser:
        if not hasattr(request.user, 'center') or invoice.issued_by_center != request.user.center:
            raise Http404("Bu faturayı görüntüleme yetkiniz yok")
    
    if invoice.status == 'paid':
        messages.info(request, 'Bu fatura zaten ödenmiş.')
        return redirect('core:invoice_detail', invoice_id=invoice_id)
    
    payment_method = get_object_or_404(PaymentMethod, method_type='bank_transfer', is_active=True)
    bank_config = payment_method.bank_transfer_config
    
    if request.method == 'POST':
        form = BankTransferPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            # Ödeme kaydı oluştur - PENDİNG durumunda
            payment = Payment.objects.create(
                invoice=invoice,
                user=request.user,
                payment_method=payment_method,
                amount=invoice.total_amount,
                status='pending',
                bank_confirmation_number=form.cleaned_data.get('bank_confirmation_number', ''),
                payment_date=form.cleaned_data.get('payment_date'),
                receipt_file=form.cleaned_data.get('receipt_file'),
                notes=form.cleaned_data.get('notes', '')
            )
            
            # Bildirim gönder - Ödeme beklemede
            SimpleNotification.objects.create(
                user=request.user,
                title='Odeme Bekleniyor',
                message=f'₺{invoice.total_amount} tutarındaki havale ödemeleri kontrollerden geçirilmektedir.',
                notification_type='info',
                related_url=f'/financial/invoices/{invoice_id}/'
            )
            
            # Admin'e bildirim gönder
            admin_users = User.objects.filter(is_superuser=True)
            for admin in admin_users:
                SimpleNotification.objects.create(
                    user=admin,
                    title='Havale Odeme Talep Edildi',
                    message=f'{request.user.get_full_name()} tarafından ₺{invoice.total_amount} tutarında havale ödemesi yapılmıştır.',
                    notification_type='warning',
                    related_url=f'/admin/'
                )
            
            messages.success(
                request, 
                f'Havale talebi alınmıştır. Fatura Numarası: {invoice.invoice_number}. '
                f'Ödemeniz onaylandıktan sonra fatura başarıyla işaretlenecektir.'
            )
            return redirect('core:invoice_detail', invoice_id=invoice_id)
    else:
        form = BankTransferPaymentForm()
    
    context = {
        'invoice': invoice,
        'form': form,
        'payment_method': payment_method,
        'bank_config': bank_config,
    }
    
    return render(request, 'core/payment/bank_transfer_payment.html', context)


@login_required
def payment_methods_list(request):
    """Tum odeme yontemlerini listele"""
    
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    
    context = {
        'payment_methods': payment_methods,
    }
    
    return render(request, 'core/payment/payment_methods_list.html', context)


@login_required
def bank_transfer_details(request):
    """Havale/EFT detaylarini goster"""
    
    payment_method = PaymentMethod.objects.filter(
        method_type='bank_transfer',
        is_active=True
    ).first()
    
    if not payment_method or not payment_method.bank_transfer_config:
        raise Http404("Havale bilgileri bulunamadi")
    
    bank_config = payment_method.bank_transfer_config
    
    context = {
        'bank_config': bank_config,
        'payment_method': payment_method,
    }
    
    return render(request, 'core/payment/bank_transfer_details.html', context)

