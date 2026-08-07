from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from analytics_app.models import AnalyticsEvent
from django.contrib.auth.models import User

class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        all_events = AnalyticsEvent.objects.filter(user=request.user)
        events = all_events.order_by('-created_at')[:5]
        
        total_requests = all_events.count()
        total_tokens = sum(e.tokens_used for e in all_events)
        total_cost = sum(e.estimated_cost for e in all_events)
        
        avg_latency = 0
        if total_requests > 0:
            avg_latency = int(sum(e.latency_ms for e in all_events) / total_requests)
            
        success_events = all_events.filter(status="success").count()
        success_rate = 100.0
        if total_requests > 0:
            success_rate = round((success_events / total_requests) * 100, 2)
            
        # Format token usage
        if total_tokens >= 1000000:
            token_usage_str = f"{total_tokens / 1000000:.1f}M Tokens"
        elif total_tokens >= 1000:
            token_usage_str = f"{total_tokens / 1000:.1f}K Tokens"
        else:
            token_usage_str = f"{total_tokens / 1000000:.3f}M Tokens"

        recent_events = []
        for e in events:
            local_time = e.created_at.strftime("%H:%M:%S")
            prompt_title = e.prompt.title if e.prompt else "System Template"
            recent_events.append({
                "timestamp": local_time,
                "prompt_title": prompt_title,
                "provider": e.provider,
                "latency": f"{e.latency_ms}ms",
                "status": "200 OK" if e.status == "success" else "Error"
            })

        return Response({
            "total_requests": total_requests,
            "token_usage": token_usage_str,
            "ai_cost": float(total_cost),
            "avg_latency": avg_latency,
            "success_rate": success_rate,
            "active_users": User.objects.count(),
            "recent_events": recent_events
        })