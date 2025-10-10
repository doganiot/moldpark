import logging

logger = logging.getLogger(__name__)

from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.decorators import login_required

from django.contrib.admin.views.decorators import staff_member_required

from django.contrib.auth.models import User

from django.contrib.auth import authenticate, login, logout

from django.contrib import messages

from django.core.exceptions import PermissionDenied

from django.db.models import Q, Count

from django.utils import timezone

from django.http import JsonResponse, HttpResponse, Http404

from notifications.signals import notify

from core.utils import send_success_notification, send_order_notification, send_system_notification

from center.models import Center

from mold.models import EarMold, ModeledMold, RevisionRequest

from .models import Producer, ProducerOrder, ProducerNetwork, ProducerProductionLog

from .forms import (

    ProducerRegistrationForm, ProducerProfileForm, ProducerOrderForm,

    ProducerOrderUpdateForm, ProductionLogForm

)

from core.models import Invoice

import mimetypes

import os

from django.core.paginator import Paginator

from django.utils.dateparse import parse_date

from datetime import timedelta

import json



# ÜRETİCİ AUTHENTICATION - Ayrı sistem

def producer_required(view_func):

    """Decorator: Sadece doğrulanmış üretici merkezlerin erişimi"""

    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:

            messages.error(request, 'Bu sayfaya erişmek için giriş yapmalısınız.')

            return redirect('producer:login')

        

        try:

            producer = request.user.producer

            if not producer.is_active or not producer.is_verified:

                messages.error(request, 'Üretici hesabınız aktif değil veya doğrulanmamış.')

                logout(request)

                return redirect('producer:login')

            return view_func(request, *args, **kwargs)

        except Producer.DoesNotExist:

            messages.error(request, 'Bu sayfaya erişmek için üretici hesabınız olmalıdır.')

            logout(request)

            return redirect('producer:login')

    return wrapper





def producer_login(request):

    """Üretici Girişi - Ayrı Authentication Sistemi"""

    if request.user.is_authenticated:

        # Eğer zaten giriş yapmışsa ve üretici ise dashboard'a yönlendir

        try:

            producer = request.user.producer

            if producer.is_active and producer.is_verified:

                return redirect('producer:dashboard')

            else:

                logout(request)

                messages.error(request, 'Üretici hesabınız aktif değil.')

        except Producer.DoesNotExist:

            # Normal kullanıcı ise çıkış yap

            logout(request)

            messages.info(request, 'Üretici girişi için lütfen üretici bilgilerinizle giriş yapın.')

    

    if request.method == 'POST':

        email = request.POST.get('email')

        password = request.POST.get('password')

        

        if email and password:

            try:

                # Email ile kullanıcı bul

                user = User.objects.get(email=email)

                

                # ÖNEMLİ GÜVENLİK KONTROLÜ: Admin kullanıcıları engelle

                if user.is_superuser or user.is_staff:

                    messages.error(request, 'Admin hesapları bu panelden giriş yapamaz.')

                    return render(request, 'producer/login.html')

                

                # Şifre kontrolü

                user = authenticate(request, username=user.username, password=password)

                if user:

                    # Üretici kontrolü

                    try:

                        producer = user.producer

                        if producer.is_active and producer.is_verified:

                            login(request, user)

                            messages.success(request, f'Hoş geldiniz, {producer.company_name}!')

                            return redirect('producer:dashboard')

                        else:

                            messages.error(request, 'Üretici hesabınız aktif değil veya doğrulanmamış. Lütfen yönetici ile iletişime geçin.')

                    except Producer.DoesNotExist:

                        messages.error(request, 'Bu e-posta adresi ile kayıtlı üretici hesabı bulunamadı.')

                else:

                    messages.error(request, 'E-posta veya şifre hatalı.')

            except User.DoesNotExist:

                messages.error(request, 'Bu e-posta adresi ile kayıtlı kullanıcı bulunamadı.')

        else:

            messages.error(request, 'E-posta ve şifre alanları zorunludur.')

    

    return render(request, 'producer/login.html')





def producer_logout(request):

    """Üretici Çıkış"""

    logout(request)

    messages.success(request, 'Başarıyla çıkış yaptınız.')

    return redirect('producer:login')





def producer_register(request):

    """Üretici Merkez Kayıt Sayfası"""

    if request.method == 'POST':

        form = ProducerRegistrationForm(request.POST, request.FILES)

        if form.is_valid():

            # Kullanıcı oluştur - Admin yetkisi verme!

            user = User.objects.create_user(

                username=form.cleaned_data['username'],

                email=form.cleaned_data['email'],

                password=form.cleaned_data['password'],

                is_staff=False,  # Kesinlikle admin yetkisi verme

                is_superuser=False  # Kesinlikle superuser yapma

            )

            

            # Producer profili oluştur

            producer = form.save(commit=False)

            producer.user = user

            producer.is_verified = False  # Admin onayı beklesin

            producer.save()

            

            # 6 AYLIK ÜCRETSİZ KAMPANYA ABONELİĞİ - ÜRETİCİ MERKEZ İÇİN

            from core.models import PricingPlan, UserSubscription, SimpleNotification

            from datetime import timedelta

            from django.utils import timezone

            

            try:

                # Üretici merkezler için 6 aylık ücretsiz planı al

                producer_trial = PricingPlan.objects.filter(

                    plan_type='producer_trial',

                    is_active=True,

                    trial_days__gte=180

                ).first()

                

                if not producer_trial:

                    # Alternatif olarak normal üretici trial planı ara

                    producer_trial = PricingPlan.objects.filter(

                        name__icontains='üretici',

                        plan_type='trial',

                        is_active=True

                    ).first()

                

                if producer_trial:

                    # 6 aylık ücretsiz abonelik oluştur

                    end_date = timezone.now() + timedelta(days=180)

                    

                    subscription = UserSubscription.objects.create(

                        user=user,

                        plan=producer_trial,

                        status='active',

                        start_date=timezone.now(),

                        end_date=end_date,  # 6 ay sonrası

                        models_used_this_month=0,

                        amount_paid=0,

                        currency='USD'

                    )

                    

                    # Hoşgeldin bildirimi

                    SimpleNotification.objects.create(

                        user=user,

                        title='🏭 6 Aylık Ücretsiz Üretici Kampanyası!',

                        message=f'Hoş geldiniz! Üretici merkez olarak 6 ay boyunca platformu ücretsiz kullanabilirsiniz. Aylık {producer_trial.monthly_model_limit} sipariş alma hakkınız bulunmaktadır.',

                        notification_type='success',

                        related_url='/subscription/'

                    )

            except Exception as e:

                # Hata durumunda sessizce devam et

                pass

            

            # Admin'e bildirim gönder

            admin_users = User.objects.filter(is_superuser=True)

            for admin in admin_users:

                notify.send(

                    sender=user,

                    recipient=admin,

                    verb='yeni üretici merkez kaydı',

                    action_object=producer,

                    description=f'{producer.company_name} adlı üretici merkez onay bekliyor. 6 aylık ücretsiz kampanya otomatik tanımlandı.'

                )

            

            messages.success(request, 

                '🎉 Üretici merkez kaydınız başarıyla oluşturuldu! '

                '6 AYLIK ÜCRETSİZ kullanım hakkınız tanımlandı. '

                'Hesabınız admin onayından sonra aktif olacaktır.'

            )

            return redirect('producer:login')

    else:

        form = ProducerRegistrationForm()

    

    return render(request, 'producer/register.html', {'form': form})





@producer_required

def producer_dashboard(request):

    """Üretici Ana Sayfa - Güvenli Erişim"""

    producer = request.user.producer

    

    # Sadece kendi verilerine erişim

    total_orders = producer.orders.count()

    active_orders = producer.orders.exclude(status__in=['delivered', 'cancelled']).count()

    completed_orders = producer.orders.filter(status='delivered').count()

    network_centers_count = producer.network_centers.filter(status='active').count()

    

    # Ağ merkezleri - sadece kendi ağı

    network_centers = producer.network_centers.filter(status='active').select_related('center')

    

    # Son siparişler - sadece kendi siparişleri

    recent_orders = producer.orders.all()[:5]

    

    # Revizyon talepleri

    pending_revision_requests = RevisionRequest.objects.filter(

        modeled_mold__ear_mold__producer_orders__producer=producer,

        status='pending'

    ).count()

    

    # MESAJ İSTATİSTİKLERİ

    from core.models import Message, MessageRecipient

    from django.db.models import Q

    

    # Direkt gelen mesajlar

    user_messages = Message.objects.filter(

        Q(recipient=request.user) | Q(recipients__recipient=request.user)

    ).distinct()

    

    # Okunmamış mesajlar

    unread_direct = Message.objects.filter(

        recipient=request.user,

        is_read=False

    ).count()

    

    unread_broadcast = MessageRecipient.objects.filter(

        recipient=request.user,

        is_read=False

    ).count()

    

    total_messages = user_messages.count()

    unread_message_count = unread_direct + unread_broadcast

    

    # Bu ayki sipariş sayısı ve limit kontrolü

    monthly_orders = producer.get_current_month_orders()

    remaining_limit = producer.get_remaining_limit()

    

    # Yüzde hesaplama

    if producer.monthly_limit > 0:

        usage_percentage = round((monthly_orders * 100) / producer.monthly_limit, 1)

    else:

        usage_percentage = 0

    

    context = {

        'producer': producer,

        'total_orders': total_orders,

        'active_orders': active_orders,

        'completed_orders': completed_orders,

        'network_centers': network_centers_count,

        'network_centers_list': network_centers,

        'recent_orders': recent_orders,

        'pending_revision_requests': pending_revision_requests,

        'monthly_orders': monthly_orders,

        'remaining_limit': remaining_limit,

        'usage_percentage': usage_percentage,

        'total_messages': total_messages,

        'unread_message_count': unread_message_count,

    }

    

    return render(request, 'producer/dashboard.html', context)





@producer_required

def producer_profile(request):

    """Üretici Profil Sayfası"""

    producer = request.user.producer

    

    if request.method == 'POST':

        form = ProducerProfileForm(request.POST, request.FILES, instance=producer)

        if form.is_valid():

            form.save()

            messages.success(request, 'Profiliniz başarıyla güncellendi.')

            return redirect('producer:profile')

    else:

        form = ProducerProfileForm(instance=producer)

    

    return render(request, 'producer/profile.html', {'form': form, 'producer': producer})





@producer_required

def order_list(request):

    """Sipariş Listesi - Sadece Kendi Siparişleri"""

    producer = request.user.producer

    orders = producer.orders.all()

    

    # Filtreleme

    status_filter = request.GET.get('status')

    priority_filter = request.GET.get('priority')

    center_filter = request.GET.get('center')

    

    if status_filter:

        orders = orders.filter(status=status_filter)

    if priority_filter:

        orders = orders.filter(priority=priority_filter)

    if center_filter:

        # Sadece kendi ağındaki merkezleri kontrol et

        if producer.network_centers.filter(center_id=center_filter, status='active').exists():

            orders = orders.filter(center_id=center_filter)

    

    # Arama

    search = request.GET.get('search')

    if search:

        orders = orders.filter(

            Q(order_number__icontains=search) |

            Q(ear_mold__patient_name__icontains=search) |

            Q(ear_mold__patient_surname__icontains=search) |

            Q(center__name__icontains=search)

        )

    

    # Sadece kendi ağındaki merkezler

    network_centers = producer.network_centers.filter(status='active')

    

    context = {

        'orders': orders,

        'network_centers': network_centers,

    }

    

    return render(request, 'producer/order_list.html', context)





@producer_required

