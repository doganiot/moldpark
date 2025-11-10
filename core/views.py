from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import ContactMessage, Message, MessageRecipient, PricingPlan, UserSubscription, PaymentHistory, SimpleNotification, SubscriptionRequest, Invoice, Transaction, Commission
from .forms import ContactForm, MessageForm, AdminMessageForm, MessageReplyForm, SubscriptionRequestForm, PackagePurchaseForm
from django.views.generic import TemplateView
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.admin.views.decorators import staff_member_required
from center.models import Center
from mold.models import EarMold
from producer.models import Producer, ProducerOrder, ProducerNetwork
from accounts.forms import CustomSignupForm
from django.db.models import Q, Count, Avg
from django.contrib.auth.models import User
from notifications.signals import notify
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging
from .smart_notifications import SmartNotificationManager
from .utils import get_user_notifications, get_unread_count, mark_all_as_read, send_notification
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)

def home(request):
    # Paketleri al (package ve single tipindeki planlar)
    packages = PricingPlan.objects.filter(
        is_active=True, 
        plan_type__in=['package', 'single']
    ).order_by('order')[:3]  # İlk 3 paketi göster
    
    # En iyi puanlı üreticileri al
    top_producers = []
    try:
        from producer.models import Producer
        producers = Producer.objects.filter(is_active=True, is_verified=True)
        
        # Puanlarına göre sırala
        producer_ratings = []
        for producer in producers:
            avg_rating = producer.get_average_rating()
            if avg_rating > 0:  # Sadece değerlendirme almış üreticiler
                producer_ratings.append({
                    'producer': producer,
                    'avg_rating': avg_rating,
                    'quality_rating': producer.get_quality_rating(),
                    'speed_rating': producer.get_speed_rating(),
                    'total_evaluations': producer.get_total_evaluations(),
                    'rating_color': producer.get_rating_color()
                })
        
        # Puanlarına göre sırala (en yüksek önce)
        top_producers = sorted(producer_ratings, key=lambda x: x['avg_rating'], reverse=True)[:10]
        
    except Exception as e:
        logger.error(f"Üretici puanları alınırken hata: {e}")
        top_producers = []
    
    if request.user.is_authenticated:
        # Kullanıcının üretici olup olmadığını kontrol et
        is_producer = False
        try:
            is_producer = hasattr(request.user, 'producer') and request.user.producer is not None
        except:
            is_producer = False
        
        return render(request, 'core/home.html', {
            'is_producer': is_producer,
            'top_producers': top_producers,
            'packages': packages
        })
    
    # Giriş yapmamış kullanıcılar için kayıt formu
    if request.method == 'POST':
        try:
            form = CustomSignupForm(request.POST)
            if form.is_valid():
                try:
                    user = form.save(request)
                    messages.success(request, 'Kaydınız başarıyla oluşturuldu! Giriş yapabilirsiniz.')
                    return redirect('account_login')
                except Exception as e:
                    messages.error(request, 'Kayıt sırasında bir hata oluştu. Lütfen tekrar deneyin.')
            else:
                messages.error(request, 'Lütfen formdaki hataları düzeltin.')
        except Exception as e:
            form = CustomSignupForm()
            messages.error(request, 'Form yüklenirken bir hata oluştu.')
    else:
        try:
            form = CustomSignupForm()
        except Exception as e:
            # Basit bir form oluştur
            form = None
            messages.error(request, 'Form yüklenirken bir hata oluştu. Lütfen kayıt sayfasını kullanın.')
    
    return render(request, 'core/home.html', {
        'signup_form': form,
        'top_producers': top_producers,
        'packages': packages
    })

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Mesajınız başarıyla gönderildi.'))
            return redirect('core:contact')
    else:
        form = ContactForm()
    
    return render(request, 'core/contact.html', {'form': form})

class TermsView(TemplateView):
    template_name = 'core/terms.html'

class PrivacyView(TemplateView):
    template_name = 'core/privacy.html'

