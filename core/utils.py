# Basit Bildirim Sistemi Utilities

from .models import SimpleNotification


def send_notification(user, title, message, notification_type='info', related_url=None, related_object_id=None):
    """Kullanıcıya basit bildirim gönder"""
    try:
        notification = SimpleNotification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            related_url=related_url,
            related_object_id=related_object_id
        )

        return notification
    except Exception as e:
        print(f"Bildirim gönderme hatası: {e}")
        return None


def send_bulk_notification(users, title, message, notification_type='info', related_url=None):
    """Birden fazla kullanıcıya bildirim gönder"""
    notifications = []
    for user in users:
        notification = send_notification(user, title, message, notification_type, related_url)
        if notification:
            notifications.append(notification)
    return notifications


def get_user_notifications(user, limit=10, unread_only=False):
    """Kullanıcının bildirimlerini getir"""
    notifications = user.simple_notifications.all()
    
    if unread_only:
        notifications = notifications.filter(is_read=False)
    
    return notifications.order_by('-created_at')[:limit]


def get_unread_count(user):
    """Kullanıcının okunmamış bildirim sayısı"""
    return user.simple_notifications.filter(is_read=False).count()


def mark_all_as_read(user):
    """Kullanıcının tüm bildirimlerini okundu olarak işaretle"""
    user.simple_notifications.filter(is_read=False).update(is_read=True)


# Yaygın bildirim türleri için kısayollar
def send_success_notification(user, title, message, related_url=None):
    return send_notification(user, title, message, 'success', related_url)


def send_warning_notification(user, title, message, related_url=None):
    return send_notification(user, title, message, 'warning', related_url)


def send_error_notification(user, title, message, related_url=None):
    return send_notification(user, title, message, 'error', related_url)


def send_order_notification(user, title, message, related_url=None, order_id=None):
    return send_notification(user, title, message, 'order', related_url, order_id)


def send_system_notification(user, title, message, related_url=None):
    return send_notification(user, title, message, 'system', related_url) 


def send_message_notification(user, title, message, related_url=None):
    return send_notification(user, title, message, 'message', related_url) 