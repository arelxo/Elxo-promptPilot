from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import ProviderConnection
from django.utils import timezone
import os

class ConnectionsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        providers = ["OpenAI", "Claude", "Gemini"]
        connections_data = []

        for provider in providers:
            conn, created = ProviderConnection.objects.get_or_create(
                user=request.user,
                provider=provider
            )
            connections_data.append({
                "provider": conn.provider,
                "status": conn.status,
                "connected_at": conn.connected_at.isoformat() if conn.connected_at else None
            })

        return Response({"connections": connections_data}, status=status.HTTP_200_OK)

class ConnectProviderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, provider):
        prov_map = {
            "openai": "OpenAI",
            "claude": "Claude",
            "gemini": "Gemini"
        }
        normalized = prov_map.get(provider.lower())
        if not normalized:
            return Response({"detail": f"Provider '{provider}' is not supported."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if API Key is configured in environment
        key_var = f"{normalized.upper()}_API_KEY" if normalized != "Claude" else "ANTHROPIC_API_KEY"
        if not os.environ.get(key_var):
            return Response({"detail": "Provider connection is not configured yet."}, status=status.HTTP_400_BAD_REQUEST)

        conn, created = ProviderConnection.objects.get_or_create(
            user=request.user,
            provider=normalized
        )
        conn.status = "connected"
        conn.connected_at = timezone.now()
        conn.save()

        return Response({
            "provider": conn.provider,
            "status": conn.status,
            "connected_at": conn.connected_at.isoformat()
        }, status=status.HTTP_200_OK)

class DisconnectProviderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, provider):
        prov_map = {
            "openai": "OpenAI",
            "claude": "Claude",
            "gemini": "Gemini"
        }
        normalized = prov_map.get(provider.lower())
        if not normalized:
            return Response({"detail": f"Provider '{provider}' is not supported."}, status=status.HTTP_400_BAD_REQUEST)

        conn, created = ProviderConnection.objects.get_or_create(
            user=request.user,
            provider=normalized
        )
        conn.status = "not_connected"
        conn.connected_at = None
        conn.save()

        return Response({
            "provider": conn.provider,
            "status": conn.status,
            "connected_at": None
        }, status=status.HTTP_200_OK)
