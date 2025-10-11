from django.db.models import Q
from .models import Message, MessageRecipient, SimpleNotification, PricingConfiguration
from mold.models import RevisionRequest


def unread_messages(request):
    """Okunmamış mesaj sayısını context'e ekler"""
    if not request.user.is_authenticated:
        return {'unread_message_count': 0}
    
    try:
        # Direkt gelen okunmamış mesajlar
        unread_direct = Message.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        # Toplu mesajlardaki okunmamış mesajlar
        unread_broadcast = MessageRecipient.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        total_unread = unread_direct + unread_broadcast
        
        # Üretici için bekleyen revizyon talepleri
        pending_revision_requests = 0
        if hasattr(request.user, 'producer'):
            try:
                pending_revision_requests = RevisionRequest.objects.filter(
                    modeled_mold__ear_mold__producer_orders__producer=request.user.producer,
                    status='pending'
                ).count()
            except:
                pending_revision_requests = 0
        
        # Basit bildirim sayısı
        unread_notifications = SimpleNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return {
            'unread_message_count': total_unread,
            'unread_direct_count': unread_direct,
            'unread_broadcast_count': unread_broadcast,
            'pending_revision_requests': pending_revision_requests,
            'unread_notifications': unread_notifications,
        }
    except Exception as e:
        # Hata durumunda sıfır döndür
        return {
            'unread_message_count': 0,
            'pending_revision_requests': 0,
            'unread_notifications': 0,
        }


def pricing_config(request):
    """
    Aktif fiyatlandırma yapılandırmasını tüm template'lere ekler
    Kullanım: {{ pricing.physical_mold_price }}
    """
    try:
        pricing = PricingConfiguration.get_active()
        return {
            'pricing': pricing,
            'pricing_summary': pricing.get_pricing_summary() if pricing else None,
        }
    except Exception as e:
        # Hata durumunda boş döndür
        return {
            'pricing': None,
            'pricing_summary': None,
        } 