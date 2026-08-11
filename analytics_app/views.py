from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import AnalyticsEvent
from prompts.models import Prompt
from django.contrib.auth.models import User
from django.db.models import Sum, Avg, Min, Max
from django.utils import timezone
from datetime import datetime, timedelta

class AnalyticsDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Base query optimized with select_related for prompt to avoid N+1 queries
        all_events = AnalyticsEvent.objects.filter(user=request.user).select_related('prompt').order_by('created_at')
        total_requests = all_events.count()
        
        # 2. Main KPIs
        total_prompts = Prompt.objects.filter(owner=request.user).count()
        total_tokens = all_events.aggregate(Sum('tokens_used'))['tokens_used__sum'] or 0
        total_cost = all_events.aggregate(Sum('estimated_cost'))['estimated_cost__sum'] or 0.0
        avg_latency = all_events.aggregate(Avg('latency_ms'))['latency_ms__avg'] or 0
        success_events = all_events.filter(status="success").count()
        
        success_rate = 100.0
        if total_requests > 0:
            success_rate = round((success_events / total_requests) * 100, 2)
            
        active_connections = 0
        try:
            from connections.models import ProviderConnection
            active_connections = ProviderConnection.objects.filter(user=request.user, status="connected").count()
        except Exception:
            pass

        # Format token usage
        if total_tokens >= 1000000:
            token_usage_str = f"{total_tokens / 1000000:.1f}M Tokens"
        elif total_tokens >= 1000:
            token_usage_str = f"{total_tokens / 1000:.1f}K Tokens"
        else:
            token_usage_str = f"{total_tokens / 1000000:.3f}M Tokens"

        # 3. Usage by day ranges (Today, 7d, 30d, 12m)
        now = timezone.now()
        
        # today (last 24 hours in 6 blocks of 4 hours)
        today_labels = []
        today_requests = [0] * 6
        today_executions = [0] * 6
        today_tokens = [0.0] * 6
        
        start_24h = now - timedelta(hours=24)
        events_24h = [e for e in all_events if e.created_at >= start_24h]
        for i in range(6):
            b_start = start_24h + timedelta(hours=i*4)
            b_end = b_start + timedelta(hours=4)
            today_labels.append(b_start.strftime("%H:%M"))
            
            b_events = [e for e in events_24h if b_start <= e.created_at < b_end]
            today_requests[i] = len(b_events)
            today_executions[i] = len([e for e in b_events if e.status == "success"])
            today_tokens[i] = round(sum(e.tokens_used for e in b_events) / 1000, 3) # Let's keep it in thousands for line charts readability
            
        # 7d (last 7 days daily)
        seven_days_labels = []
        seven_days_requests = [0] * 7
        seven_days_executions = [0] * 7
        seven_days_tokens = [0.0] * 7
        
        start_7d = (now - timedelta(days=6)).date()
        for i in range(7):
            day_date = start_7d + timedelta(days=i)
            seven_days_labels.append(day_date.strftime("%a"))
            
            day_events = [e for e in all_events if e.created_at.date() == day_date]
            seven_days_requests[i] = len(day_events)
            seven_days_executions[i] = len([e for e in day_events if e.status == "success"])
            seven_days_tokens[i] = round(sum(e.tokens_used for e in day_events) / 1000, 3)

        # 30d (last 30 days weekly)
        thirty_days_labels = ['Wk 1', 'Wk 2', 'Wk 3', 'Wk 4']
        thirty_days_requests = [0] * 4
        thirty_days_executions = [0] * 4
        thirty_days_tokens = [0.0] * 4
        
        start_30d = now - timedelta(days=28)
        for i in range(4):
            wk_start = start_30d + timedelta(weeks=i)
            wk_end = wk_start + timedelta(weeks=1)
            
            wk_events = [e for e in all_events if wk_start <= e.created_at < wk_end]
            thirty_days_requests[i] = len(wk_events)
            thirty_days_executions[i] = len([e for e in wk_events if e.status == "success"])
            thirty_days_tokens[i] = round(sum(e.tokens_used for e in wk_events) / 1000, 3)

        # 12m (last 12 months)
        twelve_months_labels = []
        twelve_months_requests = [0] * 12
        twelve_months_executions = [0] * 12
        twelve_months_tokens = [0.0] * 12
        
        start_12m = now - timedelta(days=365)
        curr_month_date = start_12m
        for i in range(12):
            twelve_months_labels.append(curr_month_date.strftime("%b"))
            m_events = [e for e in all_events if e.created_at.year == curr_month_date.year and e.created_at.month == curr_month_date.month]
            
            twelve_months_requests[i] = len(m_events)
            twelve_months_executions[i] = len([e for e in m_events if e.status == "success"])
            twelve_months_tokens[i] = round(sum(e.tokens_used for e in m_events) / 1000, 3)
            
            # Increment month
            if curr_month_date.month == 12:
                curr_month_date = curr_month_date.replace(year=curr_month_date.year + 1, month=1)
            else:
                curr_month_date = curr_month_date.replace(month=curr_month_date.month + 1)

        # 4. Latency and Provider Distribution (usage_by_model)
        provider_mappings = {
            "OpenAI": ["openai", "OpenAI"],
            "Claude": ["claude", "Claude", "anthropic", "Anthropic"],
            "Gemini": ["gemini", "Gemini", "google", "Google"],
            "DeepSeek": ["deepseek", "DeepSeek"],
            "Llama": ["llama", "Llama", "meta", "Meta"],
            "Mistral": ["mistral", "Mistral"]
        }
        
        latency_labels = []
        latency_avg = []
        latency_min = []
        latency_max = []
        
        provider_labels = []
        provider_counts = []
        
        for p_name, aliases in provider_mappings.items():
            p_events = [e for e in all_events if e.provider in aliases]
            count = len(p_events)
            
            if count > 0:
                p_avg = int(sum(e.latency_ms for e in p_events) / count)
                p_min = min(e.latency_ms for e in p_events)
                p_max = max(e.latency_ms for e in p_events)
                
                latency_labels.append(p_name)
                latency_avg.append(p_avg)
                latency_min.append(p_min)
                latency_max.append(p_max)
                
                provider_labels.append(p_name)
                provider_counts.append(count)

        # 5. Token Cost analytics over last 30 days
        cost_labels = [str(i) for i in range(1, 31)]
        cost_input_tokens = [0.0] * 30
        cost_output_tokens = [0.0] * 30
        cost_amount = [0.0] * 30
        
        start_cost = (now - timedelta(days=29)).date()
        for i in range(30):
            d_date = start_cost + timedelta(days=i)
            d_events = [e for e in all_events if e.created_at.date() == d_date]
            tot_t = sum(e.tokens_used for e in d_events)
            cost_input_tokens[i] = round((tot_t * 0.6) / 1000000, 3)
            cost_output_tokens[i] = round((tot_t * 0.4) / 1000000, 3)
            cost_amount[i] = float(sum(e.estimated_cost for e in d_events))

        # 6. Recent Activity
        recent_activity = []
        for e in reversed(all_events):
            if len(recent_activity) >= 15:
                break
            recent_activity.append({
                "timestamp": e.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "prompt_title": e.prompt.title if e.prompt else "System Template",
                "provider": e.provider,
                "latency_ms": e.latency_ms,
                "tokens_used": e.tokens_used,
                "estimated_cost": float(e.estimated_cost),
                "status": e.status
            })

        # 7. Model performance list
        model_performance = []
        for p_name, aliases in provider_mappings.items():
            p_events = [e for e in all_events if e.provider in aliases]
            count = len(p_events)
            if count > 0:
                p_success = len([e for e in p_events if e.status == "success"])
                p_success_rate = round((p_success / count) * 100, 2)
                p_avg_latency = int(sum(e.latency_ms for e in p_events) / count)
                p_avg_tokens = int(sum(e.tokens_used for e in p_events) / count)
                p_cost = float(sum(e.estimated_cost for e in p_events))
                
                model_performance.append({
                    "provider": p_name,
                    "model": f"{p_name} Default Model",
                    "requests": count,
                    "avg_tokens": p_avg_tokens,
                    "avg_latency": p_avg_latency,
                    "success_rate": p_success_rate,
                    "cost": p_cost,
                    "status": "Healthy" if p_success_rate >= 95.0 else "Degraded"
                })

        # 8. Top Prompt performance
        prompt_performance = []
        user_prompts = Prompt.objects.filter(owner=request.user)
        for p in user_prompts:
            p_events = [e for e in all_events if e.prompt_id == p.id]
            exec_count = len(p_events)
            if exec_count > 0:
                p_success = len([e for e in p_events if e.status == "success"])
                p_success_rate = round((p_success / exec_count) * 100, 2)
                p_avg_latency = int(sum(e.latency_ms for e in p_events) / exec_count)
                p_cost = float(sum(e.estimated_cost for e in p_events))
                
                prompt_performance.append({
                    "name": p.title,
                    "executions": exec_count,
                    "success_rate": p_success_rate,
                    "avg_latency": p_avg_latency,
                    "cost": p_cost
                })
        prompt_performance.sort(key=lambda x: x["executions"], reverse=True)

        data = {
            "total_prompts": total_prompts,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "token_usage": token_usage_str,
            "total_cost": float(total_cost),
            "estimated_cost": float(total_cost),
            "avg_latency": int(avg_latency),
            "success_rate": success_rate,
            "active_connections": active_connections,
            "active_users": User.objects.count(),
            "usage_by_day": {
                "today": {
                    "labels": today_labels,
                    "requests": today_requests,
                    "executions": today_executions,
                    "tokens": today_tokens
                },
                "7d": {
                    "labels": seven_days_labels,
                    "requests": seven_days_requests,
                    "executions": seven_days_executions,
                    "tokens": seven_days_tokens
                },
                "30d": {
                    "labels": thirty_days_labels,
                    "requests": thirty_days_requests,
                    "executions": thirty_days_executions,
                    "tokens": thirty_days_tokens
                },
                "12m": {
                    "labels": twelve_months_labels,
                    "requests": twelve_months_requests,
                    "executions": twelve_months_executions,
                    "tokens": twelve_months_tokens
                }
            },
            "usage_by_model": {
                "latency": {
                    "labels": latency_labels,
                    "avg": latency_avg,
                    "min": latency_min,
                    "max": latency_max
                },
                "distribution": {
                    "labels": provider_labels,
                    "data": provider_counts
                }
            },
            "cost_data": {
                "labels": cost_labels,
                "inputTokens": cost_input_tokens,
                "outputTokens": cost_output_tokens,
                "cost": cost_amount
            },
            "recent_activity": recent_activity,
            "model_performance": model_performance,
            "prompt_performance": prompt_performance
        }
        
        return Response(data, status=status.HTTP_200_OK)

