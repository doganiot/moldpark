from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import ContactMessage, Message, MessageRecipient, PricingPlan, UserSubscription, PaymentHistory, SimpleNotification, SubscriptionRequest
from .forms import ContactForm, MessageForm, AdminMessageForm, MessageReplyForm, SubscriptionRequestForm
from django.views.generic import TemplateView
from django.contrib.auth.decorators import user_passes_test, login_required
from center.models import Center
from mold.models import EarMold
from accounts.forms import CustomSignupForm
from django.db.models import Q, Count, Avg
from django.contrib.auth.models import User
from producer.models import Producer
from notifications.signals import notify
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta
import json
import logging
from .smart_notifications import SmartNotificationManager
from .utils import get_user_notifications, get_unread_count, mark_all_as_read, send_notification

def home(request):
    # Fiyatlandırma planlarını al
    plans = PricingPlan.objects.filter(is_active=True).order_by('price_usd')
    
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
        print(f"DEBUG - Üretici puanları alınırken hata: {e}")
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
            'plans': plans
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
        'plans': plans
    })

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mesajınız başarıyla gönderildi.')
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
    # Import Producer modeli burada yapalım
    try:
        from producer.models import Producer, ProducerOrder, ProducerNetwork
        producers = Producer.objects.all()
        
        # MoldPark üretim merkezini bul
        moldpark_producer = Producer.objects.filter(
            company_name='MoldPark Üretim Merkezi'
        ).first()
        
        # DEBUG: Print etmek için
        print(f"DEBUG - MoldPark Producer: {moldpark_producer}")
        print(f"DEBUG - Producer count: {producers.count()}")
        if moldpark_producer:
            print(f"DEBUG - MoldPark Company: {moldpark_producer.company_name}")
        
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
            
    except ImportError as e:
        print(f"DEBUG - Import Error: {e}")
        producers = []
        moldpark_producer = None
        moldpark_orders = []
        terminated_networks = []
        auto_assigned_centers = []
    except Exception as e:
        print(f"DEBUG - Other Error: {e}")
        producers = []
        moldpark_producer = None
        moldpark_orders = []
        terminated_networks = []
        auto_assigned_centers = []
    
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
    """Admin tarafından abonelik talebi onaylama"""
    if request.method == 'POST':
        subscription_request = get_object_or_404(SubscriptionRequest, id=request_id, status='pending')
        
        admin_notes = request.POST.get('admin_notes', '')
        success = subscription_request.approve(request.user, admin_notes)
        
        if success:
            messages.success(request, f'{subscription_request.user.get_full_name()} kullanıcısının {subscription_request.plan.name} talebi onaylandı.')
        else:
            messages.error(request, 'Talep onaylanırken bir hata oluştu.')
    
    return redirect('core:admin_dashboard')

