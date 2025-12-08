"""
Türkiye Kargo Sistemi Views
Kargo gönderi oluşturma, takip ve yönetim view'ları
"""
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.paginator import Paginator

from .models import Invoice, CargoCompany, CargoShipment, CargoTracking, CargoLabel
from .cargo_service import CargoManager
from .cargo_label_service import CargoLabelManager
from .forms import CargoShipmentForm, CargoCompanyForm

logger = logging.getLogger(__name__)


@login_required
def cargo_dashboard(request):
    """Kargo dashboard sayfası"""

    # Kullanıcının yetkisine göre gönderileri filtrele
    shipments = CargoShipment.objects.select_related('invoice', 'cargo_company')

    if not request.user.is_staff and not request.user.is_superuser:
        # Sadece kullanıcının kendi gönderileri
        shipments = shipments.filter(invoice__user=request.user)

    shipments = shipments.order_by('-created_at')

    # İstatistikler
    total_shipments = shipments.count()
    pending_shipments = shipments.filter(status='pending').count()
    delivered_shipments = shipments.filter(status='delivered').count()
    in_transit_shipments = shipments.filter(status__in=['picked_up', 'in_transit', 'out_for_delivery']).count()

    # Sayfalama
    paginator = Paginator(shipments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_shipments': total_shipments,
        'pending_shipments': pending_shipments,
        'delivered_shipments': delivered_shipments,
        'in_transit_shipments': in_transit_shipments,
        'cargo_companies': CargoManager.get_cargo_companies()
    }

    return render(request, 'core/cargo/dashboard.html', context)


@login_required
def create_cargo_shipment_from_mold(request, mold_id):
    """Mold ID'den kargo gönderisi oluştur"""

    # Mold modelini import et
    from mold.models import EarMold

    mold = get_object_or_404(EarMold, pk=mold_id)

    # İzin kontrolü: superuser || ilgili üretici || ilgili merkez
    has_access = False
    producer_order = None

    # Üretici erişimi
    if hasattr(request.user, 'producer'):
        producer_order = mold.producer_orders.filter(
            producer=request.user.producer,
            status__in=['received', 'processing', 'completed']
        ).first()
        if producer_order:
            has_access = True

    # Merkez erişimi
    if hasattr(request.user, 'center') and mold.center == request.user.center:
        # Merkez kullanıcısı için aktif order'ı al (üretici fark etmeksizin)
        if not producer_order:
            producer_order = mold.producer_orders.filter(
                status__in=['received', 'processing', 'completed']
            ).first()
        has_access = True

    # Admin erişimi
    if request.user.is_superuser:
        if not producer_order:
            producer_order = mold.producer_orders.filter(
                status__in=['received', 'processing', 'completed']
            ).first()
        has_access = True

    if not has_access:
        messages.error(request, 'Bu işlem için yetkiniz yok (üretici veya ilgili merkez olmalısınız).')
        return redirect('mold:mold_detail', mold_id)

    # Fatura olsa da olmasa da kargo oluştur (invoice opsiyonel)
    existing_shipment = CargoShipment.objects.filter(
        invoice=getattr(producer_order, "invoice", None)
    ).first()
    if existing_shipment:
        messages.info(request, 'Bu sipariş için zaten kargo gönderisi oluşturulmuş.')
        return redirect('core:cargo_shipment_detail', shipment_id=existing_shipment.id)

    # Varsayılan kargo firmasını seç
    from core.models import CargoCompany
    default_company = CargoCompany.objects.first()
    if not default_company:
        default_company = CargoCompany.objects.create(
            name='Aras',
            display_name='Aras Kargo',
            tracking_url='https://kargotakip.araskargo.com.tr',
            base_price=0,
            price_per_kg=0,
            estimated_delivery_days=3
        )

    # Gönderen bilgisi: üretici varsa üretici, yoksa merkez
    sender_name = producer_order.producer.company_name if producer_order else mold.center.name
    sender_address = (
        getattr(producer_order.producer, 'address', '') if producer_order else getattr(mold.center, 'address', '')
    ) or ''
    sender_phone = (
        getattr(producer_order.producer, 'phone', '') if producer_order else getattr(mold.center, 'phone', '')
    ) or ''

    # Gönderi oluştur
    shipment = CargoShipment.objects.create(
        invoice=getattr(producer_order, "invoice", None),
        cargo_company=default_company,
        sender_name=sender_name,
        sender_address=sender_address,
        sender_phone=sender_phone,
        recipient_name=mold.center.name,
        recipient_address=getattr(mold.center, 'address', '') or '',
        recipient_phone=getattr(mold.center, 'phone', '') or '',
        package_description=f"Kalıp: {mold.patient_name} {mold.patient_surname} - {mold.get_mold_type_display()}",
        weight_kg=0.5,
        package_count=1,
        estimated_delivery=timezone.now() + timezone.timedelta(days=3),
    )

    messages.success(request, 'Kargo gönderisi oluşturuldu, etiket üretimi aktif.')
    return redirect('core:cargo_shipment_detail', shipment_id=shipment.id)