def order_detail(request, pk):

    """Sipariş Detayı - Güvenlik Kontrolü"""

    producer = request.user.producer

    

    # Sadece kendi siparişlerine erişim

    order = get_object_or_404(ProducerOrder, pk=pk, producer=producer)

    

    # Üretim logları

    production_logs = order.production_logs.all().order_by('-created_at')

    

    context = {

        'order': order,

        'production_logs': production_logs,

    }

    

    return render(request, 'producer/order_detail.html', context)





@producer_required

def order_update(request, pk):

    """Sipariş Güncelleme"""

    producer = request.user.producer

    

    order = get_object_or_404(ProducerOrder, pk=pk, producer=producer)

    

    if request.method == 'POST':

        form = ProducerOrderUpdateForm(request.POST, instance=order)

        if form.is_valid():

            old_status = order.status

            order = form.save()

            

            # Durum değişikliği bildirimi

            if old_status != order.status:

                notify.send(

                    sender=request.user,

                    recipient=order.center.user,

                    verb='sipariş durumu güncellendi',

                    action_object=order,

                    description=f'{order.order_number} siparişi {order.get_status_display()} durumuna geçti'

                )

            

            messages.success(request, 'Sipariş başarıyla güncellendi.')

            return redirect('producer:order_detail', pk=pk)

    else:

        form = ProducerOrderUpdateForm(instance=order)

    

    return render(request, 'producer/order_update.html', {'form': form, 'order': order})





# Mesajlaşma view'ları kaldırıldı - Sadece Admin Dashboard üzerinden mesajlaşma





@producer_required

def network_list(request):

    """Ağ Merkez Listesi"""

    networks = request.user.producer.network_centers.all()

    

    # Filtreleme

    status_filter = request.GET.get('status')

    if status_filter:

        networks = networks.filter(status=status_filter)

    

    context = {

        'networks': networks,

        'status_choices': ProducerNetwork.STATUS_CHOICES,

        'current_status': status_filter,

    }

    

    return render(request, 'producer/network_list.html', context)





# Davetiye sistemi kaldırıldı - Sadece admin tarafından ağ yönetimi yapılacak





@producer_required

def network_remove(request, center_id):

    """Merkezi Ağdan Çıkar - Otomatik MoldPark Ağına Geçiş"""

    if request.method == 'POST':

        try:

            network = ProducerNetwork.objects.get(

                producer=request.user.producer, 

                center_id=center_id,

                status='active'

            )

            

            # Merkez bilgilerini sakla

            center = network.center

            removed_producer = request.user.producer

            

            # Ağdan çıkar - status 'terminated' olarak değiştir

            network.status = 'terminated'

            network.terminated_at = timezone.now()

            network.termination_reason = f'{removed_producer.company_name} tarafından ağdan çıkarıldı'

            network.save()

            

            # MoldPark üretim merkezini bul veya oluştur

            try:

                moldpark_producer = Producer.objects.get(

                    company_name='MoldPark Üretim Merkezi',

                    contact_person='MoldPark Merkezi',

                    phone='0212-555-0100',

                    email='uretim@moldpark.com',

                    address='İstanbul, Türkiye',

                    tax_number='9876543210',

                    trade_registry='İstanbul-987654',

                    established_year=2024,

                    monthly_limit=5000,

                    is_active=True,

                    is_verified=True

                )

                

                # MoldPark ağına otomatik bağla

                moldpark_network, created = ProducerNetwork.objects.get_or_create(

                    producer=moldpark_producer,

                    center=center,

                    defaults={

                        'status': 'active',

                        'joined_at': timezone.now(),

                        'activated_at': timezone.now(),

                        'priority_level': 'medium',

                        'can_receive_orders': True,

                        'can_send_messages': True,

                        'auto_assigned': True,

                        'assignment_reason': f'{removed_producer.company_name} ağından çıkarıldıktan sonra otomatik atama'

                    }

                )

                

                if not created:

                    # Zaten varsa aktif hale getir

                    moldpark_network.status = 'active'

                    moldpark_network.activated_at = timezone.now()

                    moldpark_network.assignment_reason = f'{removed_producer.company_name} ağından çıkarıldıktan sonra otomatik yeniden atama'

                    moldpark_network.save()

                

            except Producer.DoesNotExist:

                # MoldPark üreticisi yoksa oluştur

                from django.contrib.auth.models import User

                moldpark_user, _ = User.objects.get_or_create(

                    username='moldpark_producer',

                    defaults={

                        'email': 'uretim@moldpark.com',

                        'first_name': 'MoldPark',

                        'last_name': 'Üretim'

                    }

                )

                

                moldpark_producer = Producer.objects.create(

                    user=moldpark_user,

                    company_name='MoldPark Üretim Merkezi',

                    contact_person='MoldPark Merkezi',

                    phone='0212-555-0100',

                    email='uretim@moldpark.com',

                    address='İstanbul, Türkiye',

                    tax_number='9876543210',

                    trade_registry='İstanbul-987654',

                    established_year=2024,

                    monthly_limit=5000,

                    is_active=True,

                    is_verified=True

                )

                

                # MoldPark ağına bağla

                ProducerNetwork.objects.create(

                    producer=moldpark_producer,

                    center=center,

                    status='active',

                    joined_at=timezone.now(),

                    activated_at=timezone.now(),

                    priority_level='high',

                    can_receive_orders=True,

                    can_send_messages=True,

                    auto_assigned=True,

                    assignment_reason=f'{removed_producer.company_name} ağından çıkarıldıktan sonra otomatik atama'

                )

            

            # Merkeze bildirim gönder

            notify.send(

                sender=request.user,

                recipient=center.user,

                verb='ağdan çıkarıldı ve MoldPark ağına alındı',

                action_object=removed_producer,

                description=f'{removed_producer.company_name} sizi ağından çıkardı. Otomatik olarak MoldPark Üretim Merkezi ağına bağlandınız.'

            )

            

            # Admin'lere bildirim gönder

            admin_users = User.objects.filter(is_superuser=True)

            for admin in admin_users:

                notify.send(

                    sender=request.user,

                    recipient=admin,

                    verb='merkez ağdan çıkarıldı',

                    action_object=center,

                    description=f'{center.name} merkezi {removed_producer.company_name} tarafından ağdan çıkarıldı ve MoldPark ağına otomatik geçiş yapıldı.'

                )

            

            return JsonResponse({

                'success': True, 

                'message': f'{center.name} merkezi başarıyla ağdan çıkarıldı ve otomatik olarak MoldPark ağına geçiş yaptı.'

            })

            

        except ProducerNetwork.DoesNotExist:

            return JsonResponse({'success': False, 'message': 'Merkez ağınızda bulunamadı.'})

        except Exception as e:
            logger.error(f'Network remove error: {str(e)}')

            return JsonResponse({'success': False, 'message': 'Bir hata oluştu.'})

    

    return JsonResponse({'success': False, 'message': 'Geçersiz istek.'})





@producer_required

def mold_list(request):

    """Güvenli Üretici Kalıp Listesi - Sadece Bu Üreticiye Gönderilen Kalıplar"""

    producer = request.user.producer

    

    # ÖNEMLİ GÜVENLİK: Sadece bu üreticiye gönderilen siparişlerin kalıplarını al

    # Veri tabanına direkt erişim YOK!

    producer_orders = producer.orders.select_related('ear_mold', 'center').all()

    

    # Filtreleme - sadece sipariş üzerinden

    status_filter = request.GET.get('status')

    order_status_filter = request.GET.get('order_status')

    center_filter = request.GET.get('center')

    

    if status_filter:

        # EarMold status filtresi

        producer_orders = producer_orders.filter(ear_mold__status=status_filter)

    if order_status_filter:

        # ProducerOrder status filtresi

        producer_orders = producer_orders.filter(status=order_status_filter)

    if center_filter:

        # Sadece kendi ağındaki merkezleri kontrol et

        if producer.network_centers.filter(center_id=center_filter, status='active').exists():

            producer_orders = producer_orders.filter(center_id=center_filter)

    

    # Arama - güvenli arama

    search = request.GET.get('search')

    if search:

        producer_orders = producer_orders.filter(

            Q(ear_mold__patient_name__icontains=search) |

            Q(ear_mold__patient_surname__icontains=search) |

            Q(center__name__icontains=search) |

            Q(order_number__icontains=search)

        )

    

    # Sıralama

    producer_orders = producer_orders.order_by('-created_at')

    

    # İstatistikler - güvenli hesaplama

    total_orders = producer_orders.count()

    received_orders = producer_orders.filter(status='received').count()

    production_orders = producer_orders.filter(status__in=['designing', 'production', 'quality_check']).count()

    completed_orders = producer_orders.filter(status='delivered').count()

    pending_orders = producer_orders.filter(status__in=['received', 'designing']).count()

    

    # Ağ merkezleri - sadece kendi ağı

    network_centers = producer.network_centers.filter(status='active').select_related('center')

    

    # Bu ayki sipariş limiti kontrolü

    monthly_orders = producer.get_current_month_orders()

    remaining_limit = producer.get_remaining_limit()

    

    # Kalıp türü seçenekleri - mold modelinden al

    from mold.models import EarMold

    mold_status_choices = EarMold.STATUS_CHOICES

    

    context = {

        'producer': producer,

        'producer_orders': producer_orders,  # Kalıplar değil, siparişler

        'network_centers': network_centers,

        'order_status_choices': ProducerOrder.STATUS_CHOICES,

        'mold_status_choices': mold_status_choices,

        'current_filters': {

            'status': status_filter,

            'order_status': order_status_filter,

            'center': center_filter,

            'search': search,

        },

        # İstatistikler

        'total_orders': total_orders,

        'received_orders': received_orders,

        'production_orders': production_orders,

        'completed_orders': completed_orders,

        'pending_orders': pending_orders,

        # Limit bilgileri

        'monthly_orders': monthly_orders,

        'remaining_limit': remaining_limit,

        'usage_percentage': round((monthly_orders * 100) / producer.monthly_limit, 1) if producer.monthly_limit > 0 else 0,

    }

    

    return render(request, 'producer/mold_list.html', context)





@producer_required