@user_passes_test(lambda u: u.is_superuser)
def admin_reject_subscription_request(request, request_id):
    """Admin tarafından abonelik talebi reddetme"""
    if request.method == 'POST':
        subscription_request = get_object_or_404(SubscriptionRequest, id=request_id, status='pending')
        
        admin_notes = request.POST.get('admin_notes', 'Talep reddedildi.')
        success = subscription_request.reject(request.user, admin_notes)
        
        if success:
            messages.success(request, f'{subscription_request.user.get_full_name()} kullanıcısının {subscription_request.plan.name} talebi reddedildi.')
        else:
            messages.error(request, 'Talep reddedilirken bir hata oluştu.')
    
    return redirect('core:admin_dashboard')

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
    
    # Arama
    if search_query:
        messages_list = messages_list.filter(
            Q(subject__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(sender__first_name__icontains=search_query) |
            Q(sender__last_name__icontains=search_query)
        )
    
    # Sayfalama
    from django.core.paginator import Paginator
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
    # İstatistikler
    stats = {
        'total_received': received_messages.count(),
        'unread_received': received_messages.filter(is_read=False).count(),
        'total_sent': sent_messages.count(),
        'urgent_messages': received_messages.filter(priority='urgent', is_read=False).count(),
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
                
                # Bildirim gönder
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
    """Mesaj Oluştur"""
    user = request.user
    
    if user.is_superuser:
        # Admin için özel form
        if request.method == 'POST':
            form = AdminMessageForm(request.POST, request.FILES)
            if form.is_valid():
                message = form.save(commit=False)
                message.sender = user
                
                recipient_type = form.cleaned_data['recipient_type']
                specific_recipient = form.cleaned_data.get('specific_recipient')
                
                if recipient_type == 'single_center':
                    message.recipient = specific_recipient
                    message.message_type = 'admin_to_center'
                elif recipient_type == 'single_producer':
                    message.recipient = specific_recipient
                    message.message_type = 'admin_to_producer'
                else:
                    # Toplu mesaj
                    message.is_broadcast = True
                    message.message_type = 'admin_broadcast'
                    
                    if recipient_type == 'all_centers':
                        message.broadcast_to_centers = True
                    elif recipient_type == 'all_producers':
                        message.broadcast_to_producers = True
                    elif recipient_type == 'all_users':
                        message.broadcast_to_centers = True
                        message.broadcast_to_producers = True
                
                message.save()
                
                # Toplu mesaj ise alıcıları oluştur
                if message.is_broadcast:
                    recipients = []
                    
                    if message.broadcast_to_centers:
                        center_users = User.objects.filter(center__isnull=False)
                        recipients.extend(center_users)
                    
                    if message.broadcast_to_producers:
                        producer_users = User.objects.filter(producer__isnull=False)
                        recipients.extend(producer_users)
                    
                    # MessageRecipient objelerini oluştur
                    for recipient in recipients:
                        MessageRecipient.objects.create(
                            message=message,
                            recipient=recipient
                        )
                        
                        # Bildirim gönder
                        notify.send(
                            sender=user,
                            recipient=recipient,
                            verb='size mesaj gönderdi',
                            action_object=message,
                            description=f'Konu: {message.subject}'
                        )
                else:
                    # Tekil mesaj için bildirim
                    notify.send(
                        sender=user,
                        recipient=message.recipient,
                        verb='size mesaj gönderdi',
                        action_object=message,
                        description=f'Konu: {message.subject}'
                    )
                
                messages.success(request, 'Mesajınız gönderildi.')
                return redirect('core:message_list')
        else:
            form = AdminMessageForm()
    else:
        # Merkez ve üreticiler için basit form
        if request.method == 'POST':
            form = MessageForm(request.POST, request.FILES, user=user)
            if form.is_valid():
                message = form.save(commit=False)
                message.sender = user
                
                # Admin'e gönder
                admin_user = User.objects.filter(is_superuser=True).first()
                message.recipient = admin_user
                
                # Mesaj tipini belirle
                if hasattr(user, 'center'):
                    message.message_type = 'center_to_admin'
                elif hasattr(user, 'producer'):
                    message.message_type = 'producer_to_admin'
                
                message.save()
                
                # Admin'e bildirim gönder
                if admin_user:
                    notify.send(
                        sender=user,
                        recipient=admin_user,
                        verb='size mesaj gönderdi',
                        action_object=message,
                        description=f'Konu: {message.subject}'
                    )
                
                messages.success(request, 'Mesajınız admin\'e gönderildi.')
                return redirect('core:message_list')
        else:
            form = MessageForm(user=user)
    
    context = {
        'form': form,
        'is_admin': user.is_superuser,
    }
    
    return render(request, 'core/message_create.html', context)

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
    """Fiyatlandırma sayfası - artık talep sistemi ile çalışıyor"""
    plans = PricingPlan.objects.filter(is_active=True).exclude(plan_type='trial').order_by('price_usd')
    
    context = {
        'plans': plans
    }
    
    # Giriş yapmış kullanıcı için ek bilgiler
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

@login_required
def subscription_dashboard(request):
    """Abonelik yönetim paneli"""
    try:
        subscription = UserSubscription.objects.get(user=request.user, status='active')
    except UserSubscription.DoesNotExist:
        subscription = None
    
    # Ödeme geçmişi
    payments = PaymentHistory.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    context = {
        'subscription': subscription,
        'payments': payments,
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
            return JsonResponse({'success': True})
        
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