@login_required
def create_cargo_shipment(request, invoice_id):
    """Yeni kargo gönderisi oluştur"""

    invoice = get_object_or_404(Invoice, id=invoice_id)

    # İzin kontrolü
    if not request.user.is_superuser:
        can_access = False
        if hasattr(request.user, 'center') and invoice.issued_by_center == request.user.center:
            can_access = True
        elif invoice.user == request.user:
            can_access = True

        if not can_access:
            messages.error(request, 'Bu fatura için kargo gönderisi oluşturma yetkiniz yok.')
            return redirect('core:invoice_detail', invoice_id=invoice_id)

    # Zaten gönderi var mı kontrol et
    existing_shipment = CargoShipment.objects.filter(invoice=invoice).first()
    if existing_shipment:
        messages.info(request, 'Bu fatura için zaten kargo gönderisi oluşturulmuş.')
        return redirect('core:cargo_shipment_detail', shipment_id=existing_shipment.id)

    cargo_companies = CargoManager.get_cargo_companies()

    if request.method == 'POST':
        form = CargoShipmentForm(request.POST)
        if form.is_valid():
            cargo_company = form.cleaned_data['cargo_company']

            # Gönderi verilerini hazırla
            shipment_data = {
                'sender_name': form.cleaned_data['sender_name'],
                'sender_address': form.cleaned_data['sender_address'],
                'sender_phone': form.cleaned_data['sender_phone'],
                'recipient_name': form.cleaned_data['recipient_name'],
                'recipient_address': form.cleaned_data['recipient_address'],
                'recipient_phone': form.cleaned_data['recipient_phone'],
                'weight_kg': form.cleaned_data['weight_kg'],
                'package_count': form.cleaned_data['package_count'],
                'description': form.cleaned_data['description']
            }

            # Kargo gönderisi oluştur
            result = CargoManager.create_shipment(invoice, cargo_company, shipment_data)

            if result['success']:
                messages.success(request, f'Kargo gönderisi başarıyla oluşturuldu. Takip No: {result["tracking_number"]}')
                return redirect('core:cargo_shipment_detail', shipment_id=result['shipment'].id)
            else:
                messages.error(request, f'Kargo gönderisi oluşturulamadı: {result["error"]}')
        else:
            messages.error(request, 'Lütfen formu doğru şekilde doldurun.')
    else:
        # Form'u varsayılan değerlerle doldur
        initial_data = {}

        # Gönderen bilgileri (üretim merkezi)
        if hasattr(request.user, 'producer'):
            initial_data.update({
                'sender_name': request.user.producer.company_name,
                'sender_address': getattr(request.user.producer, 'address', ''),
                'sender_phone': getattr(request.user.producer, 'phone', ''),
            })
        elif hasattr(request.user, 'center'):
            initial_data.update({
                'sender_name': request.user.center.name,
                'sender_address': request.user.center.address,
                'sender_phone': request.user.center.phone,
            })

        # Alıcı bilgileri (fatura sahibi)
        if invoice.user:
            initial_data.update({
                'recipient_name': f"{invoice.user.first_name} {invoice.user.last_name}".strip() or invoice.user.username,
                'recipient_address': getattr(invoice.user, 'address', ''),
                'recipient_phone': getattr(invoice.user, 'phone', ''),
            })

        form = CargoShipmentForm(initial=initial_data)

    # Kargo maliyetlerini hesapla
    shipping_costs = {}
    for company in cargo_companies:
        weight = form.initial.get('weight_kg', 0.5)
        shipping_costs[company.id] = CargoManager.calculate_shipping_cost(company, weight)

    context = {
        'invoice': invoice,
        'form': form,
        'cargo_companies': cargo_companies,
        'shipping_costs': shipping_costs
    }

    return render(request, 'core/cargo/create_shipment.html', context)


@login_required
def cargo_shipment_detail(request, shipment_id):
    """Kargo gönderisi detay sayfası"""

    shipment = get_object_or_404(
        CargoShipment.objects.select_related('invoice', 'cargo_company'),
        id=shipment_id
    )

    # İzin kontrolü
    if not request.user.is_superuser:
        can_access = False
        if hasattr(request.user, 'center') and shipment.invoice.issued_by_center == request.user.center:
            can_access = True
        elif shipment.invoice.user == request.user:
            can_access = True

        if not can_access:
            messages.error(request, 'Bu kargo gönderisini görüntüleme yetkiniz yok.')
            return redirect('core:cargo_dashboard')

    # Takip geçmişini al
    tracking_history = shipment.tracking_history.select_related().order_by('-timestamp')

    context = {
        'shipment': shipment,
        'tracking_history': tracking_history,
        'tracking_url': shipment.get_tracking_url()
    }

    return render(request, 'core/cargo/shipment_detail.html', context)


