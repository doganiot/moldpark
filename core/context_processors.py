from django.db.models import Q
from .models import Message, MessageRecipient


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
        
        return {
            'unread_message_count': total_unread,
            'unread_direct_count': unread_direct,
            'unread_broadcast_count': unread_broadcast,
        }
    except Exception as e:
        # Hata durumunda sıfır döndür
        return {'unread_message_count': 0} 