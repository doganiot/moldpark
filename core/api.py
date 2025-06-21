"""
MoldPark REST API Views
Sistem durumu ve istatistikler için API endpoints
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from django.db.models import Count, Q, Avg, F
from django.contrib.auth.models import User
from center.models import Center
from producer.models import Producer, ProducerOrder, ProducerNetwork
from mold.models import EarMold
from datetime import timedelta
import json
from django.db import connection
from django.conf import settings
from django.contrib.auth.decorators import staff_member_required


class SystemStatusAPI(View):
    """Sistem durumu API endpoint'i"""
    
    @method_decorator(login_required)
    def get(self, request):
        """Sistem genel durumu"""
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        
        # Temel istatistikler
        stats = {
            'system': {
                'status': 'healthy',
                'version': '2.0.0',
                'uptime': '24/7',
                'last_updated': now.isoformat(),
            },
            'users': {
                'total': User.objects.count(),
                'active_24h': User.objects.filter(last_login__gte=last_24h).count(),
                'centers': Center.objects.count(),
                'producers': Producer.objects.count(),
                'verified_producers': Producer.objects.filter(is_verified=True).count(),
            },
            'orders': {
                'total': ProducerOrder.objects.count(),
                'active': ProducerOrder.objects.filter(
                    status__in=['received', 'designing', 'production', 'quality_check']
                ).count(),
                'completed_30d': ProducerOrder.objects.filter(
                    status='delivered',
                    created_at__gte=last_30d
                ).count(),
                'pending': ProducerOrder.objects.filter(status='received').count(),
            },
            'molds': {
                'total': EarMold.objects.count(),
                'created_24h': EarMold.objects.filter(created_at__gte=last_24h).count(),
                'created_7d': EarMold.objects.filter(created_at__gte=last_7d).count(),
                'created_30d': EarMold.objects.filter(created_at__gte=last_30d).count(),
            },
            'networks': {
                'total': ProducerNetwork.objects.count(),
                'active': ProducerNetwork.objects.filter(status='active').count(),
                'pending': ProducerNetwork.objects.filter(status='pending').count(),
                'suspended': ProducerNetwork.objects.filter(status='suspended').count(),
            }
        }
        
        # Performans metrikleri
        performance = self.get_performance_metrics(last_30d)
        stats['performance'] = performance
        
        # Sistem sağlığı
        health_score = self.calculate_health_score(stats)
        stats['system']['health_score'] = health_score
        
        return JsonResponse(stats)
    
    def get_performance_metrics(self, since_date):
        """Performans metrikleri hesapla"""
        completed_orders = ProducerOrder.objects.filter(
            status='delivered',
            created_at__gte=since_date,
            actual_delivery__isnull=False
        )
        
        avg_delivery_time = 0
        if completed_orders.exists():
            total_time = sum([
                (order.actual_delivery - order.created_at).days 
                for order in completed_orders
            ])
            avg_delivery_time = round(total_time / completed_orders.count(), 1)
        
        # Kalite skorları
        quality_scores = EarMold.objects.filter(
            quality_score__isnull=False,
            created_at__gte=since_date
        ).aggregate(avg_quality=Avg('quality_score'))
        
        return {
            'avg_delivery_days': avg_delivery_time,
            'avg_quality_score': round(quality_scores['avg_quality'] or 0, 1),
            'completion_rate': self.calculate_completion_rate(since_date),
        }
    
    def calculate_completion_rate(self, since_date):
        """Tamamlanma oranı hesapla"""
        total_orders = ProducerOrder.objects.filter(created_at__gte=since_date).count()
        completed_orders = ProducerOrder.objects.filter(
            status='delivered',
            created_at__gte=since_date
        ).count()
        
        if total_orders == 0:
            return 0
        
        return round((completed_orders / total_orders) * 100, 1)
    
    def calculate_health_score(self, stats):
        """Sistem sağlık skoru hesapla (0-100)"""
        score = 100
        
        # Aktif üretici oranı
        if stats['users']['producers'] > 0:
            producer_ratio = stats['users']['verified_producers'] / stats['users']['producers']
            if producer_ratio < 0.5:
                score -= 20
        
        # Network sağlığı
        if stats['networks']['total'] > 0:
            network_health = stats['networks']['active'] / stats['networks']['total']
            if network_health < 0.7:
                score -= 15
        
        # Aktif sipariş yoğunluğu
        if stats['orders']['active'] > stats['orders']['completed_30d'] * 2:
            score -= 10  # Çok fazla bekleyen sipariş
        
        return max(0, min(100, score))


