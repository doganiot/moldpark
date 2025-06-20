from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import ContactMessage, Message, MessageRecipient
from .forms import ContactForm, MessageForm, AdminMessageForm, MessageReplyForm
from django.views.generic import TemplateView
from django.contrib.auth.decorators import user_passes_test, login_required
from center.models import Center, CenterMessage
from mold.models import EarMold
from accounts.forms import CustomSignupForm
from django.db.models import Q, Count
from django.contrib.auth.models import User
from producer.models import Producer
from notifications.signals import notify
from django.http import JsonResponse

def home(request):
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
            'top_producers': top_producers
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
        'top_producers': top_producers
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
    messages = CenterMessage.objects.order_by('-created_at')[:5]
    
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
        'revision_molds': molds.filter(status='revision').count(),
        'shipping_molds': molds.filter(status='shipping').count(),
        'delivered_molds': molds.filter(status='delivered').count(),
    }
    
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
        'shipping_molds': mold_stats['shipping_molds'],
        'delivered_molds': mold_stats['delivered_molds'],
        'pending_molds': mold_stats['waiting_molds'],  # Geriye dönük uyumluluk için
        'moldpark_orders': len(moldpark_orders),
        'moldpark_active_orders': len([o for o in moldpark_orders if o.status in ['received', 'designing', 'production', 'quality_check']]),
        'total_users': len(center_users) + len(producer_users),
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
    }
    return render(request, 'core/dashboard_admin.html', context)

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
