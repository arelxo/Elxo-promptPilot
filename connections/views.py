from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import ProviderConnection
from django.utils import timezone
import os
import openai
import anthropic
import google.generativeai as genai

class ConnectionsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        providers = [
            ("OpenAI", "OPENAI_API_KEY"),
            ("Claude", "ANTHROPIC_API_KEY"),
            ("Gemini", "GEMINI_API_KEY")
        ]
        connections_data = []

        for p_name, key_var in providers:
            conn, created = ProviderConnection.objects.get_or_create(
                user=request.user,
                provider=p_name
            )
            
            # Determine dynamic status based on key presence and db connection status
            has_key = bool(os.environ.get(key_var))
            if not has_key:
                conn_status = "credentials_missing"
            elif conn.status == "connected":
                conn_status = "connected"
            else:
                conn_status = "not_connected"
                
            connections_data.append({
                "provider": conn.provider,
                "status": conn_status,
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

class TestConnectionView(APIView):
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

        key_var = f"{normalized.upper()}_API_KEY" if normalized != "Claude" else "ANTHROPIC_API_KEY"
        api_key = os.environ.get(key_var)
        if not api_key:
            return Response({"detail": "Provider credentials are missing in server environment."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if normalized == "OpenAI":
                client = openai.OpenAI(api_key=api_key)
                client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "say ok"}],
                    max_tokens=5
                )
            elif normalized == "Claude":
                client = anthropic.Anthropic(api_key=api_key)
                client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=5,
                    messages=[{"role": "user", "content": "say ok"}]
                )
            elif normalized == "Gemini":
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                model.generate_content("say ok", generation_config=genai.types.GenerationConfig(max_output_tokens=5))
            
            return Response({"status": "success", "detail": f"Connection to {normalized} verified successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "detail": f"API validation failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