@require_http_methods(["GET"])
@login_required
def production_pipeline_api(request):
    """Üretim hattı durumu API"""
    stages = [
        ('received', 'Alınan Siparişler'),
        ('designing', '3D Tasarım'),
        ('production', 'Üretimde'),
        ('quality_check', 'Kalite Kontrol'),
        ('packaging', 'Paketleme'),
        ('shipping', 'Kargoda'),
    ]
    
    pipeline_data = []
    total_orders = ProducerOrder.objects.filter(
        status__in=[stage[0] for stage in stages]
    ).count()
    
    for stage_code, stage_name in stages:
        count = ProducerOrder.objects.filter(status=stage_code).count()
        percentage = round((count / total_orders) * 100, 1) if total_orders > 0 else 0
        
        pipeline_data.append({
            'stage': stage_name,
            'stage_code': stage_code,
            'count': count,
            'percentage': percentage,
        })
    
    return JsonResponse({
        'pipeline': pipeline_data,
        'total_active_orders': total_orders,
        'last_updated': timezone.now().isoformat(),
    })


@require_http_methods(["GET"])
@login_required
def alerts_api(request):
    """Sistem uyarıları API"""
    alerts = []
    
    # Geciken siparişler
    overdue_orders = ProducerOrder.objects.filter(
        estimated_delivery__lt=timezone.now(),
        status__in=['received', 'designing', 'production', 'quality_check']
    ).count()
    
    if overdue_orders > 0:
        alerts.append({
            'type': 'warning',
            'title': 'Geciken Siparişler',
            'message': f'{overdue_orders} sipariş tahmini teslimat tarihini geçti',
            'count': overdue_orders,
            'priority': 'high' if overdue_orders > 10 else 'medium',
        })
    
    # Askıya alınmış ağlar
    suspended_networks = ProducerNetwork.objects.filter(status='suspended').count()
    if suspended_networks > 0:
        alerts.append({
            'type': 'danger',
            'title': 'Askıya Alınmış Ağlar',
            'message': f'{suspended_networks} üretici ağı askıya alınmış',
            'count': suspended_networks,
            'priority': 'high',
        })
    
    # Doğrulanmamış üreticiler
    unverified_producers = Producer.objects.filter(
        is_active=True, 
        is_verified=False
    ).count()
    
    if unverified_producers > 0:
        alerts.append({
            'type': 'info',
            'title': 'Doğrulama Bekleyen Üreticiler',
            'message': f'{unverified_producers} üretici doğrulama bekliyor',
            'count': unverified_producers,
            'priority': 'low',
        })
    
    # Yüksek öncelikli siparişler
    urgent_orders = ProducerOrder.objects.filter(
        priority='urgent',
        status__in=['received', 'designing', 'production']
    ).count()
    
    if urgent_orders > 0:
        alerts.append({
            'type': 'warning',
            'title': 'Acil Siparişler',
            'message': f'{urgent_orders} acil sipariş beklemede',
            'count': urgent_orders,
            'priority': 'high',
        })
    
    return JsonResponse({
        'alerts': alerts,
        'total_alerts': len(alerts),
        'high_priority': len([a for a in alerts if a['priority'] == 'high']),
        'last_updated': timezone.now().isoformat(),
    })


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def health_check_api(request):
    """Sistem sağlık kontrolü API"""
    try:
        # Database bağlantısı test et
        User.objects.count()
        
        # Temel model kontrolü
        center_count = Center.objects.count()
        producer_count = Producer.objects.count()
        mold_count = EarMold.objects.count()
        
        status = {
            'status': 'healthy',
            'database': 'connected',
            'models': {
                'centers': center_count,
                'producers': producer_count,
                'molds': mold_count,
            },
            'timestamp': timezone.now().isoformat(),
        }
        
        return JsonResponse(status)
        
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat(),
        }, status=500)