def mold_detail(request, pk):

    """Güvenli Kalıp Detayı - Sadece Kendi Siparişlerine Erişim"""

    producer = request.user.producer

    

    # ÖNEMLİ GÜVENLİK: Önce bu üreticiye ait sipariş olup olmadığını kontrol et

    try:

        producer_order = ProducerOrder.objects.select_related('ear_mold', 'center').get(

            pk=pk,  # Sipariş ID'si ile erişim

            producer=producer  # Sadece kendi siparişleri

        )

        ear_mold = producer_order.ear_mold

    except ProducerOrder.DoesNotExist:

        # Eğer bu üreticiye ait değilse hata ver

        messages.error(request, 'Bu kalıba erişim yetkiniz bulunmamaktadır.')

        return redirect('producer:order_list')

    

    # Ağ kontrolü - bu merkez üreticinin ağında mı? (Esnek kontrol)

    network_relation = producer.network_centers.filter(center=ear_mold.center).first()

    if not network_relation:

        messages.error(request, 'Bu merkez sizin ağınızda bulunmamaktadır.')

        return redirect('producer:order_list')

    

    # Network durumu kontrolü ve uyarı sistemi

    network_warning = None

    if network_relation.status == 'suspended':

        network_warning = 'Bu merkez ile ağ bağlantınız askıya alınmış durumda.'

        messages.warning(request, network_warning)

    elif network_relation.status == 'terminated':

        messages.error(request, 'Bu merkez ile ağ bağlantınız sonlandırılmış.')

        return redirect('producer:order_list')

    elif network_relation.status == 'pending':

        network_warning = 'Bu merkez ile ağ bağlantınız henüz onaylanmamış.'

        messages.info(request, network_warning)

    

    # Network aktivitesini güncelle

    network_relation.last_activity = timezone.now()

    network_relation.save(update_fields=['last_activity'])

    

    # Üretim logları - sadece bu siparişe ait

    production_logs = producer_order.production_logs.order_by('-created_at')

    

    # Kalıp dosyalarını al - sadece bu kalıba ait

    mold_files = ear_mold.modeled_files.all()

    

    # Revizyon dosyalarını al - sadece bu kalıba ait

    revisions = ear_mold.revisions.order_by('-created_at')

    

    # Revizyon yönetimi - kapsamlı sistem

    active_revision = None

    all_revisions = []

    revision_stats = {}

    try:

        from mold.models import RevisionRequest

        

        # Aktif revizyon talebi

        active_revision = RevisionRequest.objects.filter(

            modeled_mold__ear_mold=ear_mold,

            status__in=['producer_review', 'accepted', 'in_progress', 'quality_check', 'ready_for_delivery']

        ).first()

        

        # Tüm revizyon geçmişi - bu kalıba ait

        all_revisions = RevisionRequest.objects.filter(

            modeled_mold__ear_mold=ear_mold

        ).select_related('center').order_by('-created_at')

        

        # Revizyon istatistikleri

        revision_stats = {

            'total': all_revisions.count(),

            'completed': all_revisions.filter(status='completed').count(),

            'pending': all_revisions.filter(status__in=['pending', 'producer_review']).count(),

            'in_progress': all_revisions.filter(status__in=['accepted', 'in_progress', 'quality_check']).count(),

            'avg_completion_time': None,

        }

        

        # Ortalama tamamlanma süresi hesapla

        completed_revisions = all_revisions.filter(status='completed', completed_at__isnull=False)

        if completed_revisions.exists():

            total_days = sum([(r.completed_at.date() - r.created_at.date()).days for r in completed_revisions])

            revision_stats['avg_completion_time'] = round(total_days / completed_revisions.count(), 1)

            

    except Exception as e:

        print(f"Revizyon verileri yüklenemedi: {e}")

        pass

    

    # Son aktiviteler (loglar + mesajlar) - sadece bu siparişe ait

    activities = []

    

    # Production logları ekle

    for log in production_logs:

        activities.append({

            'type': 'production_log',

            'timestamp': log.created_at,

            'title': log.get_stage_display(),

            'description': log.description,

            'operator': log.operator,

            'data': log

        })

    

    # Mesajlaşma sistemi kaldırıldı - sadece production logları gösteriliyor

    

    # Aktiviteleri tarih sırasına göre sırala

    activities.sort(key=lambda x: x['timestamp'], reverse=True)

    

    # Form işlemleri - güvenli processing

    if request.method == 'POST':

        action = request.POST.get('action')

        

        if action == 'update_status':

            new_status = request.POST.get('status')

            if new_status and new_status in dict(ProducerOrder.STATUS_CHOICES):

                old_status = producer_order.get_status_display()

                producer_order.status = new_status

                producer_order.save()

                

                # Kalıp durumunu da senkronize et

                if new_status == 'delivered':

                    ear_mold.status = 'completed'

                    ear_mold.save()

                

                # Log oluştur

                stage_map = {

                    'designing': 'design_start',

                    'production': 'production_start',

                    'quality_check': 'quality_start',

                    'packaging': 'packaging_complete',

                    'shipping': 'shipping_start',

                    'delivered': 'delivered'

                }

                

                if new_status in stage_map:

                    ProducerProductionLog.objects.create(

                        order=producer_order,

                        stage=stage_map[new_status],

                        description=f'Durum güncellendi: {old_status} → {producer_order.get_status_display()}',

                        operator=request.user.get_full_name() or request.user.username

                    )

                

                # Merkeze bildirim gönder

                notify.send(

                    sender=request.user,

                    recipient=ear_mold.center.user,

                    verb='sipariş durumu güncellendi',

                    description=f'{ear_mold.patient_name} siparişinin durumu: {producer_order.get_status_display()}',

                    action_object=producer_order

                )

                

                messages.success(request, f'Sipariş durumu güncellendi: {producer_order.get_status_display()}')

                return redirect('producer:mold_detail', pk=pk)

        

        elif action == 'add_log':

            stage = request.POST.get('stage')

            description = request.POST.get('description')

            operator = request.POST.get('operator')

            duration = request.POST.get('duration')

            

            if stage and description:

                ProducerProductionLog.objects.create(

                    order=producer_order,

                    stage=stage,

                    description=description,

                    operator=operator or request.user.get_full_name() or request.user.username,

                    duration_minutes=int(duration) if duration else None

                )

                

                # Merkeze bildirim gönder

                notify.send(

                    sender=request.user,

                    recipient=ear_mold.center.user,

                    verb='üretim aşaması eklendi',

                    description=f'{ear_mold.patient_name}: {dict(ProducerProductionLog.STAGE_CHOICES)[stage]}',

                    action_object=producer_order

                )

                

                messages.success(request, 'Üretim logu eklendi.')

                return redirect('producer:mold_detail', pk=pk)

        

        elif action == 'add_shipping':

            shipping_company = request.POST.get('shipping_company')

            tracking_number = request.POST.get('tracking_number')

            shipping_cost = request.POST.get('shipping_cost')

            

            if shipping_company and tracking_number:

                producer_order.shipping_company = shipping_company

                producer_order.tracking_number = tracking_number

                if shipping_cost:

                    try:

                        producer_order.shipping_cost = float(shipping_cost)

                    except ValueError:

                        pass

                producer_order.status = 'shipping'

                producer_order.save()

                

                # Log oluştur

                ProducerProductionLog.objects.create(

                    order=producer_order,

                    stage='shipped',

                    description=f'Kargo: {shipping_company} - Takip No: {tracking_number}',

                    operator=request.user.get_full_name() or request.user.username

                )

                

                # Merkeze bildirim gönder

                notify.send(

                    sender=request.user,

                    recipient=ear_mold.center.user,

                    verb='sipariş kargoya verildi',

                    description=f'{ear_mold.patient_name} siparişi kargoya verildi. Takip No: {tracking_number}',

                    action_object=producer_order

                )

                

                messages.success(request, 'Kargo bilgileri eklendi ve sipariş kargoya verildi.')

                return redirect('producer:mold_detail', pk=pk)

        

        elif action == 'upload_revision':

            revision_id = request.POST.get('revision_id')

            revised_file = request.FILES.get('revised_file')

            revision_notes = request.POST.get('revision_notes', '')

            

            if revision_id and revised_file:

                try:

                    from mold.models import RevisionRequest

                    revision_request = RevisionRequest.objects.get(

                        id=revision_id,

                        modeled_mold__ear_mold=ear_mold,

                        status='in_progress'

                    )

                    

                    # Dosya boyutu kontrolü (50MB)

                    if revised_file.size > 52428800:  # 50MB

                        messages.error(request, 'Dosya boyutu 50MB\'dan büyük olamaz.')

                        return redirect('producer:mold_detail', pk=pk)

                    

                    # Dosya formatı kontrolü

                    allowed_extensions = ['stl', 'obj', 'ply', '3mf', 'amf']

                    file_extension = revised_file.name.split('.')[-1].lower()

                    if file_extension not in allowed_extensions:

                        messages.error(request, f'Sadece {", ".join(allowed_extensions).upper()} dosyaları yüklenebilir.')

                        return redirect('producer:mold_detail', pk=pk)

                    

                    # Revizyon dosyasını yükle

                    revision_request.revised_file = revised_file

                    revision_request.revision_notes = revision_notes

                    revision_request.status = 'completed'

                    revision_request.completed_at = timezone.now()

                    revision_request.save()

                    

                    # Kalıp durumunu güncelle

                    ear_mold.status = 'completed'

                    ear_mold.save()

                    

                    # Sipariş durumunu güncelle

                    producer_order.status = 'delivered'

                    producer_order.save()

                    

                    # Log oluştur

                    ProducerProductionLog.objects.create(

                        order=producer_order,

                        stage='delivered',

                        description=f'Revizyon tamamlandı - Revize edilmiş dosya yüklendi: {revised_file.name}',

                        operator=request.user.get_full_name() or request.user.username

                    )

                    

                    # Merkeze bildirim gönder

                    notify.send(

                        sender=request.user,

                        recipient=ear_mold.center.user,

                        verb='revizyon tamamlandı',

                        description=f'#{revision_request.id} numaralı revizyon talebiniz tamamlandı ve yeni dosya yüklendi.',

                        action_object=revision_request

                    )

                    

                    messages.success(request, 'Revizyon dosyası başarıyla yüklendi ve revizyon tamamlandı!')

                    return redirect('producer:mold_detail', pk=pk)

                    

                except RevisionRequest.DoesNotExist:

                    messages.error(request, 'Revizyon talebi bulunamadı.')

                    return redirect('producer:mold_detail', pk=pk)

                except Exception as e:

                    messages.error(request, f'Dosya yükleme hatası: {str(e)}')

                    return redirect('producer:mold_detail', pk=pk)

    

    # Güvenli context - sadece kendi verileri

    context = {

        'producer_order': producer_order,

        'ear_mold': ear_mold,

        'producer': producer,

        'network_relation': network_relation,

        'network_warning': network_warning,

        'production_logs': production_logs,

        'mold_files': mold_files,

        'revisions': revisions,

        'active_revision': active_revision,

        'all_revisions': all_revisions,

        'revision_stats': revision_stats,

        'activities': activities[:20],  # Son 20 aktivite

        'status_choices': ProducerOrder.STATUS_CHOICES,

        'stage_choices': ProducerProductionLog.STAGE_CHOICES,

    }

    

    return render(request, 'producer/mold_detail.html', context)





@producer_required

def mold_download(request, pk, file_id=None):

    """Güvenli Kalıp Dosyası İndirme - Sadece Kendi Siparişleri"""

    producer = request.user.producer

    

    # ÖNEMLİ GÜVENLİK: Önce bu üreticiye ait sipariş olup olmadığını kontrol et

    try:

        producer_order = ProducerOrder.objects.select_related('ear_mold', 'center').get(

            pk=pk,  # Sipariş ID'si ile erişim

            producer=producer  # Sadece kendi siparişleri

        )

        ear_mold = producer_order.ear_mold

    except ProducerOrder.DoesNotExist:

        messages.error(request, 'Bu kalıba erişim yetkiniz bulunmamaktadır.')

        return redirect('producer:mold_list')

    

    # Ağ kontrolü - bu merkez üreticinin ağında mı?

    network_relation = producer.network_centers.filter(center=ear_mold.center).first()

    if not network_relation:

        messages.error(request, 'Bu merkez sizin ağınızda bulunmamaktadır.')

        return redirect('producer:mold_list')

    

    # Network aktivitesini güncelle

    network_relation.last_activity = timezone.now()

    network_relation.save(update_fields=['last_activity'])

    

    # Varsayılan olarak scan_file indirme tipi

    download_type = 'scan_file'

    

    # Belirli bir dosya ID'si verilmişse

    if file_id:

        try:

            mold_file = ear_mold.modeled_files.get(id=file_id)

            file_path = mold_file.file.path

            file_name = os.path.basename(file_path)

            download_type = 'modeled_file'

        except ModeledMold.DoesNotExist:

            messages.error(request, 'Belirtilen dosya bulunamadı.')

            return redirect('producer:mold_detail', pk=pk)

    else:

        # Ana kalıp dosyasını (scan_file) indir

        if ear_mold.scan_file:

            file_path = ear_mold.scan_file.path

            file_name = os.path.basename(file_path)

        else:

            # Eğer scan_file yoksa, modeled_files'dan ilkini al

            mold_file = ear_mold.modeled_files.first()

            if not mold_file:

                messages.info(request, 'Bu kalıp için henüz indirilebilir dosya bulunmuyor. Merkez tarafından dosya yüklendiğinde burada görünecektir.')

                return redirect('producer:mold_detail', pk=pk)

            file_path = mold_file.file.path

            file_name = os.path.basename(file_path)

            download_type = 'modeled_file'

    

    # Dosya varlığını kontrol et

    if not os.path.exists(file_path):

        messages.error(request, 'Dosya bulunamadı veya erişilemez.')

        return redirect('producer:mold_detail', pk=pk)

    

    # Dosya indirme log'u ekle

    ProducerProductionLog.objects.create(

        order=producer_order,

        stage='design_start',

        description=f'{download_type.title()} indirildi: {file_name}',

        operator=request.user.get_full_name() or request.user.username

    )

    

    # Merkeze bildirim gönder

    notify.send(

        sender=request.user,

        recipient=ear_mold.center.user,

        verb='kalıp dosyası indirildi',

        description=f'{producer.company_name} tarafından {ear_mold.patient_name} kalıp dosyası ({download_type}) indirildi.',

        action_object=producer_order

    )

    

    try:

        # Dosya türünü al

        mime_type, _ = mimetypes.guess_type(file_path)

        if not mime_type:

            mime_type = 'application/octet-stream'

        

        # Dosya içeriğini oku

        with open(file_path, 'rb') as f:

            response = HttpResponse(f.read(), content_type=mime_type)

        

        # Dosya adını ayarla - güvenli encoding

        safe_filename = file_name.encode('ascii', 'ignore').decode('ascii')

        if not safe_filename:

            safe_filename = f'mold_file_{producer_order.id}'

        

        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'

        response['Content-Length'] = os.path.getsize(file_path)

        

        return response

        

    except (IOError, OSError) as e:

        messages.error(request, f'Dosya okunurken hata oluştu: {str(e)}')

        return redirect('producer:mold_detail', pk=pk)





