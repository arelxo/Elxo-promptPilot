from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Prompt, PromptVersion
from .serializers import PromptSerializer, PromptVersionSerializer


class PromptViewSet(viewsets.ModelViewSet):
    serializer_class = PromptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Prompt.objects.filter(
            owner=self.request.user
        ).order_by("-updated_at")

    def perform_create(self, serializer):
        prompt = serializer.save(owner=self.request.user)
        try:
            from analytics_app.models import AnalyticsEvent
            import random
            tokens = max(1, len(prompt.content) // 4)
            cost = tokens * 0.00002
            latency = random.randint(150, 350)
            AnalyticsEvent.objects.create(
                user=self.request.user,
                prompt=prompt,
                provider="openai",
                tokens_used=tokens,
                estimated_cost=cost,
                latency_ms=latency,
                status="success"
            )
        except Exception as e:
            print("Error creating analytics event:", e)


class PromptVersionViewSet(viewsets.ModelViewSet):
    serializer_class = PromptVersionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PromptVersion.objects.filter(
            created_by=self.request.user
        ).order_by("-version_number")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)