@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    # Ana modeller artık başta import edildi
    producers = Producer.objects.all()
    
    # MoldPark üretim merkezini bul
    moldpark_producer = Producer.objects.filter(
        company_name='MoldPark Üretim Merkezi'
    ).first()
    
    # MoldPark siparişlerini al
    moldpark_orders = []
    if moldpark_producer:
        moldpark_orders = ProducerOrder.objects.filter(
            producer=moldpark_producer
        ).select_related('center', 'ear_mold').order_by('-created_at')[:10]
    
    # Sonlandırılan merkez ağları (terminated)
    terminated_networks = ProducerNetwork.objects.filter(
        status='terminated'
    ).select_related('producer', 'center').order_by('-terminated_at')[:10]
    
    # Otomatik MoldPark'a geçen merkezler
    auto_assigned_centers = ProducerNetwork.objects.filter(
        auto_assigned=True,
        status='active'
    ).select_related('producer', 'center').order_by('-activated_at')[:10]
            
    centers = Center.objects.all()
    molds = EarMold.objects.all()
    # CenterMessage kaldırıldı - Merkezi mesajlaşma sistemi kullanılıyor
    messages = []
    
    # === BİLDİRİM SİSTEMİ CONTEXT'İ ===
    from datetime import datetime, timedelta
    from django.db.models import Count
    from django.utils import timezone
    
    # Son 24 saatteki bildirimler
    last_24h = timezone.now() - timedelta(hours=24)
    
    # Django-notifications-hq bildirimleri (tüm sistem)
    try:
        from notifications.models import Notification
        system_notifications_24h = Notification.objects.filter(timestamp__gte=last_24h)
        
        notification_stats = {
            'total_notifications_24h': system_notifications_24h.count(),
            'unread_notifications': Notification.objects.filter(unread=True).count(),
            'unique_recipients_24h': system_notifications_24h.values('recipient').distinct().count(),
            'notification_types': {}
        }
        
        # Bildirim türleri
        verb_counts = system_notifications_24h.values('verb').annotate(count=Count('verb')).order_by('-count')[:10]
        for item in verb_counts:
            notification_stats['notification_types'][item['verb']] = item['count']
            
    except ImportError:
        notification_stats = {
            'total_notifications_24h': 0,
            'unread_notifications': 0,
            'unique_recipients_24h': 0,
            'notification_types': {}
        }
    
    # SimpleNotification bildirimleri
    try:
        simple_notifications_24h = SimpleNotification.objects.filter(created_at__gte=last_24h)
        simple_notification_stats = {
            'total_simple_notifications_24h': simple_notifications_24h.count(),
            'unread_simple_notifications': SimpleNotification.objects.filter(is_read=False).count(),
            'simple_notification_types': {}
        }
        
        # Basit bildirim türleri
        simple_types = simple_notifications_24h.values('notification_type').annotate(count=Count('notification_type')).order_by('-count')
        for item in simple_types:
            simple_notification_stats['simple_notification_types'][item['notification_type']] = item['count']
            
    except:
        simple_notification_stats = {
            'total_simple_notifications_24h': 0,
            'unread_simple_notifications': 0,
            'simple_notification_types': {}
        }
    
    # Sistem sağlık durumu
    system_health = {
        'status': 'healthy',  # healthy, warning, critical
        'database_status': 'ok',
        'notification_system_status': 'ok',
        'active_users_24h': len(set(list(centers.values_list('user_id', flat=True)) + [p.user.id for p in producers])),
        'last_backup': timezone.now().replace(hour=0, minute=0, second=0),  # Demo
        'uptime_days': 30,  # Demo
    }
    
    # Akıllı bildirim önerileri
    smart_suggestions = []
    
    # Pasif merkezler için öneri
    inactive_centers = centers.filter(is_active=False)
    if inactive_centers.exists():
        smart_suggestions.append({
            'type': 'warning',
            'title': 'Pasif Merkezler',
            'message': f'{inactive_centers.count()} merkez pasif durumda. Durumlarını kontrol edin.',
            'action_url': None,
            'priority': 'high'
        })
    
    # Doğrulanmamış üreticiler için öneri
    unverified_producers = [p for p in producers if hasattr(p, 'is_verified') and not p.is_verified]
    if unverified_producers:
        smart_suggestions.append({
            'type': 'info',
            'title': 'Doğrulama Bekleyen Üreticiler',
            'message': f'{len(unverified_producers)} üretici doğrulama bekliyor.',
            'action_url': None,
            'priority': 'medium'
        })
    
    # Bekleyen kalıplar için öneri
    waiting_molds_count = molds.filter(status='waiting').count()
    if waiting_molds_count > 10:
        smart_suggestions.append({
            'type': 'warning',
            'title': 'Yüksek Bekleme Sırası',
            'message': f'{waiting_molds_count} kalıp işlem bekliyor.',
            'action_url': None,
            'priority': 'high'
        })
    
    # Kullanıcı bilgileri için center ve producer verilerini hazırla
    center_users = []
    for center in centers:
        center_users.append({
            'type': 'center',
            'name': center.name,
            'company': center.name,
            'username': center.user.username,
            'email': center.user.email,
            'password_display': '••••••••',  # Güvenlik için maskelenmiş
            'is_active': center.is_active,
            'created_at': center.created_at,
            'user_id': center.user.id,
            'profile_id': center.id
        })
    
    producer_users = []
    for producer in producers:
        producer_users.append({
            'type': 'producer',
            'name': producer.company_name,
            'company': producer.company_name,
            'username': producer.user.username,
            'email': producer.user.email,
            'password_display': '••••••••',  # Güvenlik için maskelenmiş
            'is_active': producer.is_active,
            'created_at': producer.created_at,
            'user_id': producer.user.id,
            'profile_id': producer.id
        })
    
    # MoldPark merkez yönetimi bilgisi
    moldpark_center = {
        'name': 'MoldPark Merkez Yönetimi',
        'is_active': True,
        'user': {'email': 'admin@moldpark.com'},
        'phone': 'Sistem Yönetimi',
        'address': 'Merkezi Kalıp Üretim Sistemi',
        'created_at': None,
        'is_moldpark': True
    }
    
    # Kalıp durumlarına göre istatistikler
    mold_stats = {
        'total_molds': molds.count(),
        'waiting_molds': molds.filter(status='waiting').count(),
        'processing_molds': molds.filter(status='processing').count(),
        'completed_molds': molds.filter(status='completed').count(),
        'revision_molds': molds.filter(
            modeled_files__revision_requests__status__in=['pending', 'admin_review', 'approved', 'rejected', 'producer_review', 'accepted', 'in_progress', 'quality_check', 'ready_for_delivery']
        ).distinct().count(),  # Sadece aktif revizyon talepleri olan kalıpları say
        'rejected_molds': molds.filter(status='rejected').count(),
        'shipping_molds': molds.filter(status='shipping').count(),
        'delivered_molds': molds.filter(status='delivered').count(),
    }
    
    # === ABONELİK TALEPLERİ YÖNETİMİ ===
    from .models import PricingPlan, UserSubscription, SubscriptionRequest
    
    # Beklemede olan abonelik talepleri
    pending_requests = SubscriptionRequest.objects.filter(
        status='pending'
    ).select_related('user', 'plan').order_by('-created_at')
    
    # Son 7 günde işlenen talepler
    last_week = timezone.now() - timedelta(days=7)
    recent_processed_requests = SubscriptionRequest.objects.filter(
        processed_at__gte=last_week
    ).select_related('user', 'plan', 'processed_by').order_by('-processed_at')
    
    # Abonelik istatistikleri
    all_subscriptions = UserSubscription.objects.all()
    subscription_stats = {
        'total_subscriptions': all_subscriptions.count(),
        'active_subscriptions': all_subscriptions.filter(status='active').count(),
        'trial_users': all_subscriptions.filter(plan__plan_type='trial', status='active').count(),
        'paid_users': all_subscriptions.filter(status='active').exclude(plan__plan_type='trial').count(),
        'pending_requests': pending_requests.count(),
        'total_requests': SubscriptionRequest.objects.count(),
        'approved_requests': SubscriptionRequest.objects.filter(status='approved').count(),
        'rejected_requests': SubscriptionRequest.objects.filter(status='rejected').count(),
    }
    
    # Plan türlerine göre dağılım
    subscription_by_plan = {}
    for plan in PricingPlan.objects.filter(is_active=True):
        count = all_subscriptions.filter(plan=plan, status='active').count()
        subscription_by_plan[plan.name] = {
            'count': count,
            'plan_type': plan.plan_type,
            'price': plan.price_usd
        }
    
    # Deneme paketi tükenen kullanıcılar
    trial_expired_users = []
    trial_subscriptions = all_subscriptions.filter(plan__plan_type='trial', status='active')
    for sub in trial_subscriptions:
        remaining = sub.get_remaining_models()
        if remaining is not None and remaining <= 0:
            trial_expired_users.append({
                'user': sub.user,
                'subscription': sub,
                'center_name': getattr(sub.user, 'center', None),
            })
    
    # Deneme paketi neredeyse tükenen kullanıcılar
    trial_warning_users = []
    for sub in trial_subscriptions:
        remaining = sub.get_remaining_models()
        if remaining is not None and 0 < remaining <= 1:
            trial_warning_users.append({
                'user': sub.user,
                'subscription': sub,
                'remaining': remaining,
                'center_name': getattr(sub.user, 'center', None),
            })
    
    # Aylık gelir hesaplaması (demo)
    monthly_revenue = 0
    for sub in all_subscriptions.filter(status='active'):
        if sub.plan.is_monthly:
            monthly_revenue += float(sub.plan.price_usd)
    
    # İstatistikler
    stats = {
        'total_centers': centers.count() + 1,  # MoldPark dahil
        'active_centers': centers.filter(is_active=True).count() + 1,  # MoldPark aktif
        'total_producers': len(producers),
        'verified_producers': len([p for p in producers if hasattr(p, 'is_verified') and p.is_verified]),
        'total_molds': mold_stats['total_molds'],
        'waiting_molds': mold_stats['waiting_molds'],
        'processing_molds': mold_stats['processing_molds'],
        'completed_molds': mold_stats['completed_molds'],
        'revision_molds': mold_stats['revision_molds'],
        'rejected_molds': mold_stats['rejected_molds'],
        'shipping_molds': mold_stats['shipping_molds'],
        'delivered_molds': mold_stats['delivered_molds'],
        'pending_molds': mold_stats['waiting_molds'],  # Geriye dönük uyumluluk için
        'moldpark_orders': len(moldpark_orders),
        'moldpark_active_orders': len([o for o in moldpark_orders if o.status in ['received', 'designing', 'production', 'quality_check']]),
        'total_users': len(center_users) + len(producer_users),
        # Abonelik istatistikleri
        'total_subscriptions': subscription_stats['total_subscriptions'],
        'active_subscriptions': subscription_stats['active_subscriptions'],
        'trial_users': subscription_stats['trial_users'],
        'paid_users': subscription_stats['paid_users'],
        'pending_requests': subscription_stats['pending_requests'],
        'monthly_revenue': monthly_revenue,
    }
    
    context = {
        'centers': centers,
        'moldpark_center': moldpark_center,
        'producers': producers,
        'moldpark_producer': moldpark_producer,
        'moldpark_orders': moldpark_orders,
        'molds': molds,
        'recent_messages': messages,
        'center_users': center_users,
        'producer_users': producer_users,
        'stats': stats,
        'terminated_networks': terminated_networks,
        'auto_assigned_centers': auto_assigned_centers,
        # Bildirim sistemi context'leri
        'notification_stats': notification_stats,
        'simple_notification_stats': simple_notification_stats,
        'system_health': system_health,
        'smart_suggestions': smart_suggestions,
        'unread_notifications': notification_stats['unread_notifications'] + simple_notification_stats['unread_simple_notifications'],
        # Abonelik yönetimi context'leri
        'pending_requests': pending_requests,
        'recent_processed_requests': recent_processed_requests,
        'subscription_stats': subscription_stats,
        'subscription_by_plan': subscription_by_plan,
        'trial_expired_users': trial_expired_users,
        'trial_warning_users': trial_warning_users,
    }
    return render(request, 'core/dashboard_admin.html', context)