@require_http_methods(["GET"])
@login_required
def system_health_api(request):
    """Sistem sağlık durumu API"""
    try:
        # Temel sağlık kontrolleri
        health_data = {
            'timestamp': timezone.now().isoformat(),
            'score': 85,  # Dinamik hesaplanacak
            'status': 'healthy',
            'components': {}
        }
        
        # Database sağlığı
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_data['components']['database'] = {
                'status': 'healthy',
                'response_time': '< 50ms'
            }
        except Exception as e:
            health_data['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_data['score'] -= 30
        
        # Cache sağlığı
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 60)
            if cache.get('health_check') == 'ok':
                health_data['components']['cache'] = {
                    'status': 'healthy',
                    'type': 'active'
                }
            else:
                health_data['components']['cache'] = {
                    'status': 'warning',
                    'type': 'inactive'
                }
                health_data['score'] -= 10
        except Exception:
            health_data['components']['cache'] = {
                'status': 'warning',
                'type': 'unavailable'
            }
            health_data['score'] -= 5
        
        # Disk kullanımı
        try:
            import shutil
            total, used, free = shutil.disk_usage(settings.BASE_DIR)
            usage_percent = (used / total) * 100
            
            health_data['components']['disk'] = {
                'status': 'healthy' if usage_percent < 80 else 'warning' if usage_percent < 90 else 'critical',
                'usage_percent': round(usage_percent, 1),
                'free_gb': round(free / (1024**3), 1)
            }
            
            if usage_percent > 90:
                health_data['score'] -= 20
            elif usage_percent > 80:
                health_data['score'] -= 10
                
        except Exception:
            health_data['components']['disk'] = {
                'status': 'unknown',
                'error': 'Unable to check disk usage'
            }
        
        # Ağ sağlığı
        active_networks = ProducerNetwork.objects.filter(status='active').count()
        total_networks = ProducerNetwork.objects.count()
        
        if total_networks > 0:
            network_health_percent = (active_networks / total_networks) * 100
            health_data['components']['network'] = {
                'status': 'healthy' if network_health_percent > 70 else 'warning',
                'active_networks': active_networks,
                'total_networks': total_networks,
                'health_percent': round(network_health_percent, 1)
            }
            
            if network_health_percent < 50:
                health_data['score'] -= 15
            elif network_health_percent < 70:
                health_data['score'] -= 5
        else:
            health_data['components']['network'] = {
                'status': 'healthy',
                'active_networks': 0,
                'total_networks': 0
            }
        
        # Kritik uyarılar
        critical_alerts = []
        
        # Geciken siparişler
        overdue_orders = ProducerOrder.objects.filter(
            estimated_delivery__lt=timezone.now(),
            status__in=['received', 'designing', 'production', 'quality_check']
        ).count()
        
        if overdue_orders > 10:
            critical_alerts.append({
                'type': 'overdue_orders',
                'message': f'{overdue_orders} sipariş gecikmiş',
                'severity': 'high'
            })
            health_data['score'] -= 10
        
        # Güvenlik riskleri
        risky_producers = Producer.objects.filter(
            user__is_staff=True
        ) | Producer.objects.filter(
            user__is_superuser=True
        )
        
        if risky_producers.exists():
            critical_alerts.append({
                'type': 'security_risk',
                'message': f'{risky_producers.count()} üretici hesabının admin yetkisi var',
                'severity': 'critical'
            })
            health_data['score'] -= 25
        
        health_data['critical_alerts'] = critical_alerts
        health_data['last_check'] = timezone.now()
        
        # Genel durum belirleme
        if health_data['score'] >= 90:
            health_data['status'] = 'excellent'
        elif health_data['score'] >= 70:
            health_data['status'] = 'good'
        elif health_data['score'] >= 50:
            health_data['status'] = 'warning'
        else:
            health_data['status'] = 'critical'
        
        return JsonResponse(health_data)
        
    except Exception as e:
        return JsonResponse({
            'error': 'Health check failed',
            'message': str(e),
            'status': 'error'
        }, status=500)