@login_required
@require_http_methods(["POST"])
def generate_cargo_label(request, shipment_id):
    """Kargo etiketi oluştur (AJAX)"""

    try:
        shipment = get_object_or_404(CargoShipment, id=shipment_id)

        # İzin kontrolü (invoice opsiyonel)
        if not request.user.is_superuser:
            can_access = False
            if shipment.invoice:
                if hasattr(request.user, 'center') and shipment.invoice.issued_by_center == request.user.center:
                    can_access = True
                elif shipment.invoice.user == request.user:
                    can_access = True
            else:
                # Invoice yoksa: merkez veya üretici kullanıcıları için izin ver
                if hasattr(request.user, 'center') or hasattr(request.user, 'producer'):
                    can_access = True

            if not can_access:
                return JsonResponse({'success': False, 'error': 'Yetkisiz işlem'})

        label_type = request.POST.get('label_type', 'pdf')
        template_id = request.POST.get('template_id')

        # Şablon seçimi
        template = None
        if template_id:
            template = get_object_or_404(CargoLabel, id=template_id, is_active=True)

        # Etiket oluştur
        result = CargoLabelManager.generate_label(shipment, label_type, template)

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Kargo etiketi oluşturma hatası: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def print_cargo_label(request, shipment_id):
    """Kargo etiketini yazdır"""

    try:
        shipment = get_object_or_404(CargoShipment, id=shipment_id)

        # İzin kontrolü (invoice opsiyonel)
        if not request.user.is_superuser:
            can_access = False
            if shipment.invoice:
                if hasattr(request.user, 'center') and shipment.invoice.issued_by_center == request.user.center:
                    can_access = True
                elif shipment.invoice.user == request.user:
                    can_access = True
            else:
                if hasattr(request.user, 'center') or hasattr(request.user, 'producer'):
                    can_access = True

            if not can_access:
                return JsonResponse({'success': False, 'error': 'Yetkisiz işlem'})

        result = CargoLabelManager.print_label(shipment)

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Kargo etiketi yazdırma hatası: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def cargo_labels_list(request):
    """Kargo etiket şablonları listesi"""

    if not request.user.is_staff:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok.')
        return redirect('core:home')

    templates = CargoLabelManager.get_available_templates()

    context = {
        'templates': templates
    }

    return render(request, 'core/cargo/labels_list.html', context)


