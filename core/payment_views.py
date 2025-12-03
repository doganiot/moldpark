"""
İşitme Merkezi Ödeme İşlemleri View'ları
"""
import logging
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

logger = logging.getLogger(__name__)


@login_required
def invoice_payment(request, invoice_id):
    """Fatura ödeme seçim sayfası"""
    
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # İzin kontrolü
    if not request.user.is_superuser:
        can_view = False
        if hasattr(request.user, 'center'):
            # Yeni sistem: issued_by_center kontrolü
            if invoice.issued_by_center == request.user.center:
                can_view = True
            # Eski sistem: user kontrolü
            elif invoice.user == request.user:
                can_view = True
        
        if not can_view:
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
    """Kredi kartı ile ödeme - İyzico entegrasyonu"""
    
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # İzin kontrolü
    if not request.user.is_superuser:
        can_view = False
        if hasattr(request.user, 'center'):
            # Yeni sistem: issued_by_center kontrolü
            if invoice.issued_by_center == request.user.center:
                can_view = True
            # Eski sistem: user kontrolü
            elif invoice.user == request.user:
                can_view = True
        
        if not can_view:
            raise Http404("Bu faturayı görüntüleme yetkiniz yok")
    
    if invoice.status == 'paid':
        messages.info(request, 'Bu fatura zaten ödenmiş.')
        return redirect('core:invoice_detail', invoice_id=invoice_id)
    
    payment_method = PaymentMethod.objects.filter(method_type='credit_card', is_active=True).first()
    if not payment_method:
        messages.error(request, 'Kredi kartı ödeme yöntemi aktif değil. Lütfen admin ile iletişime geçin.')
        return redirect('core:invoice_payment', invoice_id=invoice_id)
    
    # İyzico ödeme servisi
    from core.payment_service import IyzicoPaymentService
    try:
        iyzico_service = IyzicoPaymentService()
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('core:invoice_payment', invoice_id=invoice_id)
    except Exception as e:
        logger.error(f"İyzico servis hatası: {str(e)}")
        messages.error(request, f"Ödeme sistemi yapılandırma hatası: {str(e)}")
        return redirect('core:invoice_payment', invoice_id=invoice_id)
    
    # İyzico ödeme formu oluştur
    payment_result = iyzico_service.create_payment_request(invoice, request.user, request)
    
    if not payment_result.get('success'):
        error_msg = payment_result.get('error_message', 'Bilinmeyen hata')
        # İyzico'dan gelen hata mesajlarını kontrol et
        if 'api' in error_msg.lower() or 'bilgileri' in error_msg.lower():
            messages.error(
                request, 
                "İyzico API anahtarları yapılandırılmamış veya geçersiz. "
                "Lütfen admin ile iletişime geçin veya .env dosyasına API anahtarlarını ekleyin."
            )
        else:
            messages.error(request, f"Ödeme formu oluşturulamadı: {error_msg}")
        return redirect('core:invoice_payment', invoice_id=invoice_id)
    
    # Ödeme kaydı oluştur (pending durumunda)
    payment = Payment.objects.create(
        invoice=invoice,
        user=request.user,
        payment_method=payment_method,
        amount=invoice.total_amount,
        status='pending',
        iyzico_conversation_id=payment_result.get('conversation_id', ''),
        notes='İyzico ödeme formu oluşturuldu'
    )
    
    context = {
        'invoice': invoice,
        'payment_method': payment_method,
        'checkout_form_content': payment_result.get('checkout_form_content', ''),
        'payment_page_url': payment_result.get('payment_page_url', ''),
        'payment': payment,
    }
    
    return render(request, 'core/payment/iyzico_payment.html', context)


