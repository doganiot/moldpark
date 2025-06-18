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
from django.db.models import Count, Q, Avg
from django.contrib.auth.models import User
from center.models import Center
from producer.models import Producer, ProducerOrder, ProducerNetwork
from mold.models import EarMold
from datetime import timedelta
import json


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