@login_required
@require_http_methods(["POST"])
def update_shipment_status(request, shipment_id):
    """Kargo gönderi durumunu güncelle (AJAX)"""

    try:
        shipment = get_object_or_404(CargoShipment, id=shipment_id)

        # İzin kontrolü (sadece admin veya üretim merkezi)
        if not request.user.is_superuser and not hasattr(request.user, 'producer'):
            return JsonResponse({'success': False, 'error': 'Yetkisiz işlem'})

        new_status = request.POST.get('status')
        description = request.POST.get('description', '')

        if not new_status:
            return JsonResponse({'success': False, 'error': 'Durum belirtilmedi'})

        # Geçerli durum geçişi mi kontrol et
        if not shipment.can_update_status(new_status):
            return JsonResponse({'success': False, 'error': 'Geçersiz durum geçişi'})

        # Durumu güncelle
        shipment.update_status(new_status, description)

        # Bildirim gönder
        from .models import SimpleNotification
        SimpleNotification.objects.create(
            user=shipment.invoice.user,
            title='Kargo Durumu Güncellendi',
            message=f'Takip No: {shipment.tracking_number} - {shipment.get_status_display()}',
            notification_type='info'
        )

        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': shipment.get_status_display(),
            'description': description
        })

    except Exception as e:
        logger.error(f"Kargo durumu güncelleme hatası: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def track_shipment_api(request, shipment_id):
    """Kargo gönderisini API'den takip et (AJAX)"""

    try:
        shipment = get_object_or_404(CargoShipment, id=shipment_id)

        # İzin kontrolü
        if not request.user.is_superuser:
            can_access = False
            if hasattr(request.user, 'center') and shipment.invoice.issued_by_center == request.user.center:
                can_access = True
            elif shipment.invoice.user == request.user:
                can_access = True

            if not can_access:
                return JsonResponse({'success': False, 'error': 'Yetkisiz işlem'})

        # API'den takip bilgilerini al
        result = CargoManager.track_shipment(shipment)

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Kargo takip hatası: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def cargo_companies_list(request):
    """Kargo firmaları listesi"""

    companies = CargoManager.get_cargo_companies()

    context = {
        'companies': companies
    }

    return render(request, 'core/cargo/companies_list.html', context)


# Admin Views
@login_required
def cargo_admin_dashboard(request):
    """Kargo admin dashboard"""

    if not request.user.is_staff:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok.')
        return redirect('core:home')

    # Genel istatistikler
    total_shipments = CargoShipment.objects.count()
    active_shipments = CargoShipment.objects.filter(status__in=['pending', 'picked_up', 'in_transit', 'out_for_delivery']).count()
    delivered_shipments = CargoShipment.objects.filter(status='delivered').count()
    failed_shipments = CargoShipment.objects.filter(status__in=['returned', 'failed', 'cancelled']).count()

    # Firma bazlı istatistikler
    company_stats = []
    for company in CargoCompany.objects.filter(is_active=True):
        shipments = CargoShipment.objects.filter(cargo_company=company)
        company_stats.append({
            'company': company,
            'total': shipments.count(),
            'active': shipments.filter(status__in=['pending', 'picked_up', 'in_transit', 'out_for_delivery']).count(),
            'delivered': shipments.filter(status='delivered').count(),
            'failed': shipments.filter(status__in=['returned', 'failed', 'cancelled']).count()
        })

    # Son gönderiler
    recent_shipments = CargoShipment.objects.select_related(
        'invoice', 'cargo_company'
    ).order_by('-created_at')[:20]

    context = {
        'total_shipments': total_shipments,
        'active_shipments': active_shipments,
        'delivered_shipments': delivered_shipments,
        'failed_shipments': failed_shipments,
        'company_stats': company_stats,
        'recent_shipments': recent_shipments
    }

    return render(request, 'core/cargo/admin_dashboard.html', context)


@login_required
def manage_cargo_company(request, company_id=None):
    """Kargo firması ekle/düzenle"""

    if not request.user.is_staff:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok.')
        return redirect('core:home')

    if company_id:
        company = get_object_or_404(CargoCompany, id=company_id)
    else:
        company = None

    if request.method == 'POST':
        form = CargoCompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kargo firması başarıyla kaydedildi.')
            return redirect('core:cargo_admin_dashboard')
    else:
        form = CargoCompanyForm(instance=company)

    context = {
        'form': form,
        'company': company
    }

    return render(request, 'core/cargo/manage_company.html', context)


@login_required
@require_http_methods(["POST"])
def delete_cargo_company(request, company_id):
    """Kargo firması sil"""

    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Yetkisiz işlem'})

    try:
        company = get_object_or_404(CargoCompany, id=company_id)

        # Aktif gönderisi olan firma silinemez
        active_shipments = CargoShipment.objects.filter(
            cargo_company=company,
            status__in=['pending', 'picked_up', 'in_transit', 'out_for_delivery']
        ).count()

        if active_shipments > 0:
            return JsonResponse({
                'success': False,
                'error': f'Bu firmada {active_shipments} aktif gönderi var. Önce gönderileri tamamlayın.'
            })

        company.delete()
        return JsonResponse({'success': True})

    except Exception as e:
        logger.error(f"Kargo firması silme hatası: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def cargo_reports(request):
    """Kargo raporları"""

    if not request.user.is_staff:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok.')
        return redirect('core:home')

    # Tarih filtresi
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    shipments = CargoShipment.objects.select_related('invoice', 'cargo_company')

    if start_date:
        shipments = shipments.filter(created_at__date__gte=start_date)
    if end_date:
        shipments = shipments.filter(created_at__date__lte=end_date)

    # İstatistikler
    stats = {
        'total_shipments': shipments.count(),
        'total_cost': sum(s.shipping_cost for s in shipments),
        'delivered': shipments.filter(status='delivered').count(),
        'pending': shipments.filter(status='pending').count(),
        'failed': shipments.filter(status__in=['returned', 'failed', 'cancelled']).count(),
    }

    # Firma bazlı rapor
    company_reports = []
    for company in CargoCompany.objects.filter(is_active=True):
        company_shipments = shipments.filter(cargo_company=company)
        company_reports.append({
            'company': company,
            'total': company_shipments.count(),
            'delivered': company_shipments.filter(status='delivered').count(),
            'total_cost': sum(s.shipping_cost for s in company_shipments),
            'success_rate': (company_shipments.filter(status='delivered').count() / company_shipments.count() * 100) if company_shipments.count() > 0 else 0
        })

    context = {
        'stats': stats,
        'company_reports': company_reports,
        'start_date': start_date,
        'end_date': end_date
    }

    return render(request, 'core/cargo/reports.html', context)