@producer_required

def mold_upload_result(request, pk):

    """Güvenli Üretilen Kalıp Dosyası Yükleme - Sadece Kendi Siparişleri"""

    producer = request.user.producer

    

    # ÖNEMLİ GÜVENLİK: Önce bu üreticiye ait sipariş olup olmadığını kontrol et

    try:

        producer_order = ProducerOrder.objects.select_related('ear_mold', 'center').get(

            pk=pk,  # Sipariş ID'si ile erişim

            producer=producer  # Sadece kendi siparişleri

        )

        ear_mold = producer_order.ear_mold

    except ProducerOrder.DoesNotExist:

        messages.error(request, 'Bu siparişe erişim yetkiniz bulunmamaktadır.')

        return redirect('producer:order_list')

    

    # Ağ kontrolü - bu merkez üreticinin ağında mı? (Esnek kontrol)

    network_relation = producer.network_centers.filter(center=ear_mold.center).first()

    if not network_relation:

        messages.error(request, 'Bu merkez sizin ağınızda bulunmamaktadır.')

        return redirect('producer:order_list')

    

    # Eğer network suspended ise uyarı ver ama erişimi engelleme

    if network_relation.status == 'suspended':

        messages.warning(request, 'Bu merkez ile ağ bağlantınız askıya alınmış durumda.')

    elif network_relation.status == 'terminated':

        messages.error(request, 'Bu merkez ile ağ bağlantınız sonlandırılmış.')

        return redirect('producer:order_list')

    

    # Network aktivitesini güncelle

    network_relation.last_activity = timezone.now()

    network_relation.save(update_fields=['last_activity'])

    

    if request.method == 'POST':

        uploaded_file = request.FILES.get('file')

        description = request.POST.get('description', '')

        

        if uploaded_file:

            # Dosya türü kontrolü

            allowed_extensions = ['.stl', '.obj', '.ply', '.zip', '.rar']

            file_extension = os.path.splitext(uploaded_file.name)[1].lower()

            

            if file_extension not in allowed_extensions:

                messages.error(request, f'Desteklenmeyen dosya türü. İzin verilen türler: {", ".join(allowed_extensions)}')

                return render(request, 'producer/mold_upload_result.html', {

                    'producer_order': producer_order,

                    'ear_mold': ear_mold,

                })

            

            # Dosya boyutu kontrolü (50MB)

            if uploaded_file.size > 50 * 1024 * 1024:

                messages.error(request, 'Dosya boyutu 50MB\'dan büyük olamaz.')

                return render(request, 'producer/mold_upload_result.html', {

                    'producer_order': producer_order,

                    'ear_mold': ear_mold,

                })

            

            # Yeni dosya oluştur

            mold_file = ModeledMold.objects.create(

                ear_mold=ear_mold,

                file=uploaded_file,

                notes=description,

                status='approved'  # Otomatik olarak onaylanmış duruma getir

            )

            

            # Revizyon kontrolü - eğer bu kalıp için revizyon talebi varsa güncelle

            from mold.models import RevisionRequest

            revision_requests = RevisionRequest.objects.filter(

                modeled_mold__ear_mold=ear_mold,

                status__in=['accepted', 'in_progress']

            )

            

            revision_completed = False

            if revision_requests.exists():

                # Revizyon taleplerini tamamlandı olarak işaretle

                revision_requests.update(

                    status='completed',

                    resolved_at=timezone.now()

                )

                revision_completed = True

                

                # Revizyon log'u ekle

                ProducerProductionLog.objects.create(

                    order=producer_order,

                    stage='delivered',

                    description=f'Revizyon talebi tamamlandı ve yeni dosya yüklendi: {uploaded_file.name}. Revizyon sipariş teslim edildi.',

                    operator=request.user.get_full_name() or request.user.username

                )

            else:

                # Normal üretim logu ekle

                ProducerProductionLog.objects.create(

                    order=producer_order,

                    stage='delivered',

                    description=f'Kalıp üretimi tamamlandı ve dosya yüklendi: {uploaded_file.name}. Sipariş teslim edildi.',

                    operator=request.user.get_full_name() or request.user.username

                )

            

            # Siparişin durumunu güncelle - hangi durumda olursa olsun dosya yüklendiğinde tamamla

            if producer_order.status in ['received', 'designing', 'production', 'quality_check', 'packaging']:

                producer_order.status = 'delivered'  # Sipariş teslim edildi

                producer_order.actual_delivery = timezone.now()  # Gerçek teslimat zamanını kaydet

                producer_order.save()

                

                # Kalıp durumunu da "teslim edildi" olarak güncelle (tutarlılık için)

                ear_mold.status = 'completed'  # Completed yerine delivered - mantıklı akış

                ear_mold.save()

            

            # Merkeze basit bildirim gönder

            try:

                print(f"DEBUG: Merkeze bildirim gönderiliyor - User: {ear_mold.center.user.username}")

                if revision_completed:

                    notification = send_success_notification(

                        ear_mold.center.user,

                        'Revizyon Talebiniz Tamamlandı',

                        f'{ear_mold.patient_name} {ear_mold.patient_surname} hastanız için revizyon talebiniz {producer.company_name} tarafından tamamlandı. Yeni kalıp dosyası hazır!',

                        related_url=f'/mold/{ear_mold.id}/'

                    )

                    print(f"DEBUG: Revizyon bildirimi gönderildi - ID: {notification.id if notification else 'HATA'}")

                else:

                    notification = send_success_notification(

                        ear_mold.center.user,

                        'Kalıp Üretiminiz Tamamlandı',

                        f'{ear_mold.patient_name} {ear_mold.patient_surname} hastanız için kalıp üretimi {producer.company_name} tarafından tamamlandı. Dosyayı indirebilirsiniz!',

                        related_url=f'/mold/{ear_mold.id}/'

                    )

                    print(f"DEBUG: Kalıp bildirimi gönderildi - ID: {notification.id if notification else 'HATA'}")

            except Exception as e:

                print(f"DEBUG: Bildirim gönderme hatası: {str(e)}")

                logger.error(f"Notification error: {str(e)}", exc_info=True)

            

            # Admin'lere sistem bildirimi

            admin_users = User.objects.filter(is_superuser=True)

            for admin in admin_users:

                if revision_completed:

                    send_system_notification(

                        admin,

                        'Revizyon Talebi Tamamlandı',

                        f'{producer.company_name} tarafından {ear_mold.center.name} merkezinin {ear_mold.patient_name} {ear_mold.patient_surname} hastası için revizyon talebi tamamlandı.',

                        related_url=f'/admin-panel/'

                    )

                else:

                    send_system_notification(

                        admin,

                        'Kalıp Üretimi Tamamlandı',

                        f'{producer.company_name} tarafından {ear_mold.center.name} merkezinin {ear_mold.patient_name} {ear_mold.patient_surname} hastası için kalıp üretimi tamamlandı.',

                        related_url=f'/admin-panel/'

                    )

            

            # Başarı mesajı

            if revision_completed:

                messages.success(request, 'Revizyon talebi tamamlandı! Yeni kalıp dosyası başarıyla yüklendi. Kalıp durumu "Teslim Edildi" olarak güncellendi.')

            else:

                messages.success(request, 'Üretilen kalıp dosyası başarıyla yüklendi. Kalıp durumu "Teslim Edildi" olarak güncellendi.')

            return redirect('producer:mold_detail', pk=pk)

        else:

            messages.error(request, 'Lütfen bir dosya seçin.')

    

    # Güvenli context

    context = {

        'producer_order': producer_order,

        'ear_mold': ear_mold,

        'producer': producer,

        'allowed_extensions': ['.stl', '.obj', '.ply', '.zip', '.rar'],

        'max_file_size': '50MB',

    }

    

    return render(request, 'producer/mold_upload_result.html', context)





@producer_required

def mold_3d_comparison(request, pk):

    """Üretici için 3D Kalıp Karşılaştırma View'ı"""

    producer = request.user.producer

    

    # Güvenlik kontrolü - sadece kendi siparişlerine erişim

    try:

        producer_order = ProducerOrder.objects.select_related('ear_mold', 'center').get(

            pk=pk,

            producer=producer

        )

        ear_mold = producer_order.ear_mold

    except ProducerOrder.DoesNotExist:

        messages.error(request, 'Bu kalıba erişim yetkiniz bulunmamaktadır.')

        return redirect('producer:order_list')

    

    # Ağ kontrolü

    network_relation = producer.network_centers.filter(center=ear_mold.center).first()

    if not network_relation:

        messages.error(request, 'Bu merkez sizin ağınızda bulunmamaktadır.')

        return redirect('producer:order_list')

    

    if network_relation.status == 'terminated':

        messages.error(request, 'Bu merkez ile ağ bağlantınız sonlandırılmış.')

        return redirect('producer:order_list')

    

    # Network aktivitesini güncelle

    network_relation.last_activity = timezone.now()

    network_relation.save(update_fields=['last_activity'])

    

    # Dosya kontrolü

    original_scan = None

    modeled_files = []

    

    # Orijinal tarama dosyası

    if ear_mold.scan_file:

        original_scan = {

            'file_url': ear_mold.scan_file.url,

            'file_name': ear_mold.scan_file.name,

            'thumbnail_url': ear_mold.scan_thumbnail.url if ear_mold.scan_thumbnail else None,

            'metadata': {

                'file_format': getattr(ear_mold, 'file_format', 'STL'),

                'vertex_count': getattr(ear_mold, 'vertex_count', None),

                'polygon_count': getattr(ear_mold, 'polygon_count', None),

                'model_complexity': getattr(ear_mold, 'model_complexity', ''),

            }

        }

    

    # Modellenen dosyalar

    for modeled_mold in ear_mold.modeled_files.all():

        if modeled_mold.file:

            modeled_files.append({

                'id': modeled_mold.id,

                'file_url': modeled_mold.file.url,

                'file_name': modeled_mold.file.name,

                'thumbnail_url': modeled_mold.model_thumbnail.url if modeled_mold.model_thumbnail else None,

                'status': modeled_mold.status,

                'status_display': modeled_mold.get_status_display(),

                'created_at': modeled_mold.created_at,

                'notes': modeled_mold.notes,

                'metadata': {

                    'file_format': getattr(modeled_mold, 'file_format', 'STL'),

                    'vertex_count': getattr(modeled_mold, 'vertex_count', None),

                    'polygon_count': getattr(modeled_mold, 'polygon_count', None),

                    'model_complexity': getattr(modeled_mold, 'model_complexity', ''),

                }

            })

    

    # Render ayarları

    render_settings = {

        'camera_position': [50, 50, 50],

        'auto_rotate': False,

        'wireframe_mode': False,

        'comparison_mode': True,

        'sync_cameras': True

    }

    

    context = {

        'producer_order': producer_order,

        'ear_mold': ear_mold,

        'producer': producer,

        'network_relation': network_relation,

        'original_scan': original_scan,

        'modeled_files': modeled_files,

        'render_settings': json.dumps(render_settings),

        'page_title': f'3D Karşılaştırma - {ear_mold.patient_name} {ear_mold.patient_surname}',

    }

    

    return render(request, 'producer/mold_3d_comparison.html', context)