@user_passes_test(lambda u: u.is_superuser)
def admin_approve_subscription_request(request, request_id):
    """Admin tarafından abonelik talebi onaylama - JSON response"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Geçersiz istek'}, status=405)
    
    try:
        subscription_request = get_object_or_404(SubscriptionRequest, id=request_id)
        
        if subscription_request.status != 'pending':
            return JsonResponse({
                'success': False,
                'error': 'Bu talep zaten işlenmiş'
            })
        
        admin_notes = request.POST.get('admin_notes', '')
        success = subscription_request.approve(request.user, admin_notes)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'{subscription_request.user.get_full_name()} kullanıcısının {subscription_request.plan.name} talebi onaylandı.'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Talep onaylanırken bir hata oluştu.'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@user_passes_test(lambda u: u.is_superuser)
def admin_reject_subscription_request(request, request_id):
    """Admin tarafından abonelik talebi reddetme - JSON response"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Geçersiz istek'}, status=405)
    
    try:
        subscription_request = get_object_or_404(SubscriptionRequest, id=request_id)
        
        if subscription_request.status != 'pending':
            return JsonResponse({
                'success': False,
                'error': 'Bu talep zaten işlenmiş'
            })
        
        admin_notes = request.POST.get('admin_notes', 'Talep reddedildi.')
        success = subscription_request.reject(request.user, admin_notes)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'{subscription_request.user.get_full_name()} kullanıcısının {subscription_request.plan.name} talebi reddedildi.'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Talep reddedilirken bir hata oluştu.'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def message_list(request):
    """Mesaj Listesi"""
    user = request.user
    
    # Gelen mesajlar
    if user.is_superuser:
        # Admin tüm mesajları görebilir
        received_messages = Message.objects.filter(
            Q(recipient=user) | 
            Q(is_broadcast=True) |
            Q(message_type__in=['center_to_admin', 'producer_to_admin'])
        ).select_related('sender', 'recipient').prefetch_related('recipients')
    else:
        # Merkez ve üreticiler sadece kendilerine gelen mesajları görebilir
        received_messages = Message.objects.filter(
            Q(recipient=user) | 
            Q(recipients__recipient=user)
        ).select_related('sender', 'recipient').distinct()
    
    # Gönderilen mesajlar
    sent_messages = Message.objects.filter(
        sender=user
    ).select_related('recipient').prefetch_related('recipients')
    
    # Filtreleme
    message_filter = request.GET.get('filter', 'received')
    search_query = request.GET.get('search', '')
    
    if message_filter == 'sent':
        messages_list = sent_messages
    else:
        messages_list = received_messages
    
    # Arama - silinmiş kullanıcıları da dikkate al
    if search_query:
        messages_list = messages_list.filter(
            Q(subject__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(sender__first_name__icontains=search_query) |
            Q(sender__last_name__icontains=search_query) |
            Q(sender__username__icontains=search_query)
        ).distinct()
    
    # Sayfalama
    paginator = Paginator(messages_list.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
    # Gelen mesajlar görüntülendiğinde otomatik olarak okundu işaretle
    if message_filter == 'received':
        # Direkt mesajları okundu olarak işaretle
        unread_direct_messages = received_messages.filter(
            recipient=user,
            is_read=False
        )
        for msg in unread_direct_messages:
            msg.mark_as_read()
        
        # Broadcast mesajları okundu olarak işaretle
        unread_broadcast_recipients = MessageRecipient.objects.filter(
            recipient=user,
            is_read=False,
            message__in=received_messages
        )
        for recipient in unread_broadcast_recipients:
            recipient.mark_as_read()
    
    # Her mesaj için kullanıcının okuma durumunu hesapla
    for message in messages_page:
        if message.is_broadcast:
            # Broadcast mesajlar için MessageRecipient kontrolü
            user_recipient = message.recipients.filter(recipient=user).first()
            message.user_is_read = user_recipient.is_read if user_recipient else False
        elif message.recipient == user:
            # Kullanıcı alıcı ise
            message.user_is_read = message.is_read
        else:
            # Kullanıcı gönderen ise
            message.user_is_read = True
    
    # İstatistikler - silinmiş kullanıcıları da dahil et
    stats = {
        'total_received': received_messages.count(),
        'unread_received': received_messages.filter(
            Q(is_read=False, recipient=user) |
            Q(recipients__recipient=user, recipients__is_read=False)
        ).distinct().count(),
        'total_sent': sent_messages.count(),
        'urgent_messages': received_messages.filter(
            Q(priority='urgent', is_read=False, recipient=user) |
            Q(priority='urgent', recipients__recipient=user, recipients__is_read=False)
        ).distinct().count(),
    }
    
    context = {
        'messages': messages_page,
        'message_filter': message_filter,
        'search_query': search_query,
        'stats': stats,
    }
    
    return render(request, 'core/message_list.html', context)

@login_required
def message_detail(request, pk):
    """Mesaj Detayı"""
    user = request.user
    
    # Mesajı al
    message = get_object_or_404(Message, pk=pk)
    
    # Yetki kontrolü
    can_view = False
    if user.is_superuser:
        can_view = True
    elif message.recipient == user or message.sender == user:
        can_view = True
    elif message.is_broadcast and message.recipients.filter(recipient=user).exists():
        can_view = True
    
    if not can_view:
        messages.error(request, 'Bu mesajı görüntüleme yetkiniz yok.')
        return redirect('core:message_list')
    
    # Mesajı okundu olarak işaretle
    if message.recipient == user and not message.is_read:
        message.mark_as_read()
    elif message.is_broadcast:
        recipient_obj = message.recipients.filter(recipient=user).first()
        if recipient_obj and not recipient_obj.is_read:
            recipient_obj.mark_as_read()
    
    # Cevap formu
    reply_form = None
    if message.can_reply(user):
        if request.method == 'POST':
            reply_form = MessageReplyForm(
                request.POST, 
                request.FILES,
                original_message=message,
                user=user
            )
            if reply_form.is_valid():
                reply = reply_form.save()
                
                # Bildirim gönder - alıcı kontrolü ekle
                if reply.recipient:
                    notify.send(
                        sender=user,
                        recipient=reply.recipient,
                        verb='mesajınıza cevap verdi',
                        action_object=reply,
                        description=f'Konu: {reply.subject}'
                    )
                
                messages.success(request, 'Cevabınız gönderildi.')
                return redirect('core:message_detail', pk=message.pk)
        else:
            reply_form = MessageReplyForm(original_message=message, user=user)
    
    # Cevapları al
    replies = message.replies.select_related('sender', 'recipient').order_by('created_at')
    
    # Toplu mesaj istatistikleri
    broadcast_stats = None
    if message.is_broadcast:
        recipients = message.recipients.all()
        broadcast_stats = {
            'total_recipients': recipients.count(),
            'read_count': recipients.filter(is_read=True).count(),
            'unread_count': recipients.filter(is_read=False).count(),
        }
    
    context = {
        'message': message,
        'replies': replies,
        'reply_form': reply_form,
        'can_reply': message.can_reply(user),
        'broadcast_stats': broadcast_stats,
    }
    
    return render(request, 'core/message_detail.html', context)

@login_required
def message_create(request):
    """Mesaj oluşturma view'ı"""
    
    if request.method == 'POST':
        if request.user.is_superuser:
            form = AdminMessageForm(request.POST, request.FILES)
        else:
            form = MessageForm(request.POST, request.FILES, user=request.user)
            
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            
            # Admin mesajı ise
            if request.user.is_superuser:
                recipient_type = form.cleaned_data['recipient_type']
                specific_recipient = form.cleaned_data['specific_recipient']
                
                recipients = set()  # Duplicate önleme
                
                if recipient_type == 'single_center':
                    recipients.add(specific_recipient)
                    message.message_type = 'admin_to_center'
                elif recipient_type == 'single_producer':
                    recipients.add(specific_recipient)
                    message.message_type = 'admin_to_producer'
                elif recipient_type == 'all_centers':
                    recipients.update(User.objects.filter(center__isnull=False))
                    message.message_type = 'admin_to_center'
                elif recipient_type == 'all_producers':
                    recipients.update(User.objects.filter(producer__isnull=False))
                    message.message_type = 'admin_to_producer'
                elif recipient_type == 'all_users':
                    recipients.update(User.objects.filter(is_superuser=False))
                    message.message_type = 'admin_to_all'
                
                message.save()
                
                # Her alıcı için MessageRecipient oluştur
                for recipient in recipients:
                    MessageRecipient.objects.get_or_create(
                        message=message,
                        recipient=recipient
                    )
                    
                    # Bildirim gönder
                    notify.send(
                        sender=request.user,
                        recipient=recipient,
                        verb='yeni mesaj gönderdi',
                        description=message.subject,
                        target=message
                    )
                    # Basit bildirim (Zil ikonu)
                    from core.utils import send_message_notification
                    send_message_notification(
                        recipient,
                        'Yeni Mesaj',
                        f'Admin tarafından yeni bir mesaj aldınız: {message.subject}',
                        related_url=f'/messages/{message.id}/'
                    )
                
                messages.success(request, 'Mesaj başarıyla gönderildi.')
                return redirect('core:message_list')
                
            # Normal kullanıcı mesajı ise
            else:
                if hasattr(request.user, 'center'):
                    message.message_type = 'center_to_admin'
                elif hasattr(request.user, 'producer'):
                    message.message_type = 'producer_to_admin'
                
                message.save()
                
                # Admin'e MessageRecipient oluştur
                admin = User.objects.filter(is_superuser=True).first()
                if admin:
                    MessageRecipient.objects.get_or_create(
                        message=message,
                        recipient=admin
                    )
                    
                    # Admin'e bildirim gönder
                    notify.send(
                        sender=request.user,
                        recipient=admin,
                        verb='yeni mesaj gönderdi',
                        description=message.subject,
                        target=message
                    )
                    from core.utils import send_message_notification
                    send_message_notification(
                        admin,
                        'Yeni Mesaj',
                        f'Yeni bir kullanıcı mesajı aldınız: {message.subject}',
                        related_url=f'/messages/{message.id}/'
                    )
                
                messages.success(request, 'Mesajınız başarıyla gönderildi.')
                return redirect('core:message_list')
    else:
        if request.user.is_superuser:
            form = AdminMessageForm()
        else:
            form = MessageForm(user=request.user)
    
    # AJAX isteği ise form'u güncelle
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.user.is_superuser:
            form = AdminMessageForm(request.GET)
            return render(request, 'core/widgets/recipient_field.html', {'form': form})
    
    return render(request, 'core/message_create.html', {'form': form})

@login_required
def message_mark_read(request, pk):
    """Mesajı Okundu Olarak İşaretle"""
    user = request.user
    message = get_object_or_404(Message, pk=pk)
    
    # Yetki kontrolü
    if message.recipient == user:
        message.mark_as_read()
    elif message.is_broadcast:
        recipient_obj = message.recipients.filter(recipient=user).first()
        if recipient_obj:
            recipient_obj.mark_as_read()
    
    return JsonResponse({'success': True})

@login_required
def message_archive(request, pk):
    """Mesajı Arşivle"""
    user = request.user
    message = get_object_or_404(Message, pk=pk)
    
    # Yetki kontrolü
    if message.recipient == user or message.sender == user:
        message.is_archived = True
        message.save()
        messages.success(request, 'Mesaj arşivlendi.')
    
    return redirect('core:message_list')

@login_required
def message_delete(request, pk):
    """Mesajı Sil"""
    user = request.user
    message = get_object_or_404(Message, pk=pk)
    
    # Sadece gönderen silebilir
    if message.sender == user:
        message.delete()
        messages.success(request, 'Mesaj silindi.')
    else:
        messages.error(request, 'Bu mesajı silme yetkiniz yok.')
    
    return redirect('core:message_list')

def terms_of_service(request):
    """Kullanım Şartları"""
    return render(request, 'core/terms.html')

def privacy_policy(request):
    """Gizlilik Politikası"""
    return render(request, 'core/privacy.html')

def pricing(request):
    """Fiyatlandırma sayfası - Paket sistemi"""
    # Aktif paketleri göster (package ve single tipindeki planlar)
    packages = PricingPlan.objects.filter(
        is_active=True, 
        plan_type__in=['package', 'single']
    ).order_by('order')
    
    # Tek kalıp seçeneği
    single_plan = PricingPlan.objects.filter(
        is_active=True, 
        plan_type='single'
    ).first()
    
    context = {
        'plans': packages,
        'single_plan': single_plan,
        'packages': packages.filter(plan_type='package'),
    }
    
    # Giriş yapmış kullanıcı için ek bilgiler (bu kod zaten çalışmayacak ama template'ler için bırakıyoruz)
    if request.user.is_authenticated:
        # Kullanıcının mevcut aboneliği
        try:
            current_subscription = UserSubscription.objects.get(user=request.user)
            context['current_subscription'] = current_subscription
        except UserSubscription.DoesNotExist:
            context['current_subscription'] = None
        
        # Beklemede olan talepler
        pending_requests = SubscriptionRequest.objects.filter(
            user=request.user,
            status='pending'
        ).select_related('plan')
        context['pending_requests'] = pending_requests
        
        # Geçmiş talepler
        past_requests = SubscriptionRequest.objects.filter(
            user=request.user,
            status__in=['approved', 'rejected']
        ).select_related('plan').order_by('-created_at')[:5]
        context['past_requests'] = past_requests
    
    return render(request, 'core/pricing.html', context)

@login_required
def request_subscription(request):
    """Abonelik Talep Sayfası"""
    if request.method == 'POST':
        # Eğer pricing sayfasından plan_id geliyorsa direkt talep oluştur
        plan_id = request.POST.get('plan_id')
        if plan_id:
            try:
                plan = PricingPlan.objects.get(id=plan_id, is_active=True)
                
                # Mevcut abonelik kontrolü
                try:
                    current_subscription = UserSubscription.objects.get(user=request.user, status='active')
                    if current_subscription.plan == plan:
                        messages.info(request, 'Bu plana zaten abone durumdasınız.')
                        return redirect('core:pricing')
                except UserSubscription.DoesNotExist:
                    pass
                
                # Beklemede olan talep kontrolü
                existing_request = SubscriptionRequest.objects.filter(
                    user=request.user,
                    plan=plan,
                    status='pending'
                ).first()
                
                if existing_request:
                    messages.warning(request, 
                        f'{plan.name} planı için zaten beklemede olan bir talebiniz bulunuyor.')
                    return redirect('core:pricing')
                
                # Yeni talep oluştur
                subscription_request = SubscriptionRequest.objects.create(
                    user=request.user,
                    plan=plan,
                    user_notes=f'Fiyatlandırma sayfasından {plan.name} planı için talep gönderildi.',
                    status='pending'
                )
                
                messages.success(
                    request, 
                    f'🎉 {plan.name} planı için talebiniz başarıyla gönderildi! '
                    f'Admin onayından sonra e-posta ile bilgilendirileceksiniz.'
                )
                return redirect('core:subscription_requests')
                
            except PricingPlan.DoesNotExist:
                messages.error(request, 'Seçilen plan bulunamadı.')
                return redirect('core:pricing')
        
        # Normal form submission
        form = SubscriptionRequestForm(request.POST, user=request.user)
        if form.is_valid():
            subscription_request = form.save()
            messages.success(
                request, 
                f'{subscription_request.plan.name} planı için talebiniz başarıyla gönderildi. Admin onayından sonra bilgilendirileceksiniz.'
            )
            return redirect('core:subscription_requests')
    else:
        form = SubscriptionRequestForm(user=request.user)
    
    # Mevcut abonelik bilgisi
    current_subscription = None
    try:
        current_subscription = UserSubscription.objects.get(user=request.user)
    except UserSubscription.DoesNotExist:
        pass
    
    # Beklemede olan talepler
    pending_requests = SubscriptionRequest.objects.filter(
        user=request.user,
        status='pending'
    ).select_related('plan')
    
    # Mevcut planlar
    available_plans = PricingPlan.objects.filter(is_active=True).exclude(plan_type='trial').order_by('price_usd')
    
    return render(request, 'core/request_subscription.html', {
        'form': form,
        'current_subscription': current_subscription,
        'pending_requests': pending_requests,
        'available_plans': available_plans
    })

@login_required
def subscription_requests(request):
    """Kullanıcının Abonelik Talepleri"""
    requests = SubscriptionRequest.objects.filter(
        user=request.user
    ).select_related('plan', 'processed_by').order_by('-created_at')
    
    # Mevcut abonelik
    current_subscription = None
    try:
        current_subscription = UserSubscription.objects.get(user=request.user)
    except UserSubscription.DoesNotExist:
        pass
    
    return render(request, 'core/subscription_requests.html', {
        'requests': requests,
        'current_subscription': current_subscription
    })

@login_required
def subscription_request_cancel(request, request_id):
    """Beklemede olan talebi iptal et"""
    subscription_request = get_object_or_404(
        SubscriptionRequest,
        id=request_id,
        user=request.user,
        status='pending'
    )
    
    if request.method == 'POST':
        subscription_request.delete()
        messages.success(request, 'Abonelik talebiniz iptal edildi.')
        return redirect('core:subscription_requests')
    
    return render(request, 'core/subscription_request_cancel.html', {
        'subscription_request': subscription_request
    })

@login_required
def subscribe_to_plan(request, plan_id):
    """Plana abone ol"""
    plan = get_object_or_404(PricingPlan, id=plan_id, is_active=True)
    
    # Mevcut aboneliği kontrol et
    try:
        current_subscription = UserSubscription.objects.get(user=request.user, status='active')
        if current_subscription.plan == plan:
            messages.info(request, 'Bu plana zaten abone durumdasınız.')
            return redirect('core:pricing')
        else:
            # Mevcut aboneliği iptal et
            current_subscription.status = 'cancelled'
            current_subscription.save()
    except UserSubscription.DoesNotExist:
        pass
    
    # Yeni abonelik oluştur
    if plan.is_monthly:
        end_date = timezone.now() + timedelta(days=30)
    else:
        end_date = None
    
    subscription = UserSubscription.objects.create(
        user=request.user,
        plan=plan,
        start_date=timezone.now(),
        end_date=end_date,
        status='active',
        amount_paid=plan.price_usd,
        currency='USD'
    )
    
    # Ödeme kaydı oluştur
    PaymentHistory.objects.create(
        user=request.user,
        subscription=subscription,
        amount=plan.price_usd,
        currency='USD',
        payment_type='subscription' if plan.is_monthly else 'pay_per_use',
        status='completed',  # Demo için direkt tamamlandı
        payment_method='Demo Payment',
        transaction_id=f'TXN_{timezone.now().strftime("%Y%m%d%H%M%S")}',
        notes=f'{plan.name} planına abonelik'
    )
    
    messages.success(request, f'{plan.name} planına başarıyla abone oldunuz!')
    return redirect('core:pricing')

@user_passes_test(lambda u: u.is_superuser)
def subscription_requests(request):
    """Admin: Abonelik Talepleri Listesi"""
    from core.models import SubscriptionRequest
    
    # Filtreleme
    status_filter = request.GET.get('status', 'all')
    
    requests = SubscriptionRequest.objects.select_related('user', 'plan', 'processed_by').order_by('-created_at')
    
    if status_filter != 'all':
        requests = requests.filter(status=status_filter)
    
    # İstatistikler
    all_requests = SubscriptionRequest.objects.all()
    pending_count = all_requests.filter(status='pending').count()
    approved_count = all_requests.filter(status='approved').count()
    rejected_count = all_requests.filter(status='rejected').count()
    total_count = all_requests.count()
    
    context = {
        'requests': requests,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_count': total_count,
    }
    
    return render(request, 'core/subscription_requests.html', context)


@user_passes_test(lambda u: u.is_superuser)
def approve_subscription_request(request, request_id):
    """Admin: Abonelik Talebini Onayla"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Geçersiz istek'}, status=405)
    
    try:
        from core.models import SubscriptionRequest, UserSubscription, SimpleNotification
        
        subscription_request = get_object_or_404(SubscriptionRequest, id=request_id)
        
        if subscription_request.status != 'pending':
            return JsonResponse({
                'success': False,
                'error': 'Bu talep zaten işlenmiş'
            })
        
        # Abonelik talebini onayla
        subscription_request.status = 'approved'
        subscription_request.processed_at = timezone.now()
        subscription_request.processed_by = request.user
        subscription_request.save()
        
        # Kullanıcının aboneliğini aktif yap
        subscription = UserSubscription.objects.filter(user=subscription_request.user).first()
        if subscription:
            subscription.status = 'active'
            subscription.start_date = timezone.now()
            subscription.end_date = None  # Sınırsız
            subscription.save()
        
        # Kullanıcıya bildirim gönder
        center_name = subscription_request.user.center.name if hasattr(subscription_request.user, 'center') else subscription_request.user.username
        SimpleNotification.objects.create(
            user=subscription_request.user,
            title='🎉 Aboneliğiniz Onaylandı!',
            message=f'Tebrikler! Abonelik talebiniz onaylandı. Artık sistemi sınırsız kullanabilirsiniz. İyi çalışmalar dileriz!',
            notification_type='success',
            related_url='/center/dashboard/'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{center_name} adlı merkezin aboneliği başarıyla onaylandı.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@user_passes_test(lambda u: u.is_superuser)
def reject_subscription_request(request, request_id):
    """Admin: Abonelik Talebini Reddet"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Geçersiz istek'}, status=405)
    
    try:
        import json
        from core.models import SubscriptionRequest, SimpleNotification
        
        subscription_request = get_object_or_404(SubscriptionRequest, id=request_id)
        
        if subscription_request.status != 'pending':
            return JsonResponse({
                'success': False,
                'error': 'Bu talep zaten işlenmiş'
            })
        
        # JSON verisini al
        data = json.loads(request.body)
        reason = data.get('reason', 'Belirtilmedi')
        
        # Abonelik talebini reddet
        subscription_request.status = 'rejected'
        subscription_request.processed_at = timezone.now()
        subscription_request.processed_by = request.user
        subscription_request.admin_notes = reason
        subscription_request.save()
        
        # Kullanıcıya bildirim gönder
        center_name = subscription_request.user.center.name if hasattr(subscription_request.user, 'center') else subscription_request.user.username
        SimpleNotification.objects.create(
            user=subscription_request.user,
            title='❌ Abonelik Talebi Reddedildi',
            message=f'Üzgünüz, abonelik talebiniz reddedildi.\n\nRed Sebebi: {reason}\n\nDetaylı bilgi için lütfen bizimle iletişime geçin.',
            notification_type='error',
            related_url='/contact/'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{center_name} adlı merkezin aboneliği reddedildi.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def subscription_dashboard(request):
    """Abonelik yönetim paneli - Paket satın alma ve ödeme"""
    # Paket satın alma işlemi
    if request.method == 'POST' and 'purchase_package' in request.POST:
        form = PackagePurchaseForm(request.POST)
        if form.is_valid():
            plan = form.cleaned_data['plan']
            payment_method = form.cleaned_data['payment_method']
            
            # Mevcut abonelik kontrolü
            try:
                current_subscription = UserSubscription.objects.get(user=request.user, status='active')
                # Mevcut aboneliği iptal et
                current_subscription.status = 'cancelled'
                current_subscription.save()
            except UserSubscription.DoesNotExist:
                pass
            except UserSubscription.MultipleObjectsReturned:
                # Birden fazla aktif abonelik varsa hepsini iptal et
                UserSubscription.objects.filter(user=request.user, status='active').update(status='cancelled')
            
            # Yeni abonelik oluştur (paket satın alma)
            if plan.plan_type == 'package':
                # Paket için abonelik oluştur
                new_subscription = UserSubscription.objects.create(
                    user=request.user,
                    plan=plan,
                    status='active',
                    monthly_fee_paid=True,  # Abonelik aktif
                )
                
                # Eğer paket türüyse PurchasedPackage kaydı oluştur
                if plan.plan_type == 'package':
                    from .models import PurchasedPackage
                    PurchasedPackage.objects.create(
                        user=request.user,
                        package=plan,
                        purchase_price=plan.price_try,
                        total_credits=plan.monthly_model_limit,
                    )
                
                # Ödeme kaydı oluştur
                payment_history = PaymentHistory.objects.create(
                    user=request.user,
                    subscription=new_subscription,
                    amount=plan.price_try,
                    currency='TRY',
                    payment_type='subscription',
                    payment_method='Kredi Kartı' if payment_method == 'credit_card' else 'Havale/EFT',
                    status='completed' if payment_method == 'credit_card' else 'pending',
                    notes=f'{plan.name} paketi satın alındı - {payment_method}'
                )
                
                # Fatura oluştur
                try:
                    from core.models import Invoice, PricingConfiguration
                    
                    pricing = PricingConfiguration.get_active()
                    center = None
                    if hasattr(request.user, 'center'):
                        center = request.user.center
                    
                    # Fatura numarası oluştur
                    invoice_number = f"PKG-{request.user.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    # Fatura oluştur
                    invoice = Invoice.objects.create(
                        invoice_number=invoice_number,
                        invoice_type='center_admin_invoice',
                        user=request.user,
                        issued_by_center=center,
                        issue_date=timezone.now().date(),
                        due_date=(timezone.now() + timedelta(days=15)).date(),
                        issued_by=request.user,
                        # Paket bilgileri
                        physical_mold_count=plan.monthly_model_limit,
                        physical_mold_unit_price=plan.per_mold_price_try,
                        physical_mold_cost=plan.price_try,
                        # Toplam tutar
                        total_amount=plan.price_try,
                        subtotal=plan.price_try,
                        # KDV hesaplama
                        vat_rate=pricing.vat_rate,
                        subtotal_without_vat=plan.price_try / (Decimal('1') + (pricing.vat_rate / Decimal('100'))),
                        vat_amount=plan.price_try - (plan.price_try / (Decimal('1') + (pricing.vat_rate / Decimal('100')))),
                        total_with_vat=plan.price_try,
                        # Komisyonlar
                        moldpark_service_fee_rate=pricing.moldpark_commission_rate,
                        credit_card_fee_rate=pricing.credit_card_commission_rate,
                        moldpark_service_fee=pricing.calculate_moldpark_fee(plan.price_try),
                        credit_card_fee=pricing.calculate_credit_card_fee(plan.price_try) if payment_method == 'credit_card' else Decimal('0.00'),
                        # Durum
                        status='paid' if payment_method == 'credit_card' else 'issued',
                        payment_date=timezone.now().date() if payment_method == 'credit_card' else None,
                        # Notlar
                        notes=f'{plan.name} paketi satın alma faturası. Paket içeriği: {plan.monthly_model_limit} kalıp.',
                        breakdown_data={
                            'package_name': plan.name,
                            'package_id': plan.id,
                            'mold_count': plan.monthly_model_limit,
                            'unit_price': str(plan.per_mold_price_try),
                            'total_price': str(plan.price_try),
                            'payment_method': payment_method,
                            'payment_history_id': payment_history.id,
                        }
                    )
                    
                    # Transaction oluştur
                    from core.models import Transaction
                    Transaction.objects.create(
                        user=request.user,
                        center=center,
                        invoice=invoice,
                        transaction_type='center_invoice_payment',
                        amount=plan.price_try,
                        description=f'{plan.name} paketi satın alma faturası: {invoice_number}',
                        reference_id=invoice_number,
                        payment_method='Kredi Kartı' if payment_method == 'credit_card' else 'Havale/EFT',
                        status='completed' if payment_method == 'credit_card' else 'pending',
                    )
                    
                    # Paket satın alındığında üretici faturası oluştur
                    # Paket fiyatı üzerinden üretici faturası kesilir (kullanılan kalıp sayısına bakılmaksızın)
                    try:
                        from producer.models import ProducerNetwork
                        # Bu merkezin bağlı olduğu üretici ağlarını bul
                        active_networks = ProducerNetwork.objects.filter(
                            center=center,
                            status='active'
                        ).select_related('producer')
                        
                        if active_networks.exists():
                            # İlk aktif üretici ağını kullan (veya tüm üreticilere dağıtılabilir)
                            primary_network = active_networks.first()
                            producer = primary_network.producer
                            
                            # Üretici faturası oluştur - Paket fiyatı üzerinden
                            # Paket satın alındığında üretici merkez bu satın almayı karşılayacak olan taraftır
                            # MoldPark Hizmet Bedeli (%6.5) KDV DAHİL brüt tutar üzerinden alınır
                            producer_moldpark_fee = pricing.calculate_moldpark_fee(plan.price_try)
                            producer_cc_fee = pricing.calculate_credit_card_fee(plan.price_try) if payment_method == 'credit_card' else Decimal('0.00')
                            
                            # Üreticiye ödeme: KDV DAHİL brüt tutar - MoldPark komisyonu
                            producer_net_amount = plan.price_try - producer_moldpark_fee
                            
                            # KDV hesaplamaları (bilgi amaçlı)
                            vat_multiplier = Decimal('1') + (pricing.vat_rate / Decimal('100'))
                            package_amount_without_vat = plan.price_try / vat_multiplier
                            package_vat_amount = plan.price_try - package_amount_without_vat
                            
                            producer_invoice = Invoice.objects.create(
                                invoice_number=Invoice.generate_invoice_number('producer_invoice'),
                                invoice_type='producer_invoice',
                                producer=producer,
                                user=producer.user,
                                issued_by=request.user,
                                issued_by_producer=producer,
                                issue_date=timezone.now().date(),
                                due_date=(timezone.now() + timedelta(days=30)).date(),
                                status='issued',
                                # Paket bilgileri
                                physical_mold_count=plan.monthly_model_limit,
                                # Paket fiyatı (KDV dahil brüt tutar) - Üretici merkez bu satın almayı karşılayacak olan taraftır
                                producer_gross_revenue=plan.price_try,
                                # Üreticiye ödeme: KDV DAHİL brüt tutar - MoldPark komisyonu
                                producer_net_revenue=producer_net_amount,
                                net_amount=producer_net_amount,
                                moldpark_service_fee=producer_moldpark_fee,
                                credit_card_fee=producer_cc_fee,
                                moldpark_service_fee_rate=pricing.moldpark_commission_rate,
                                credit_card_fee_rate=pricing.credit_card_commission_rate,
                                total_amount=plan.price_try,
                                vat_rate=pricing.vat_rate,
                                subtotal_without_vat=package_amount_without_vat,
                                vat_amount=package_vat_amount,
                                breakdown_data={
                                    'package_invoice_number': invoice_number,
                                    'package_name': plan.name,
                                    'package_id': plan.id,
                                    'package_price': str(plan.price_try),
                                    'mold_count': plan.monthly_model_limit,
                                    'unit_price': str(plan.per_mold_price_try),
                                    'center_id': center.id,
                                    'center_name': center.name,
                                    'payment_method': payment_method,
                                    'note': f'{plan.name} paketi satın alındığında paket fiyatı üzerinden üretici faturası oluşturuldu. Kullanılan kalıp sayısına bakılmaksızın paket fiyatı üzerinden hesaplanmıştır.',
                                },
                                notes=f'{plan.name} paketi satın alındığında paket fiyatı üzerinden üretici faturası. Paket içeriği: {plan.monthly_model_limit} kalıp.',
                            )
                            
                            logger.info(f"Paket satın alındığında üretici faturası oluşturuldu: {producer_invoice.invoice_number} - Üretici: {producer.company_name} - Tutar: {plan.price_try} TL")
                    except Exception as e:
                        logger.error(f"Paket satın alındığında üretici faturası oluşturulurken hata: {e}")
                        # Üretici faturası oluşturulamasa bile işleme devam et
                    
                except Exception as e:
                    logger.error(f"Paket satın alma faturası oluşturulurken hata: {e}")
                    # Fatura oluşturulamasa bile işleme devam et
                
                if payment_method == 'credit_card':
                    messages.success(request, f'{plan.name} paketi başarıyla satın alındı! Paketiniz aktif. Faturanız oluşturuldu.')
                else:
                    messages.info(request, f'{plan.name} paketi için ödeme talebi oluşturuldu. Havale/EFT ile ödeme yaptıktan sonra paketiniz aktif olacak. Faturanız oluşturuldu.')
                
                return redirect('core:subscription_dashboard')
            else:
                # Tek kalıp için abonelik oluştur
                new_subscription = UserSubscription.objects.create(
                    user=request.user,
                    plan=plan,
                    status='active',
                )
                
                messages.success(request, 'Tek kalıp seçeneği aktif edildi.')
                return redirect('core:subscription_dashboard')
        else:
            messages.error(request, 'Form hataları var. Lütfen kontrol edin.')
    
    try:
        subscription = UserSubscription.objects.filter(user=request.user, status='active').order_by('-created_at').first()
        if subscription:
            pass  # Paket hakları artık PurchasedPackage'de takip edilir
            
            # Subscription'ı refresh et
            subscription.refresh_from_db()
    except UserSubscription.DoesNotExist:
        subscription = None
    
    # Ödeme geçmişi
    payments = PaymentHistory.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Aktif paketleri al (package ve single tipindeki planlar)
    packages = PricingPlan.objects.filter(
        is_active=True, 
        plan_type__in=['package', 'single']
    ).order_by('order')
    
    # Tek kalıp seçeneği
    single_plan = PricingPlan.objects.filter(
        is_active=True, 
        plan_type='single'
    ).first()
    
    # Paket satın alma formu
    purchase_form = PackagePurchaseForm()
    
    # Aktif ve geçmiş paket satın almalarını al
    from .models import PurchasedPackage
    active_purchased_package = PurchasedPackage.objects.filter(user=request.user, status='active').first()
    all_purchased_packages = PurchasedPackage.objects.filter(user=request.user).order_by('-purchase_date')
    
    context = {
        'subscription': subscription,
        'payments': payments,
        'packages': packages.filter(plan_type='package'),
        'single_plan': single_plan,
        'purchase_form': purchase_form,
        'purchased_package': active_purchased_package,  # Aktif paket
        'purchased_packages': all_purchased_packages,   # Tüm paket satın almalarının geçmişi
    }
    
    return render(request, 'core/subscription_dashboard.html', context)

@login_required
def simple_notifications(request):
    """Kullanıcının bildirimlerini listele"""
    notifications = get_user_notifications(request.user, limit=50)
    unread_count = get_unread_count(request.user)
    
    return render(request, 'core/simple_notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })

@login_required
def notification_redirect(request, notification_id):
    """Bildirimi okundu işaretle ve ilgili sayfaya yönlendir"""
    try:
        notification = SimpleNotification.objects.get(
            id=notification_id,
            user=request.user
        )
        
        # Otomatik okundu işaretle
        if not notification.is_read:
            notification.mark_as_read()
        
        # İlgili URL varsa yönlendir
        if notification.related_url:
            return redirect(notification.related_url)
        else:
            # İlgili URL yoksa bildirimler sayfasına dön
            messages.info(request, f'Bildirim: {notification.title}')
            return redirect('core:simple_notifications')
            
    except SimpleNotification.DoesNotExist:
        messages.error(request, 'Bildirim bulunamadı.')
        return redirect('core:simple_notifications')

@login_required
def mark_notification_as_read(request, notification_id):
    """Bildirimi okundu olarak işaretle"""
    try:
        notification = SimpleNotification.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.mark_as_read()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'unread_count': get_unread_count(request.user)
            })
        
        return redirect('core:simple_notifications')
        
    except SimpleNotification.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Bildirim bulunamadı'})
        messages.error(request, 'Bildirim bulunamadı.')
        return redirect('core:simple_notifications')

@login_required 
def mark_all_notifications_read(request):
    """Tüm bildirimleri okundu olarak işaretle"""
    if request.method == 'POST':
        mark_all_as_read(request.user)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'unread_count': get_unread_count(request.user)
            })
        
        messages.success(request, 'Tüm bildirimler okundu olarak işaretlendi.')
    
    return redirect('core:simple_notifications')