@require_http_methods(["POST"])
@staff_member_required
def run_health_check_api(request):
    """Tam sistem sağlık kontrolü çalıştır"""
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # System check komutunu çalıştır
        output = StringIO()
        call_command('system_check', '--verbose', stdout=output)
        
        result = {
            'status': 'started',
            'message': 'Sistem kontrolü başlatıldı',
            'timestamp': timezone.now().isoformat(),
            'output': output.getvalue()
        }
        
        # Async olarak auto_system_monitor da çalıştırılabilir
        try:
            call_command('auto_system_monitor', '--send-alerts')
            result['monitoring'] = 'started'
        except Exception as e:
            result['monitoring_error'] = str(e)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'error': 'Failed to start health check',
            'message': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def smart_notifications_status_api(request):
    """Akıllı bildirim sistemi durumu"""
    try:
        from core.smart_notifications import SmartNotificationManager
        
        # Son bildirim istatistikleri
        last_24h = timezone.now() - timedelta(hours=24)
        
        # Kullanıcı türüne göre bildirim sayıları
        user_notifications = request.user.notifications.filter(
            timestamp__gte=last_24h
        )
        
        notification_stats = {
            'user_notifications': {
                'total_24h': user_notifications.count(),
                'unread': user_notifications.unread().count(),
                'by_verb': {}
            },
            'system_stats': {}
        }
        
        # Verb'lere göre grupla
        for notification in user_notifications:
            verb = notification.verb
            if verb not in notification_stats['user_notifications']['by_verb']:
                notification_stats['user_notifications']['by_verb'][verb] = 0
            notification_stats['user_notifications']['by_verb'][verb] += 1
        
        # Admin ise sistem geneli istatistikler
        if request.user.is_superuser:
            from notifications.models import Notification
            
            system_notifications_24h = Notification.objects.filter(
                timestamp__gte=last_24h
            )
            
            notification_stats['system_stats'] = {
                'total_sent_24h': system_notifications_24h.count(),
                'unique_recipients': system_notifications_24h.values('recipient').distinct().count(),
                'by_verb': {}
            }
            
            # Sistem geneli verb istatistikleri
            verb_counts = system_notifications_24h.values('verb').annotate(
                count=Count('verb')
            ).order_by('-count')[:10]
            
            for item in verb_counts:
                notification_stats['system_stats']['by_verb'][item['verb']] = item['count']
        
        # Akıllı bildirim önerileri
        suggestions = []
        
        if hasattr(request.user, 'center'):
            center = request.user.center
            used_molds = center.molds.count()
            limit_percentage = (used_molds / center.mold_limit) * 100
            
            if limit_percentage > 80:
                suggestions.append({
                    'type': 'limit_warning',
                    'message': f'Kalıp limitinizin %{limit_percentage:.0f}\'ini kullandınız',
                    'action': 'Limit artırımı için admin ile iletişime geçin'
                })
        
        elif hasattr(request.user, 'producer'):
            producer = request.user.producer
            pending_orders = producer.orders.filter(status='received').count()
            
            if pending_orders > 5:
                suggestions.append({
                    'type': 'pending_orders',
                    'message': f'{pending_orders} bekleyen sipariş var',
                    'action': 'Siparişleri işleme almayı düşünün'
                })
        
        notification_stats['suggestions'] = suggestions
        notification_stats['timestamp'] = timezone.now().isoformat()
        
        return JsonResponse(notification_stats)
        
    except Exception as e:
        return JsonResponse({
            'error': 'Failed to get notification status',
            'message': str(e)
        }, status=500)