# Admin View'ları (Ana yönetim tarafından kullanılacak)



@staff_member_required

def admin_producer_list(request):

    """Admin: Üretici Listesi"""

    from django.core.paginator import Paginator

    

    producers = Producer.objects.all().order_by('-created_at')

    

    # Filtreleme

    status_filter = request.GET.get('status')

    if status_filter == 'verified':

        producers = producers.filter(is_verified=True)

    elif status_filter == 'pending':

        producers = producers.filter(is_verified=False)

    elif status_filter == 'active':

        producers = producers.filter(is_active=True)

    elif status_filter == 'inactive':

        producers = producers.filter(is_active=False)

    

    producer_type = request.GET.get('type')

    if producer_type:

        producers = producers.filter(producer_type=producer_type)

    

    # Arama

    search = request.GET.get('search')

    if search:

        producers = producers.filter(

            Q(company_name__icontains=search) |

            Q(brand_name__icontains=search) |

            Q(user__email__icontains=search) |

            Q(user__first_name__icontains=search) |

            Q(user__last_name__icontains=search)

        )

    

    # Sayfalama

    paginator = Paginator(producers, 20)  # Her sayfada 20 üretici

    page_number = request.GET.get('page')

    producers_page = paginator.get_page(page_number)

    

    # İstatistikler

    all_producers = Producer.objects.all()

    verified_count = all_producers.filter(is_verified=True).count()

    active_count = all_producers.filter(is_active=True).count()

    pending_count = all_producers.filter(is_verified=False).count()

    

    context = {

        'producers': producers_page,

        'verified_count': verified_count,

        'active_count': active_count,

        'pending_count': pending_count,

        'producer_types': Producer.PRODUCER_TYPE_CHOICES,

    }

    

    return render(request, 'producer/admin/producer_list.html', context)





@staff_member_required

def admin_producer_detail(request, pk):

    """Admin: Üretici Detay"""

    producer = get_object_or_404(Producer, pk=pk)

    

    # İstatistikler

    total_orders = producer.orders.count()

    active_orders = producer.orders.exclude(status__in=['delivered', 'cancelled']).count()

    

    # Ağ merkezleri ve kalıp bilgileri

    network_centers = producer.network_centers.filter(status='active').select_related('center')

    network_centers_count = network_centers.count()

    

    # Bu üreticinin kalıpları

    producer_molds = EarMold.objects.filter(

        producer_orders__producer=producer

    ).distinct().select_related('center').order_by('-created_at')

    

    # Kalıp istatistikleri

    total_molds = producer_molds.count()

    processing_molds = producer_molds.filter(status='processing').count()

    completed_molds = producer_molds.filter(status='completed').count()

    delivered_molds = producer_molds.filter(status='delivered').count()

    

    # Merkez bazında kalıp sayıları

    center_mold_stats = {}

    for network in network_centers:

        center_molds = producer_molds.filter(center=network.center)

        center_mold_stats[network.center.id] = {

            'center': network.center,

            'total': center_molds.count(),

            'processing': center_molds.filter(status='processing').count(),

            'completed': center_molds.filter(status='completed').count(),

            'delivered': center_molds.filter(status='delivered').count(),

            'recent_molds': center_molds[:5]  # Son 5 kalıp

        }

    

    context = {

        'producer': producer,

        'total_orders': total_orders,

        'active_orders': active_orders,

        'network_centers': network_centers,

        'network_centers_count': network_centers_count,

        'producer_molds': producer_molds[:10],  # Son 10 kalıp

        'total_molds': total_molds,

        'processing_molds': processing_molds,

        'completed_molds': completed_molds,

        'delivered_molds': delivered_molds,

        'center_mold_stats': center_mold_stats,

    }

    

    return render(request, 'producer/admin/producer_detail.html', context)





@staff_member_required

def admin_producer_verify(request, pk):

    """Admin: Üretici Doğrulama"""

    producer = get_object_or_404(Producer, pk=pk)

    

    if request.method == 'POST':

        action = request.POST.get('action')

        

        if action == 'verify':

            producer.is_verified = True

            producer.verification_date = timezone.now()

            producer.save()

            

            # Üreticiye bildirim gönder

            notify.send(

                sender=request.user,

                recipient=producer.user,

                verb='hesabınız doğrulandı',

                action_object=producer,

                description='Üretici merkez hesabınız başarıyla doğrulandı.'

            )

            

            messages.success(request, f'{producer.company_name} başarıyla doğrulandı.')

        

        elif action == 'unverify':

            producer.is_verified = False

            producer.verification_date = None

            producer.save()

            messages.success(request, f'{producer.company_name} doğrulaması kaldırıldı.')

    

    return redirect('producer:admin_producer_detail', pk=pk)





@staff_member_required

def admin_producer_update_limit(request, pk):

    """Admin: Üretici Limit Güncelleme"""

    producer = get_object_or_404(Producer, pk=pk)

    

    if request.method == 'POST':

        new_limit = request.POST.get('monthly_limit')

        if new_limit:

            try:

                producer.monthly_limit = int(new_limit)

                producer.save()

                messages.success(request, f'{producer.company_name} aylık kalıp limiti güncellendi.')

            except ValueError:

                messages.error(request, 'Geçersiz limit değeri.')

    

    return redirect('producer:admin_producer_detail', pk=pk)





@staff_member_required

def admin_mold_list(request):

    """Admin: Tüm Kalıpları Görüntüle"""

    from django.core.paginator import Paginator

    

    molds = EarMold.objects.all().order_by('-created_at')

    

    # Filtreleme

    status_filter = request.GET.get('status')

    mold_type_filter = request.GET.get('mold_type')

    center_filter = request.GET.get('center')

    producer_filter = request.GET.get('producer')

    

    if status_filter:

        molds = molds.filter(status=status_filter)

    if mold_type_filter:

        molds = molds.filter(mold_type=mold_type_filter)

    if center_filter:

        molds = molds.filter(center_id=center_filter)

    if producer_filter:

        molds = molds.filter(producer_orders__producer_id=producer_filter).distinct()

    

    # Arama

    search = request.GET.get('search')

    if search:

        molds = molds.filter(

            Q(patient_name__icontains=search) |

            Q(patient_surname__icontains=search) |

            Q(center__name__icontains=search)

        )

    

    # Sayfalama

    paginator = Paginator(molds, 20)  # Her sayfada 20 kalıp

    page_number = request.GET.get('page')

    molds_page = paginator.get_page(page_number)

    

    # Filtreleme için gerekli veriler

    centers = Center.objects.filter(is_active=True).order_by('name')

    producers = Producer.objects.filter(is_active=True).order_by('company_name')

    

    # İstatistikler

    total_molds = EarMold.objects.count()

    processing_molds = EarMold.objects.filter(status='processing').count()

    completed_molds = EarMold.objects.filter(status='completed').count()

    delivered_molds = EarMold.objects.filter(status='delivered').count()

    

    context = {

        'molds': molds_page,

        'centers': centers,

        'producers': producers,

        'status_choices': EarMold.STATUS_CHOICES,

        'mold_type_choices': EarMold.MOLD_TYPE_CHOICES,

        'current_filters': {

            'status': status_filter,

            'mold_type': mold_type_filter,

            'center': center_filter,

            'producer': producer_filter,

            'search': search,

        },

        # İstatistikler

        'total_molds': total_molds,

        'processing_molds': processing_molds,

        'completed_molds': completed_molds,

        'delivered_molds': delivered_molds,

    }

    

    return render(request, 'producer/admin/mold_list.html', context)





@staff_member_required

def admin_mold_download(request, pk):

    """Admin: Kalıp Dosyası İndir"""

    try:

        mold = get_object_or_404(EarMold, pk=pk)

        

        # Önce scan_file'ı kontrol et

        if mold.scan_file:

            file_path = mold.scan_file.path

            file_name = os.path.basename(file_path)

        else:

            # Yoksa modeled_files'dan ilkini al

            file = mold.modeled_files.first()

            if not file:

                raise Http404("Bu kalıp için dosya bulunamadı.")

            file_path = file.file.path

            file_name = os.path.basename(file_path)



        # Dosya türünü al

        mime_type, _ = mimetypes.guess_type(file_path)



        # Dosya içeriğini oku

        with open(file_path, 'rb') as f:

            response = HttpResponse(f.read(), content_type=mime_type)



        # Dosya adını ayarla

        response['Content-Disposition'] = f'attachment; filename="{file_name}"'

        

        return response

        

    except Exception as e:

        return HttpResponse(f"Dosya indirme hatası: {str(e)}", status=500)





# REVİZYON YÖNETİMİ



@login_required

@producer_required

def revision_requests(request):

    """Üretici revizyon talepleri listesi"""

    try:

        from mold.models import RevisionRequest

        

        # Filtreler

        status_filter = request.GET.get('status', '')

        priority_filter = request.GET.get('priority', '')

        search_query = request.GET.get('q', '')

        

        # Temel sorgu - üreticiye ait kalıpların revizyon talepleri

        revision_requests = RevisionRequest.objects.filter(

            modeled_mold__ear_mold__producer_orders__producer=request.user.producer,

            modeled_mold__ear_mold__producer_orders__status__in=['received', 'designing', 'production', 'quality_check', 'packaging', 'delivered']

        ).select_related(

            'modeled_mold__ear_mold',

            'center'

        ).distinct().order_by('-created_at')

        

        # Filtreleme

        if status_filter:

            revision_requests = revision_requests.filter(status=status_filter)

        

        if priority_filter:

            revision_requests = revision_requests.filter(priority=priority_filter)

        

        if search_query:

            revision_requests = revision_requests.filter(

                Q(modeled_mold__ear_mold__patient_name__icontains=search_query) |

                Q(modeled_mold__ear_mold__patient_surname__icontains=search_query) |

                Q(title__icontains=search_query) |

                Q(description__icontains=search_query)

            )

        

        # İstatistikler

        total_count = revision_requests.count()

        pending_count = revision_requests.filter(status='pending').count()

        in_progress_count = revision_requests.filter(status='in_progress').count()

        completed_count = revision_requests.filter(status='completed').count()

        overdue_count = len([r for r in revision_requests if r.is_overdue()])

        

        # Sayfalama

        paginator = Paginator(revision_requests, 10)

        page = request.GET.get('page', 1)

        revision_requests = paginator.get_page(page)

        

        context = {

            'revision_requests': revision_requests,

            'total_count': total_count,

            'pending_count': pending_count,

            'in_progress_count': in_progress_count,

            'completed_count': completed_count,

            'overdue_count': overdue_count,

            'status_filter': status_filter,

            'priority_filter': priority_filter,

            'search_query': search_query,

        }

        

        return render(request, 'producer/revision_requests.html', context)

        

    except Exception as e:

        messages.error(request, f'Revizyon talepleri yüklenirken hata: {str(e)}')

        return redirect('producer:dashboard')