@login_required
def delete_notification(request, notification_id):
    """Bildirimi sil"""
    try:
        notification = SimpleNotification.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'unread_count': get_unread_count(request.user)
            })
        
        messages.success(request, 'Bildirim silindi.')
        return redirect('core:simple_notifications')
        
    except SimpleNotification.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Bildirim bulunamadı'})
        messages.error(request, 'Bildirim bulunamadı.')
        return redirect('core:simple_notifications')

def features(request):
    """Özellikler sayfasını görüntüler."""
    return render(request, 'core/features.html')

def help_center(request):
    """Yardım merkezi sayfası"""
    try:
        return render(request, 'core/help_center.html')
    except Exception as e:
        logger.error(f"Help Center Error: {e}")
        messages.error(request, "Yardım merkezi sayfasına erişilirken bir hata oluştu.")
        return redirect('core:home')

def documentation(request):
    """Dokümantasyon sayfası"""
    return render(request, 'core/documentation.html')

def test_language(request):
    """Dil değiştirici test sayfası"""
    return render(request, 'test_language.html')


# ============================================
# ADMIN FİNANS YÖNETİMİ VİEW'LARI
# ============================================

@staff_member_required
def admin_financial_dashboard(request):
    """Admin Finans Dashboard - Tüm sistemi kapsayan finansal görünüm"""
    try:
        from decimal import Decimal
        from django.db.models import Sum, Count
        from datetime import date, timedelta

        # Tarih filtreleri
        today = date.today()
        current_month_start = date(today.year, today.month, 1)
        last_month_start = current_month_start - timedelta(days=30)
        last_month_end = current_month_start - timedelta(days=1)

        # === GENEL İSTATİSTİKLER ===
        total_centers = User.objects.filter(center__isnull=False).count()
        total_producers = Producer.objects.filter(is_active=True).count()
        total_molds = EarMold.objects.count()
        completed_molds = EarMold.objects.filter(status__in=['completed', 'delivered']).count()

        # === BU AY GELİRLER ===
        current_month_revenue = Decimal('0.00')

        # Center faturalarından gelen gelir (sistem kullanım + fiziksel kalıp)
        center_invoices = Invoice.objects.filter(
            invoice_type__startswith='center',
            issue_date__gte=current_month_start,
            status='paid'
        )

        for invoice in center_invoices:
            current_month_revenue += invoice.total_deductions  # MoldPark'a giden kısım

        # Producer ödemelerinden gelen gelir (komisyonlar)
        producer_invoices = Invoice.objects.filter(
            invoice_type__startswith='producer',
            issue_date__gte=current_month_start,
            status='paid'
        )

        for invoice in producer_invoices:
            current_month_revenue += invoice.total_deductions  # MoldPark komisyonları

        # === ÖDENMEMİŞ TUTARLAR ===
        pending_center_invoices = Invoice.objects.filter(
            invoice_type__startswith='center',
            status__in=['issued', 'sent']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        pending_producer_payments = Invoice.objects.filter(
            invoice_type__startswith='producer',
            status__in=['issued', 'sent']
        ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')

        # === SON 6 AY GELİR TRENDİ ===
        revenue_trend = []
        for i in range(5, -1, -1):
            month_date = current_month_start - timedelta(days=30 * i)
            month_start = date(month_date.year, month_date.month, 1)
            if month_date.month == 12:
                month_end = date(month_date.year + 1, 1, 1)
            else:
                month_end = date(month_date.year + 1, month_date.month + 1, 1)

            month_revenue = Decimal('0.00')

            # Center faturalarından
            center_monthly = Invoice.objects.filter(
                invoice_type__startswith='center',
                issue_date__gte=month_start,
                issue_date__lt=month_end,
                status='paid'
            ).aggregate(total=Sum('total_deductions'))['total'] or Decimal('0.00')

            # Producer faturalarından
            producer_monthly = Invoice.objects.filter(
                invoice_type__startswith='producer',
                issue_date__gte=month_start,
                issue_date__lt=month_end,
                status='paid'
            ).aggregate(total=Sum('total_deductions'))['total'] or Decimal('0.00')

            month_revenue = center_monthly + producer_monthly

            revenue_trend.append({
                'month': month_date.strftime('%Y-%m'),
                'month_name': month_date.strftime('%B %Y'),
                'revenue': month_revenue
            })

        # === EN FAZLA GELİR GETİREN MERKEZLER ===
        top_centers = []
        centers = User.objects.filter(center__isnull=False)
        for center_user in centers:
            center_revenue = Decimal('0.00')
            center_invoices = Invoice.objects.filter(
                user=center_user,
                status='paid'
            )
            for invoice in center_invoices:
                center_revenue += invoice.total_deductions

            if center_revenue > 0:
                top_centers.append({
                    'center': center_user.center,
                    'revenue': center_revenue
                })

        top_centers = sorted(top_centers, key=lambda x: x['revenue'], reverse=True)[:10]

        # === EN FAZLA KAZANÇ GETİREN ÜRETİCİLER ===
        top_producers = []
        producers = Producer.objects.filter(is_active=True)
        for producer in producers:
            earnings = producer.get_total_earnings()
            moldpark_share = earnings['moldpark_fee'] + earnings['credit_card_fee']

            if moldpark_share > 0:
                top_producers.append({
                    'producer': producer,
                    'moldpark_revenue': moldpark_share,
                    'total_orders': earnings['total_orders']
                })

        top_producers = sorted(top_producers, key=lambda x: x['moldpark_revenue'], reverse=True)[:10]

        context = {
            # Genel İstatistikler
            'total_centers': total_centers,
            'total_producers': total_producers,
            'total_molds': total_molds,
            'completed_molds': completed_molds,

            # Finansal Özet
            'current_month_revenue': current_month_revenue,
            'pending_center_invoices': pending_center_invoices,
            'pending_producer_payments': pending_producer_payments,
            'total_pending_amount': pending_center_invoices + pending_producer_payments,

            # Trendler
            'revenue_trend': revenue_trend,

            # Top Listeler
            'top_centers': top_centers,
            'top_producers': top_producers,
        }

        return render(request, 'core/admin_financial_dashboard.html', context)

    except Exception as e:
        logger.error(f"Admin Financial Dashboard Error: {e}")
        messages.error(request, 'Finans dashboard yüklenirken hata oluştu.')
        return redirect('admin:index')


@staff_member_required
def admin_invoice_management(request):
    """Admin Fatura Yönetimi - Tüm faturaları görüntüle ve yönet"""
    try:
        from django.core.paginator import Paginator

        # Filtreler
        status_filter = request.GET.get('status', '')
        type_filter = request.GET.get('type', '')
        search_query = request.GET.get('search', '')

        invoices = Invoice.objects.select_related('user', 'producer', 'issued_by').order_by('-issue_date')

        # Filtreleme
        if status_filter:
            invoices = invoices.filter(status=status_filter)
        if type_filter:
            invoices = invoices.filter(invoice_type__icontains=type_filter)
        if search_query:
            invoices = invoices.filter(
                models.Q(invoice_number__icontains=search_query) |
                models.Q(user__first_name__icontains=search_query) |
                models.Q(user__last_name__icontains=search_query) |
                models.Q(user__center__name__icontains=search_query) |
                models.Q(producer__company_name__icontains=search_query)
            )

        # Sayfalama
        paginator = Paginator(invoices, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'status_filter': status_filter,
            'type_filter': type_filter,
            'search_query': search_query,
            'status_choices': Invoice.STATUS_CHOICES,
            'type_choices': Invoice.INVOICE_TYPE_CHOICES,
        }

        return render(request, 'core/admin_invoice_management.html', context)

    except Exception as e:
        logger.error(f"Admin Invoice Management Error: {e}")
        messages.error(request, 'Fatura yönetimi sayfası yüklenirken hata oluştu.')
        return redirect('core:admin_financial_dashboard')


@staff_member_required
def admin_generate_invoices(request):
    """Admin Otomatik Fatura Oluşturma"""
    try:
        from datetime import date
        from decimal import Decimal

        if request.method == 'POST':
            invoice_type = request.POST.get('invoice_type')
            target_date = request.POST.get('target_date')

            if not target_date:
                target_date = date.today()

            generated_count = 0

            if invoice_type in ['center', 'all']:
                # Center faturaları oluştur
                centers = User.objects.filter(center__isnull=False)
                for center_user in centers:
                    try:
                        # Mevcut ay için fatura var mı kontrol et
                        current_month = date(target_date.year, target_date.month, 1)
                        existing_invoice = Invoice.objects.filter(
                            user=center_user,
                            invoice_type='center_monthly',
                            issue_date__year=current_month.year,
                            issue_date__month=current_month.month
                        ).exists()

                        if not existing_invoice:
                            # Abonelik kontrolü
                            try:
                                subscription = center_user.subscription
                                if subscription and subscription.status == 'active':
                                    # Fatura oluştur
                                    invoice = Invoice.objects.create(
                                        invoice_number=f"INV-C-{center_user.id}-{current_month.strftime('%Y%m')}",
                                        invoice_type='center_monthly',
                                        user=center_user,
                                        issue_date=current_month,
                                        due_date=current_month.replace(day=28),  # Ay sonu
                                        issued_by=request.user
                                    )

                                    # Faturayı hesapla
                                    invoice.calculate_center_invoice(subscription)
                                    invoice.save()
                                    generated_count += 1

                            except:
                                continue

                    except Exception as e:
                        logger.error(f"Center invoice generation error for {center_user}: {e}")
                        continue

            if invoice_type in ['producer', 'all']:
                # Producer faturaları oluştur
                producers = Producer.objects.filter(is_active=True, is_verified=True)
                for producer in producers:
                    try:
                        # Mevcut ay için fatura var mı kontrol et
                        current_month = date(target_date.year, target_date.month, 1)
                        existing_invoice = Invoice.objects.filter(
                            producer=producer,
                            invoice_type='producer_monthly',
                            issue_date__year=current_month.year,
                            issue_date__month=current_month.month
                        ).exists()

                        if not existing_invoice:
                            # Kazanç var mı kontrol et
                            monthly_revenue = producer.get_monthly_revenue(current_month.year, current_month.month)
                            if monthly_revenue > 0:
                                # Fatura oluştur
                                invoice = Invoice.objects.create(
                                    invoice_number=f"INV-P-{producer.id}-{current_month.strftime('%Y%m')}",
                                    invoice_type='producer_monthly',
                                    user=producer.user,
                                    producer=producer,
                                    issue_date=current_month,
                                    due_date=current_month.replace(day=28),  # Ay sonu
                                    issued_by=request.user
                                )

                                # Faturayı hesapla
                                invoice.calculate_producer_invoice(producer)
                                invoice.save()
                                generated_count += 1

                    except Exception as e:
                        logger.error(f"Producer invoice generation error for {producer}: {e}")
                        continue

            messages.success(request, f'{generated_count} adet fatura başarıyla oluşturuldu.')
            return redirect('core:admin_invoice_management')

        context = {
            'today': date.today().strftime('%Y-%m-%d')
        }

        return render(request, 'core/admin_generate_invoices.html', context)

    except Exception as e:
        logger.error(f"Admin Generate Invoices Error: {e}")
        messages.error(request, 'Fatura oluşturma işlemi sırasında hata oluştu.')
        return redirect('core:admin_financial_dashboard')


@staff_member_required
def admin_invoice_detail(request, invoice_id):
    """Admin Fatura Detayı"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)

        if request.method == 'POST':
            action = request.POST.get('action')

            if action == 'mark_sent':
                invoice.mark_as_sent(request.user)
                messages.success(request, 'Fatura gönderildi olarak işaretlendi.')

            elif action == 'mark_paid':
                payment_method = request.POST.get('payment_method', 'bank_transfer')
                transaction_id = request.POST.get('transaction_id', '')
                invoice.mark_as_paid(payment_method, transaction_id)
                messages.success(request, 'Fatura ödendi olarak işaretlendi.')

            elif action == 'mark_overdue':
                if invoice.is_overdue():
                    invoice.status = 'overdue'
                    invoice.save()
                    messages.success(request, 'Fatura vadesi geçmiş olarak işaretlendi.')
                else:
                    messages.warning(request, 'Fatura henüz vadesi geçmiş değil.')

            return redirect('core:admin_invoice_detail', invoice_id=invoice.id)

        context = {
            'invoice': invoice,
            'transactions': invoice.transactions.all(),
            'commissions': invoice.commissions.all(),
        }

        return render(request, 'core/admin_invoice_detail.html', context)

    except Exception as e:
        logger.error(f"Admin Invoice Detail Error: {e}")
        messages.error(request, 'Fatura detayı yüklenirken hata oluştu.')
        return redirect('core:admin_invoice_management')