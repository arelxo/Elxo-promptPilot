from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import UserBillingProfile, Invoice
from analytics_app.models import AnalyticsEvent

class BillingProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, created = UserBillingProfile.objects.get_or_create(user=request.user)
        
        # Calculate real dynamic usage statistics from AnalyticsEvent table
        from django.db.models import Sum
        user_events = AnalyticsEvent.objects.filter(user=request.user)
        requests_count = user_events.count()
        sums = user_events.aggregate(Sum('tokens_used'), Sum('estimated_cost'))
        tokens_sum = sums['tokens_used__sum'] or 0
        cost_sum = sums['estimated_cost__sum'] or 0.0

        # Retrieve invoices
        invoices = Invoice.objects.filter(user=request.user).order_by('-date')
        history_data = []
        for inv in invoices:
            history_data.append({
                "date": inv.date.strftime("%Y-%m-%d"),
                "description": inv.description,
                "amount": float(inv.amount),
                "status": inv.status
            })

        data = {
            "plan": {
                "name": profile.plan_name,
                "status": profile.plan_status,
                "billing_cycle": profile.billing_cycle
            },
            "usage": {
                "requests": requests_count,
                "requests_limit": profile.requests_limit,
                "tokens": tokens_sum,
                "tokens_limit": profile.tokens_limit,
                "estimated_cost": float(cost_sum)
            },
            "next_billing_date": profile.next_billing_date.strftime("%Y-%m-%d") if profile.next_billing_date else None,
            "payment_method": profile.payment_method,
            "billing_history": history_data
        }
        return Response(data, status=status.HTTP_200_OK)

class BillingHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invoices = Invoice.objects.filter(user=request.user).order_by('-date')
        history_data = []
        for inv in invoices:
            history_data.append({
                "date": inv.date.strftime("%Y-%m-%d"),
                "description": inv.description,
                "amount": float(inv.amount),
                "status": inv.status
            })
        return Response(history_data, status=status.HTTP_200_OK)