@login_required

@producer_required

def revision_request_respond(request, request_id):

    """Üretici Revizyon Talebi Yanıtı - Basitleştirilmiş"""

    try:

        from mold.models import RevisionRequest

        from django.utils import timezone

        from datetime import timedelta

        

        # Güvenlik kontrolleri

        revision_request = get_object_or_404(

            RevisionRequest,

            id=request_id,

            modeled_mold__ear_mold__producer_orders__producer=request.user.producer

        )

        

        # Durum kontrolü

        if revision_request.status not in ['pending', 'producer_review']:

            messages.error(request, f'Bu revizyon talebi yanıtlanamaz. Mevcut durum: {revision_request.get_status_display()}')

            return redirect('producer:revision_requests')

        

        if request.method == 'POST':

            action = request.POST.get('action', '').strip()

            response = request.POST.get('response', '').strip()

            reason = request.POST.get('reason', '').strip()

            

            if action not in ['accept', 'reject']:

                messages.error(request, 'Geçersiz işlem türü.')

                return redirect('producer:revision_requests')

            

            now = timezone.now()

            

            if action == 'accept':

                # Kabul işlemi

                revision_request.status = 'accepted'

                revision_request.producer_response = response or 'Revizyon talebi kabul edildi'

                revision_request.producer_reviewed_at = now

                revision_request.producer_response_time = now - revision_request.created_at

                

                # Teslim tarihi hesaplama

                priority_days = {

                    'urgent': 2,

                    'high': 4,

                    'normal': 7,

                    'low': 10,

                }

                base_days = priority_days.get(revision_request.priority, 7)

                revision_request.expected_delivery = now.date() + timedelta(days=base_days)

                revision_request.save()

                

                # Süreç adımı ekle

                revision_request.add_process_step(

                    'Üretici tarafından kabul edildi',

                    'accepted',

                    f'Kabul edildi. Tahmini teslim: {revision_request.expected_delivery.strftime("%d.%m.%Y")}. {response or ""}'

                )

                

                # Bildirim gönder

                try:

                    send_success_notification(

                        revision_request.center.user,

                        'Revizyon Talebiniz Kabul Edildi',

                        f'#{revision_request.id} numaralı revizyon talebiniz kabul edildi. Tahmini teslim: {revision_request.expected_delivery.strftime("%d.%m.%Y")}. {response or ""}',

                        related_url=f'/mold/{revision_request.modeled_mold.ear_mold.id}/'

                    )

                    print(f"DEBUG: Revizyon kabul bildirimi gönderildi - Request ID: {revision_request.id}")

                except Exception as e:

                    print(f"Bildirim gönderme hatası: {e}")

                    logger.error(f"Revision accept notification error: {str(e)}", exc_info=True)

                

                messages.success(request, f'Revizyon talebi kabul edildi. Tahmini teslim: {revision_request.expected_delivery.strftime("%d.%m.%Y")}')

                

            elif action == 'reject':

                # Red nedeni kontrolü

                if not reason or len(reason.strip()) < 20:

                    messages.error(request, 'Red nedeni zorunludur ve en az 20 karakter olmalıdır.')

                    return redirect('producer:revision_requests')

                

                # Red işlemi

                revision_request.status = 'producer_rejected'

                revision_request.producer_response = response or 'Revizyon talebi reddedildi'

                revision_request.rejection_reason = reason

                revision_request.producer_reviewed_at = now

                revision_request.producer_response_time = now - revision_request.created_at

                revision_request.save()

                

                # Süreç adımı ekle

                revision_request.add_process_step(

                    'Üretici tarafından reddedildi',

                    'producer_rejected',

                    f'Red nedeni: {reason}'

                )

                

                # Bildirim gönder

                try:

                    send_warning_notification(

                        revision_request.center.user,

                        'Revizyon Talebiniz Reddedildi',

                        f'#{revision_request.id} numaralı revizyon talebiniz reddedildi. Nedeni: {reason}',

                        related_url=f'/mold/{revision_request.modeled_mold.ear_mold.id}/'

                    )

                    print(f"DEBUG: Revizyon red bildirimi gönderildi - Request ID: {revision_request.id}")

                except Exception as e:

                    print(f"Bildirim gönderme hatası: {e}")

                    logger.error(f"Revision reject notification error: {str(e)}", exc_info=True)

                

                messages.success(request, 'Revizyon talebi reddedildi.')

            

            return redirect('producer:revision_requests')

            

        # GET request - revizyon detay sayfasına yönlendir

        return redirect('producer:revision_request_detail', request_id)

        

    except RevisionRequest.DoesNotExist:

        messages.error(request, 'Revizyon talebi bulunamadı.')

        return redirect('producer:revision_requests')

    except Exception as e:

        messages.error(request, f'Bir hata oluştu: {str(e)}')

        return redirect('producer:revision_requests')





@login_required

@producer_required

def revision_start_work(request, request_id):

    """Revizyon işine başla - Basitleştirilmiş"""

    try:

        from mold.models import RevisionRequest

        from django.utils import timezone

        

        revision_request = get_object_or_404(

            RevisionRequest,

            id=request_id,

            modeled_mold__ear_mold__producer_orders__producer=request.user.producer

        )

        

        if revision_request.status != 'accepted':

            messages.error(request, f'Bu revizyon talebi için çalışma başlatılamaz. Mevcut durum: {revision_request.get_status_display()}')

            return redirect('producer:revision_requests')

        

        if request.method == 'POST':

            # Çalışmayı başlat

            revision_request.status = 'in_progress'

            revision_request.work_started_at = timezone.now()

            revision_request.save()

            

            # Süreç adımı ekle

            revision_request.add_process_step(

                'Revizyon çalışması başlatıldı',

                'in_progress',

                'Üretici revizyon çalışmasına başladı'

            )

            

            # Bildirim gönder

            try:

                # SimpleNotification ile bildirim gönder

                send_success_notification(

                    revision_request.center.user,

                    'Revizyon Çalışması Başladı',

                    f'#{revision_request.id} numaralı revizyon talebiniz için üretici çalışmaya başladı. Revizyon türü: {revision_request.get_revision_type_display()}',

                    related_url=f'/mold/{revision_request.modeled_mold.ear_mold.id}/'

                )

                print(f"DEBUG: Revizyon başlama bildirimi gönderildi - Request ID: {revision_request.id}")

            except Exception as e:

                print(f"Bildirim gönderme hatası: {e}")

                logger.error(f"Revision start notification error: {str(e)}", exc_info=True)

            

            messages.success(request, 'Revizyon çalışması başarıyla başlatıldı.')

            return redirect('producer:revision_requests')

            

        # GET request için onay sayfası göster

        return render(request, 'producer/revision_start_confirm.html', {

            'revision_request': revision_request

        })

        

    except RevisionRequest.DoesNotExist:

        messages.error(request, 'Revizyon talebi bulunamadı.')

        return redirect('producer:revision_requests')

    except Exception as e:

        messages.error(request, f'Bir hata oluştu: {str(e)}')

        return redirect('producer:revision_requests')





@login_required

@producer_required

def revision_complete_work(request, request_id):

    """Revizyon çalışmasını tamamla - Basitleştirilmiş"""

    try:

        from mold.models import RevisionRequest, ModeledMold

        from django.utils import timezone

        

        revision_request = get_object_or_404(

            RevisionRequest,

            id=request_id,

            modeled_mold__ear_mold__producer_orders__producer=request.user.producer

        )

        

        if revision_request.status != 'in_progress':

            messages.error(request, f'Bu revizyon talebi tamamlanamaz. Mevcut durum: {revision_request.get_status_display()}')

            return redirect('producer:revision_requests')

        

        if request.method == 'POST':

            revised_file = request.FILES.get('revised_file')

            revision_notes = request.POST.get('revision_notes', '').strip()

            

            if not revised_file:

                messages.error(request, 'Revize edilmiş dosya yüklenmesi zorunludur.')

                return redirect('producer:revision_requests')

            

            # Dosya boyutu kontrolü (50MB)

            if revised_file.size > 52428800:  # 50MB

                messages.error(request, 'Dosya boyutu 50MB\'dan büyük olamaz.')

                return redirect('producer:revision_requests')

            

            # Dosya formatı kontrolü

            allowed_extensions = ['stl', 'obj', 'ply', '3mf', 'amf']

            file_extension = revised_file.name.split('.')[-1].lower()

            if file_extension not in allowed_extensions:

                messages.error(request, f'Sadece {", ".join(allowed_extensions).upper()} dosyaları yüklenebilir.')

                return redirect('producer:revision_requests')

            

            # Revizyon dosyasını kaydet

            revision_request.revised_file = revised_file

            revision_request.revision_notes = revision_notes

            revision_request.status = 'completed'

            revision_request.completed_at = timezone.now()

            revision_request.save()

            

            # Kalıp durumunu güncelle

            ear_mold = revision_request.modeled_mold.ear_mold

            ear_mold.status = 'completed'

            ear_mold.save()

            

            # Sipariş durumunu güncelle

            producer_order = ear_mold.producer_orders.filter(producer=request.user.producer).first()

            if producer_order:

                producer_order.status = 'delivered'

                producer_order.actual_delivery = timezone.now()

                producer_order.save()

            

            # Süreç adımı ekle

            revision_request.add_process_step(

                'Revizyon tamamlandı',

                'completed',

                f'Revize edilmiş dosya yüklendi: {revised_file.name}' + (f' - {revision_notes}' if revision_notes else '')

            )

            

            # Bildirim gönder

            try:

                send_success_notification(

                    revision_request.center.user,

                    'Revizyon Tamamlandı',

                    f'#{revision_request.id} numaralı revizyon talebiniz tamamlandı ve revize edilmiş dosya yüklendi. {revision_notes or ""}',

                    related_url=f'/mold/{revision_request.modeled_mold.ear_mold.id}/'

                )

                print(f"DEBUG: Revizyon tamamlama bildirimi gönderildi - Request ID: {revision_request.id}")

            except Exception as e:

                print(f"Bildirim gönderme hatası: {e}")

                logger.error(f"Revision complete notification error: {str(e)}", exc_info=True)

            

            messages.success(request, 'Revizyon başarıyla tamamlandı ve dosya yüklendi!')

            return redirect('producer:revision_requests')

            

        # GET request için form sayfası göster

        return render(request, 'producer/revision_complete_form.html', {

            'revision_request': revision_request

        })

        

    except RevisionRequest.DoesNotExist:

        messages.error(request, 'Revizyon talebi bulunamadı.')

        return redirect('producer:revision_requests')

    except Exception as e:

        messages.error(request, f'Bir hata oluştu: {str(e)}')

        return redirect('producer:revision_requests')









@login_required

@producer_required

def revision_request_detail(request, request_id):

    """Revizyon talebi detay sayfası"""

    try:

        from mold.models import RevisionRequest

        

        revision_request = get_object_or_404(

            RevisionRequest,

            id=request_id,

            modeled_mold__ear_mold__producer_orders__producer=request.user.producer

        )

        

        # İlgili sipariş bilgisi

        producer_order = revision_request.modeled_mold.ear_mold.producer_orders.filter(

            producer=request.user.producer

        ).first()

        

        context = {

            'revision_request': revision_request,

            'producer_order': producer_order,

        }

        

        return render(request, 'producer/revision_request_detail.html', context)

        

    except RevisionRequest.DoesNotExist:

        messages.error(request, 'Revizyon talebi bulunamadı.')

        return redirect('producer:revision_requests')

    except Exception as e:

        messages.error(request, f'Bir hata oluştu: {str(e)}')

        return redirect('producer:revision_requests')







@producer_required

