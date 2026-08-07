from django.db import models
from django.contrib.auth.models import User
from prompts.models import Prompt

class AnalyticsEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="analytics_events")
    prompt = models.ForeignKey(Prompt, on_delete=models.SET_NULL, null=True, blank=True, related_name="analytics_events")
    provider = models.CharField(max_length=100, blank=True, default='openai')
    tokens_used = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=6, default=0.0)
    latency_ms = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='success')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Event {self.id} - {self.provider} - {self.status}"