@login_required
def invoice_payment_bank_transfer(request, invoice_id):
    """Havale/EFT ile ödeme"""
    
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # İzin kontrolü
    if not request.user.is_superuser:
        can_view = False
        if hasattr(request.user, 'center'):
            # Yeni sistem: issued_by_center kontrolü
            if invoice.issued_by_center == request.user.center:
                can_view = True
            # Eski sistem: user kontrolü
            elif invoice.user == request.user:
                can_view = True
        
        if not can_view:
            raise Http404("Bu faturayı görüntüleme yetkiniz yok")
    
    if invoice.status == 'paid':
        messages.info(request, 'Bu fatura zaten ödenmiş.')
        return redirect('core:invoice_detail', invoice_id=invoice_id)
    
    payment_method = PaymentMethod.objects.filter(method_type='bank_transfer', is_active=True).first()
    if not payment_method:
        messages.error(request, 'Havale/EFT ödeme yöntemi aktif değil. Lütfen admin ile iletişime geçin.')
        return redirect('core:invoice_payment', invoice_id=invoice_id)
    
    bank_config = payment_method.bank_transfer_config if hasattr(payment_method, 'bank_transfer_config') else None
    if not bank_config:
        messages.error(request, 'Havale/EFT banka bilgileri yapılandırılmamış. Lütfen admin ile iletişime geçin.')
        return redirect('core:invoice_payment', invoice_id=invoice_id)
    
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


@login_required
def iyzico_payment_callback(request, invoice_id):
    """İyzico ödeme callback - Ödeme sonucu işleme"""
    
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # İzin kontrolü
    if not request.user.is_superuser:
        can_view = False
        if hasattr(request.user, 'center'):
            # Yeni sistem: issued_by_center kontrolü
            if invoice.issued_by_center == request.user.center:
                can_view = True
            # Eski sistem: user kontrolü
            elif invoice.user == request.user:
                can_view = True
        
        if not can_view:
            raise Http404("Bu faturayı görüntüleme yetkiniz yok")
    
    # İyzico token'ı al
    token = request.GET.get('token')
    if not token:
        messages.error(request, 'Ödeme token\'ı bulunamadı.')
        return redirect('core:invoice_payment', invoice_id=invoice_id)
    
    # İyzico ödeme servisi
    from core.payment_service import IyzicoPaymentService
    iyzico_service = IyzicoPaymentService()
    
    # Ödeme doğrulama
    verification_result = iyzico_service.verify_payment(token, invoice)
    
    # Bekleyen ödeme kaydını bul
    payment = Payment.objects.filter(
        invoice=invoice,
        user=request.user,
        status='pending',
        iyzico_token__isnull=True
    ).order_by('-created_at').first()
    
    if not payment:
        payment = Payment.objects.create(
            invoice=invoice,
            user=request.user,
            payment_method=PaymentMethod.objects.filter(method_type='credit_card', is_active=True).first(),
            amount=invoice.total_amount,
            status='pending'
        )
    
    if verification_result.get('success'):
        # Ödeme başarılı
        payment.status = 'completed'
        payment.iyzico_payment_id = verification_result.get('payment_id', '')
        payment.iyzico_token = token
        payment.iyzico_conversation_id = verification_result.get('conversation_id', '')
        payment.transaction_id = verification_result.get('payment_id', '')
        payment.iyzico_response = verification_result.get('raw_response', {})
        payment.last_four_digits = 'XXXX'  # İyzico'dan gelen kart bilgisi yoksa
        payment.confirmed_at = timezone.now()
        payment.save()
        
        # Faturayı ödendi olarak işaretle
        invoice.mark_as_paid(
            payment_method='Kredi Kartı (İyzico)',
            transaction_id=payment.transaction_id
        )
        
        # Bildirim gönder
        SimpleNotification.objects.create(
            user=request.user,
            title='Ödeme Başarılı',
            message=f'₺{invoice.total_amount} tutarındaki faturanız kredi kartı ile ödenmiştir.',
            notification_type='success',
            related_url=f'/financial/invoices/{invoice_id}/'
        )
        
        messages.success(request, f'Ödemeniz başarıyla yapılmıştır. Fatura Numarası: {invoice.invoice_number}')
        return redirect('core:invoice_detail', invoice_id=invoice_id)
    else:
        # Ödeme başarısız
        payment.status = 'failed'
        payment.iyzico_token = token
        payment.iyzico_response = verification_result.get('raw_response', {})
        payment.notes = f"Ödeme başarısız: {verification_result.get('error_message', 'Bilinmeyen hata')}"
        payment.save()
        
        messages.error(request, f"Ödeme başarısız: {verification_result.get('error_message', 'Bilinmeyen hata')}")
        return redirect('core:invoice_payment', invoice_id=invoice_id)