def producer_payments(request):

    """�Sretici ��demeleri ve alacaklar�� - Detayl�� finansal takip"""

    producer = request.user.producer



    # Mevcut ay ��deme ��zeti

    from datetime import date

    current_date = date.today()

    current_month_start = date(current_date.year, current_date.month, 1)



    if current_date.month == 12:

        next_month = date(current_date.year + 1, 1, 1)

    else:

        next_month = date(current_date.year, current_date.month + 1, 1)

    current_month_end = next_month



    # Bu ay tamamlanan sipari�xler

    current_month_completed_orders = producer.orders.filter(

        status="delivered",

        actual_delivery__gte=current_month_start,

        actual_delivery__lt=current_month_end

    )



    # Bu ay tahmini gelir

    current_month_estimated_revenue = sum(order.price for order in current_month_completed_orders if order.price)



    # Bu ay tahmini MoldPark komisyonu (%6.5)

    current_month_moldpark_commission = current_month_estimated_revenue * Decimal("0.065")



    # Bu ay tahmini kredi kart�� komisyonu (%3)

    current_month_credit_fee = current_month_estimated_revenue * Decimal("0.03")



    # Bu ay tahmini net ��deme

    current_month_net_payment = current_month_estimated_revenue - current_month_moldpark_commission - current_month_credit_fee



    # Kullan��c��n��n faturalar��

    invoices = Invoice.objects.filter(

        user=request.user,

        invoice_type="producer"

    ).order_by("-issue_date")



    # Ayl��k ��deme detaylar�� (faturalardan)

    monthly_payments = []

    for invoice in invoices:

        if invoice.issue_date:

            year = invoice.issue_date.year

            month = invoice.issue_date.month

            monthly_payments.append({

                "year": year,

                "month": month,

                "month_name": {

                    1: "Ocak", 2: "��ubat", 3: "Mart", 4: "Nisan",

                    5: "May��s", 6: "Haziran", 7: "Temmuz", 8: "A�xustos",

                    9: "Eyl��l", 10: "Ekim", 11: "Kas��m", 12: "Aral��k"

                }.get(month, ""),

                "gross_revenue": invoice.producer_revenue,

                "moldpark_commission": invoice.moldpark_commission,

                "credit_card_fee": invoice.credit_card_fee,

                "net_payment": invoice.net_amount,

                "status": invoice.status,

                "invoice_id": invoice.id,

                "order_count": invoice.producer_order_count,

            })



    # ��statistikler

    total_invoices = invoices.count()

    paid_invoices = invoices.filter(status="paid").count()

    pending_invoices = invoices.filter(status__in=["issued", "overdue"]).count()

    total_gross_revenue = sum(invoice.producer_revenue for invoice in invoices if invoice.producer_revenue)

    total_net_payments = sum(invoice.net_amount for invoice in invoices if invoice.net_amount)



    # Filtreleme

    status_filter = request.GET.get("status", "")

    year_filter = request.GET.get("year", "")

    month_filter = request.GET.get("month", "")



    if status_filter:

        invoices = invoices.filter(status=status_filter)



    if year_filter:

        invoices = invoices.filter(issue_date__year=year_filter)



    if month_filter:

        invoices = invoices.filter(issue_date__month=month_filter)



    # Sayfalama

    paginator = Paginator(invoices, 10)  # Sayfa ba�x��na 10 fatura

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)



    # Y��l se��enekleri

    years = Invoice.objects.filter(

        user=request.user,

        invoice_type="producer"

    ).dates("issue_date", "year", order="DESC")



    context = {

        "producer": producer,

        "page_obj": page_obj,

        "current_month_stats": {

            "completed_orders": current_month_completed_orders.count(),

            "estimated_revenue": current_month_estimated_revenue,

            "moldpark_commission": current_month_moldpark_commission,

            "credit_card_fee": current_month_credit_fee,

            "net_payment": current_month_net_payment,

        },

        "monthly_payments": monthly_payments[:12],  # Son 12 ay

        "total_invoices": total_invoices,

        "paid_invoices": paid_invoices,

        "pending_invoices": pending_invoices,

        "total_gross_revenue": total_gross_revenue,

        "total_net_payments": total_net_payments,

        "status_filter": status_filter,

        "year_filter": year_filter,

        "month_filter": month_filter,

        "years": years,

        "status_choices": Invoice.STATUS_CHOICES,

    }



    return render(request, "producer/payments.html", context)





@producer_required

def producer_payment_detail(request, invoice_id):

    """� deme faturas�� detay sayfas��"""

    producer = request.user.producer



    # Sadece kendi faturas��n�� g��rebilir

    invoice = get_object_or_404(

        Invoice,

        id=invoice_id,

        user=request.user,

        invoice_type="producer"

    )



    # ��lgili sipari�xleri bul (bu fatura d��neminde tamamlanan)

    related_orders = []

    if invoice.issue_date:

        # Fatura ay��n��n ba�x�� ve sonu

        year = invoice.issue_date.year

        month = invoice.issue_date.month



        from datetime import date

        month_start = date(year, month, 1)

        if month == 12:

            month_end = date(year + 1, 1, 1)

        else:

            month_end = date(year, month + 1, 1)



        related_orders = producer.orders.filter(

            status="delivered",

            actual_delivery__gte=month_start,

            actual_delivery__lt=month_end

        ).order_by("-actual_delivery")



    context = {

        "producer": producer,

        "invoice": invoice,

        "related_orders": related_orders,

    }



    return render(request, "producer/payment_detail.html", context)