@require_http_methods(["POST"])
@staff_member_required
def trigger_smart_notifications_api(request):
    """Akıllı bildirimleri manuel olarak tetikle"""
    try:
        from core.smart_notifications import send_smart_notifications
        
        notification_type = request.POST.get('type', 'all')
        dry_run = request.POST.get('dry_run', 'false').lower() == 'true'
        
        if dry_run:
            # Dry run modu - sadece analiz
            from django.core.management import call_command
            from io import StringIO
            
            output = StringIO()
            call_command('send_smart_notifications', '--dry-run', '--type', notification_type, stdout=output)
            
            return JsonResponse({
                'status': 'analyzed',
                'message': 'Analiz tamamlandı (bildirim gönderilmedi)',
                'analysis': output.getvalue(),
                'dry_run': True
            })
        else:
            # Gerçek bildirim gönderimi
            send_smart_notifications()
            
            return JsonResponse({
                'status': 'sent',
                'message': 'Akıllı bildirimler gönderildi',
                'timestamp': timezone.now().isoformat(),
                'dry_run': False
            })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Failed to trigger smart notifications',
            'message': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def performance_insights_api(request):
    """Performans içgörüleri API"""
    try:
        insights = {
            'timestamp': timezone.now().isoformat(),
            'user_insights': {},
            'system_insights': {}
        }
        
        # Kullanıcı spesifik içgörüler
        if hasattr(request.user, 'center'):
            center = request.user.center
            
            # Son 30 günün analizi
            last_month = timezone.now() - timedelta(days=30)
            recent_orders = ProducerOrder.objects.filter(
                center=center,
                created_at__gte=last_month
            )
            
            if recent_orders.exists():
                # Ortalama teslimat süresi
                completed_orders = recent_orders.filter(
                    actual_delivery__isnull=False
                )
                
                if completed_orders.exists():
                    avg_delivery_days = sum([
                        (order.actual_delivery - order.created_at).days
                        for order in completed_orders
                    ]) / completed_orders.count()
                    
                    insights['user_insights']['avg_delivery_days'] = round(avg_delivery_days, 1)
                
                # Sipariş başarı oranı
                success_rate = (completed_orders.count() / recent_orders.count()) * 100
                insights['user_insights']['success_rate'] = round(success_rate, 1)
                
                # Popüler kalıp tipleri
                mold_types = center.molds.filter(
                    created_at__gte=last_month
                ).values('mold_type').annotate(
                    count=Count('mold_type')
                ).order_by('-count')[:3]
                
                insights['user_insights']['popular_mold_types'] = list(mold_types)
        
        elif hasattr(request.user, 'producer'):
            producer = request.user.producer
            
            # Üretici performans metrikleri
            last_month = timezone.now() - timedelta(days=30)
            recent_orders = producer.orders.filter(created_at__gte=last_month)
            
            if recent_orders.exists():
                # Zamanında teslimat oranı
                on_time_orders = recent_orders.filter(
                    actual_delivery__lte=F('estimated_delivery'),
                    actual_delivery__isnull=False
                ).count()
                
                on_time_rate = (on_time_orders / recent_orders.count()) * 100
                insights['user_insights']['on_time_delivery_rate'] = round(on_time_rate, 1)
                
                # Kapasite kullanımı
                current_month_orders = producer.get_current_month_orders()
                capacity_usage = (current_month_orders / producer.mold_limit) * 100
                insights['user_insights']['capacity_usage'] = round(capacity_usage, 1)
        
        # Admin ise sistem geneli içgörüler
        if request.user.is_superuser:
            # Sistem performans metrikleri
            last_week = timezone.now() - timedelta(days=7)
            
            # Haftalık büyüme
            this_week_orders = ProducerOrder.objects.filter(created_at__gte=last_week).count()
            last_week_orders = ProducerOrder.objects.filter(
                created_at__gte=last_week - timedelta(days=7),
                created_at__lt=last_week
            ).count()
            
            if last_week_orders > 0:
                growth_rate = ((this_week_orders - last_week_orders) / last_week_orders) * 100
                insights['system_insights']['weekly_growth_rate'] = round(growth_rate, 1)
            
            # En aktif üreticiler
            top_producers = Producer.objects.filter(
                orders__created_at__gte=last_week
            ).annotate(
                order_count=Count('orders')
            ).order_by('-order_count')[:5]
            
            insights['system_insights']['top_producers'] = [
                {
                    'name': p.company_name,
                    'order_count': p.order_count
                } for p in top_producers
            ]
        
        return JsonResponse(insights)
        
    except Exception as e:
        return JsonResponse({
            'error': 'Failed to get performance insights',
            'message': str(e)
        }, status=500) 