@producer_required
def producer_payments(request):
    """Üretici Kazançları ve Ödemeleri - Detaylı Merkez Bazlı Takip Sistemi"""
    producer = request.user.producer
    from decimal import Decimal
    from django.db.models import Sum, Count, Q
    from datetime import datetime, date

    # Kazanç verilerini al
    earnings_this_month = producer.get_monthly_revenue()
    total_earnings = producer.get_total_earnings()
    monthly_earnings = producer.get_earnings_by_month(limit=6)
    pending_payments = producer.get_pending_payments()

    # Bu ay detayları (güncel oranlarla)
    earnings_this_month = {
        'gross_revenue': earnings_this_month,
        'moldpark_fee': earnings_this_month * Decimal('0.065'),  # %6.5
        'credit_card_fee': earnings_this_month * Decimal('0.03'),  # %3 (güncel oran)
        'net_earnings': earnings_this_month - (earnings_this_month * Decimal('0.065')) - (earnings_this_month * Decimal('0.03'))
    }

    # ============================================
    # MERKEZ BAZLI DETAYLI ÖDEME TAKİBİ
    # ============================================
    
    # Tüm aktif merkezler
    active_centers = producer.network_centers.filter(status='active').select_related('center')
    
    # Her merkez için detaylı ödeme bilgisi
    center_payment_details = []
    
    for network in active_centers:
        center = network.center
        
        # Bu merkeze ait siparişler
        center_orders = producer.orders.filter(center=center).select_related('ear_mold')
        
        # Tamamlanan ve işlem gören siparişler
        # Fiziksel kalıplar: Üretici aldığı anda (received) hizmet başlamıştır
        # Dijital kalıplar: Teslim edildiğinde (delivered) hizmet tamamlanmıştır
        completed_orders = center_orders.filter(
            Q(status='delivered') |  # Dijital kalıplar için teslim edilmiş
            Q(status__in=['received', 'designing', 'production', 'quality_check', 'packaging', 'shipping'], 
              ear_mold__is_physical_shipment=True)  # Fiziksel kalıplar için işlemde olanlar
        )
        
        # Fiziksel ve dijital kalıp sayıları
        physical_molds = completed_orders.filter(ear_mold__is_physical_shipment=True).count()
        digital_molds = completed_orders.filter(ear_mold__is_physical_shipment=False).count()
        
        # Toplam kazanç hesaplama
        total_gross = Decimal('0.00')
        for order in completed_orders:
            if order.ear_mold.is_physical_shipment:
                total_gross += Decimal('450.00')  # Fiziksel kalıp modelleme hizmeti
            else:
                total_gross += Decimal('50.00')   # 3D modelleme hizmeti
        
        # Kesintiler
        moldpark_fee = total_gross * Decimal('0.065')  # %6.5 MoldPark hizmet bedeli
        credit_card_fee = total_gross * Decimal('0.03')  # %3 kredi kartı komisyonu
        net_earnings = total_gross - moldpark_fee - credit_card_fee
        
        # Bu merkeze ait faturalar
        center_invoices = Invoice.objects.filter(
            Q(issued_by_center=center) | Q(user=center.user),
            invoice_type='producer_invoice'
        ).order_by('-issue_date')
        
        # Ödeme durumu
        paid_amount = sum(inv.net_amount for inv in center_invoices.filter(status='paid') if inv.net_amount)
        pending_amount = sum(inv.net_amount for inv in center_invoices.filter(status__in=['issued', 'sent']) if inv.net_amount)
        
        # İş kalemleri detayı
        work_items = []
        
        # Fiziksel kalıplar
        if physical_molds > 0:
            work_items.append({
                'name': 'Fiziksel Kalıp Üretimi',
                'quantity': physical_molds,
                'unit_price': Decimal('450.00'),
                'total': physical_molds * Decimal('450.00'),
                'type': 'physical'
            })
        
        # Dijital 3D modelleme
        if digital_molds > 0:
            work_items.append({
                'name': '3D Modelleme Hizmeti',
                'quantity': digital_molds,
                'unit_price': Decimal('50.00'),
                'total': digital_molds * Decimal('50.00'),
                'type': 'digital'
            })
        
        center_payment_details.append({
            'center': center,
            'network': network,
            'total_orders': completed_orders.count(),
            'physical_molds': physical_molds,
            'digital_molds': digital_molds,
            'work_items': work_items,
            'gross_revenue': total_gross,
            'moldpark_fee': moldpark_fee,
            'credit_card_fee': credit_card_fee,
            'net_earnings': net_earnings,
            'paid_amount': paid_amount,
            'pending_amount': pending_amount,
            'invoices_count': center_invoices.count(),
            'latest_payment_date': center_invoices.filter(status='paid').first().payment_date if center_invoices.filter(status='paid').exists() else None
        })
    
    # Toplam istatistikler
    total_centers = active_centers.count()
    total_physical_molds = sum(detail['physical_molds'] for detail in center_payment_details)
    total_digital_molds = sum(detail['digital_molds'] for detail in center_payment_details)
    total_gross_from_centers = sum(detail['gross_revenue'] for detail in center_payment_details)
    total_net_from_centers = sum(detail['net_earnings'] for detail in center_payment_details)

    # ============================================
    # FATURA LİSTESİ VE FİLTRELEME
    # ============================================
    
    # Kullanıcının faturaları (MoldPark'tan üreticiye yapılan ödemeler)
    invoices = Invoice.objects.filter(
        producer=producer,
        invoice_type__startswith='producer'
    ).select_related('issued_by_center').order_by('-issue_date')

    # İstatistikler
    total_invoices = invoices.count()
    paid_invoices = invoices.filter(status='paid').count()
    pending_invoices = invoices.filter(status__in=['issued', 'sent']).count()
    total_net_amount_received = sum(invoice.net_amount for invoice in invoices.filter(status='paid') if invoice.net_amount)
    total_orders_completed = total_earnings['total_orders']

    # Filtreleme
    status_filter = request.GET.get('status', '')
    year_filter = request.GET.get('year', '')
    month_filter = request.GET.get('month', '')
    center_filter = request.GET.get('center', '')  # Yeni: Merkez filtresi

    filtered_invoices = invoices
    if status_filter:
        filtered_invoices = filtered_invoices.filter(status=status_filter)
    if year_filter:
        filtered_invoices = filtered_invoices.filter(issue_date__year=year_filter)
    if month_filter:
        filtered_invoices = filtered_invoices.filter(issue_date__month=month_filter)
    if center_filter:
        filtered_invoices = filtered_invoices.filter(issued_by_center_id=center_filter)

    # Sayfalama
    paginator = Paginator(filtered_invoices, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Yıl seçenekleri
    years = Invoice.objects.filter(
        producer=producer,
        invoice_type__startswith='producer'
    ).dates('issue_date', 'year', order='DESC')

    context = {
        'producer': producer,
        'earnings_this_month': earnings_this_month,
        'monthly_earnings': monthly_earnings,
        'pending_payments': pending_payments,
        'total_orders_completed': total_orders_completed,
        'page_obj': page_obj,
        'total_invoices': total_invoices,
        'paid_invoices': paid_invoices,
        'pending_invoices': pending_invoices,
        'total_net_amount_received': total_net_amount_received,
        'status_filter': status_filter,
        'year_filter': year_filter,
        'month_filter': month_filter,
        'center_filter': center_filter,
        'years': years,
        'status_choices': Invoice.STATUS_CHOICES,
        # Merkez bazlı detaylar
        'center_payment_details': center_payment_details,
        'total_centers': total_centers,
        'total_physical_molds': total_physical_molds,
        'total_digital_molds': total_digital_molds,
        'total_gross_from_centers': total_gross_from_centers,
        'total_net_from_centers': total_net_from_centers,
        'active_centers': active_centers,
    }

    return render(request, 'producer/payments.html', context)


# ============================================
# FİZİKSEL KALIP SÜRECİ VİEW'LARI
# ============================================

@login_required
@producer_required
def receive_physical_shipment(request, pk):
    """Fiziksel kalıp kargo teslim alındı - Üretici"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)

        # Güvenlik kontrolleri
        if not mold.is_physical_shipment:
            messages.error(request, 'Bu kalıp dijital tarama için oluşturulmuş.')
            return redirect('producer:mold_detail', pk=pk)

        # İzin kontrolü - sadece kendi ağına ait kalıplar
        order = ProducerOrder.objects.filter(
            producer=request.user.producer,
            ear_mold=mold
        ).first()

        if not order:
            raise PermissionDenied("Bu kalıba erişim yetkiniz yok.")

        if request.method == 'POST':
            # Durumu güncelle
            old_status = mold.status
            mold.status = 'processing'  # İşlemeye alındı
            mold.save()

            # Log ekle
            ProducerProductionLog.objects.create(
                order=order,
                stage='production_start',
                description='Fiziksel kalıp kargo teslim alındı',
                operator=request.user.get_full_name()
            )

            # Bildirimler
            try:
                send_success_notification(
                    mold.center.user,
                    'Kalıp Teslim Alındı',
                    f'{mold.patient_name} {mold.patient_surname} hastasının kalıbı üreticiniz tarafından teslim alındı.',
                    related_url=f'/mold/{mold.id}/'
                )
            except Exception as e:
                logger.error(f"Notification error: {e}")

            messages.success(request,
                f'✅ {mold.patient_name} {mold.patient_surname} hastasının kalıbı teslim alındı ve işleme alındı.')
            return redirect('producer:mold_detail', pk=pk)

        context = {
            'mold': mold,
            'order': order,
        }

        return render(request, 'producer/receive_shipment.html', context)

    except Exception as e:
        logger.error(f"Receive shipment error: {e}")
        messages.error(request, 'Kalıp teslim alma işlemi sırasında hata oluştu.')
        return redirect('producer:mold_detail', pk=pk)


@login_required
@producer_required
def start_physical_production(request, pk):
    """Fiziksel kalıp üretimine başla"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)

        # Güvenlik kontrolleri
        if not mold.is_physical_shipment:
            messages.error(request, 'Bu işlem sadece fiziksel kalıplar için geçerlidir.')
            return redirect('producer:mold_detail', pk=pk)

        order = ProducerOrder.objects.filter(
            producer=request.user.producer,
            ear_mold=mold
        ).first()

        if not order:
            raise PermissionDenied("Bu kalıba erişim yetkiniz yok.")

        if mold.status != 'processing':
            messages.error(request, 'Bu kalıp zaten işleme alınmış durumda.')
            return redirect('producer:mold_detail', pk=pk)

        if request.method == 'POST':
            # Durumu koru (processing'de kalacak) ama log ekle
            ProducerProductionLog.objects.create(
                order=order,
                stage='production_start',
                description='Fiziksel kalıp üretimi başlatıldı',
                operator=request.user.get_full_name()
            )

            messages.success(request,
                f'✅ {mold.patient_name} {mold.patient_surname} hastasının kalıp üretimi başlatıldı.')
            return redirect('producer:mold_detail', pk=pk)

        context = {
            'mold': mold,
            'order': order,
        }

        return render(request, 'producer/start_production.html', context)

    except Exception as e:
        logger.error(f"Start production error: {e}")
        messages.error(request, 'Üretim başlatma işlemi sırasında hata oluştu.')
        return redirect('producer:mold_detail', pk=pk)


@login_required
@producer_required
def complete_physical_production(request, pk):
    """Fiziksel kalıp üretimini tamamla"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)

        # Güvenlik kontrolleri
        if not mold.is_physical_shipment:
            messages.error(request, 'Bu işlem sadece fiziksel kalıplar için geçerlidir.')
            return redirect('producer:mold_detail', pk=pk)

        order = ProducerOrder.objects.filter(
            producer=request.user.producer,
            ear_mold=mold
        ).first()

        if not order:
            raise PermissionDenied("Bu kalıba erişim yetkiniz yok.")

        if mold.status != 'processing':
            messages.error(request, 'Bu kalıp işleme alınmamış durumda.')
            return redirect('producer:mold_detail', pk=pk)

        if request.method == 'POST':
            # Durumu güncelle
            old_status = mold.status
            mold.status = 'completed'  # Tamamlandı
            mold.actual_delivery = timezone.now()
            mold.save()

            # Log ekle
            ProducerProductionLog.objects.create(
                order=order,
                stage='production_complete',
                description='Fiziksel kalıp üretimi tamamlandı',
                operator=request.user.get_full_name()
            )

            # Bildirimler
            try:
                send_success_notification(
                    mold.center.user,
                    'Kalıp Üretimi Tamamlandı',
                    f'{mold.patient_name} {mold.patient_surname} hastasının kalıbı üretim tamamlandı ve kargoya hazır.',
                    related_url=f'/mold/{mold.id}/'
                )
            except Exception as e:
                logger.error(f"Notification error: {e}")

            messages.success(request,
                f'✅ {mold.patient_name} {mold.patient_surname} hastasının kalıp üretimi tamamlandı.')
            return redirect('producer:mold_detail', pk=pk)

        context = {
            'mold': mold,
            'order': order,
        }

        return render(request, 'producer/complete_production.html', context)

    except Exception as e:
        logger.error(f"Complete production error: {e}")
        messages.error(request, 'Üretim tamamlama işlemi sırasında hata oluştu.')
        return redirect('producer:mold_detail', pk=pk)


@login_required
@producer_required
def ship_to_center(request, pk):
    """Tamamlanan kalıbı merkeze gönder"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)

        # Güvenlik kontrolleri
        if not mold.is_physical_shipment:
            messages.error(request, 'Bu işlem sadece fiziksel kalıplar için geçerlidir.')
            return redirect('producer:mold_detail', pk=pk)

        order = ProducerOrder.objects.filter(
            producer=request.user.producer,
            ear_mold=mold
        ).first()

        if not order:
            raise PermissionDenied("Bu kalıba erişim yetkiniz yok.")

        if mold.status != 'completed':
            messages.error(request, 'Bu kalıp henüz üretim tamamlanmamış.')
            return redirect('producer:mold_detail', pk=pk)

        if request.method == 'POST':
            # Kargo bilgilerini güncelle
            carrier = request.POST.get('carrier')
            tracking_number = request.POST.get('tracking_number')
            estimated_delivery = request.POST.get('estimated_delivery')

            # Durumu güncelle
            old_status = mold.status
            mold.status = 'shipped_to_center'  # Merkeze gönderildi
            mold.carrier_company = carrier
            mold.tracking_number = tracking_number
            if estimated_delivery:
                mold.estimated_delivery = estimated_delivery
            mold.shipment_date = timezone.now()
            mold.shipment_status = 'shipped'
            mold.save()

            # Log ekle
            ProducerProductionLog.objects.create(
                order=order,
                stage='shipped',
                description=f'Kalıp merkeze gönderildi - {carrier} {tracking_number}',
                operator=request.user.get_full_name()
            )

            # Bildirimler
            try:
                send_success_notification(
                    mold.center.user,
                    'Kalıp Kargoya Verildi',
                    f'{mold.patient_name} {mold.patient_surname} hastasının kalıbı kargoya verildi. '
                    f'Takip No: {tracking_number} ({carrier})',
                    related_url=f'/mold/{mold.id}/'
                )
            except Exception as e:
                logger.error(f"Notification error: {e}")

            messages.success(request,
                f'✅ {mold.patient_name} {mold.patient_surname} hastasının kalıbı {carrier} ile kargoya verildi.')
            return redirect('producer:mold_detail', pk=pk)

        context = {
            'mold': mold,
            'order': order,
            'carrier_choices': EarMold.CARRIER_CHOICES,
        }

        return render(request, 'producer/ship_to_center.html', context)

    except Exception as e:
        logger.error(f"Ship to center error: {e}")
        messages.error(request, 'Kargo gönderme işlemi sırasında hata oluştu.')
        return redirect('producer:mold_detail', pk=pk)


@login_required
@producer_required
def mark_delivered(request, pk):
    """Kalıp merkeze teslim edildi olarak işaretle"""
    try:
        mold = get_object_or_404(EarMold, pk=pk)

        # Güvenlik kontrolleri
        if not mold.is_physical_shipment:
            messages.error(request, 'Bu işlem sadece fiziksel kalıplar için geçerlidir.')
            return redirect('producer:mold_detail', pk=pk)

        order = ProducerOrder.objects.filter(
            producer=request.user.producer,
            ear_mold=mold
        ).first()

        if not order:
            raise PermissionDenied("Bu kalıba erişim yetkiniz yok.")

        if mold.status != 'shipped_to_center':
            messages.error(request, 'Bu kalıp henüz merkeze gönderilmemiş.')
            return redirect('producer:mold_detail', pk=pk)

        if request.method == 'POST':
            # Durumu güncelle - Center'ın onayı bekleniyor
            old_status = mold.status
            mold.status = 'delivered_pending_approval'  # Teslimat onayı bekleniyor
            mold.shipment_status = 'delivered_to_producer'  # Bu aslında center'a teslim edildi
            mold.save()

            # Log ekle
            ProducerProductionLog.objects.create(
                order=order,
                stage='delivered',
                description='Kalıp merkeze teslim edildi, onay bekleniyor',
                operator=request.user.get_full_name()
            )

            # Siparişi tamamla
            order.status = 'completed'
            order.completed_at = timezone.now()
            order.save()

            # Bildirimler
            try:
                send_success_notification(
                    mold.center.user,
                    'Kalıp Teslim Edildi',
                    f'{mold.patient_name} {mold.patient_surname} hastasının kalıbı başarıyla teslim edildi.',
                    related_url=f'/mold/{mold.id}/'
                )
            except Exception as e:
                logger.error(f"Notification error: {e}")

            messages.success(request,
                f'✅ {mold.patient_name} {mold.patient_surname} hastasının kalıbı başarıyla teslim edildi.')
            return redirect('producer:mold_detail', pk=pk)

        context = {
            'mold': mold,
            'order': order,
        }

        return render(request, 'producer/mark_delivered.html', context)

    except Exception as e:
        logger.error(f"Mark delivered error: {e}")
        messages.error(request, 'Teslim işlemi sırasında hata oluştu.')
        return redirect('producer:mold_detail', pk=pk)



