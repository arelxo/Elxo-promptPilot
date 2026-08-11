from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import os
import time
import concurrent.futures

from .models import Prompt, PromptVersion
from .serializers import PromptSerializer, PromptVersionSerializer
from analytics_app.models import AnalyticsEvent
from connections.models import ProviderConnection

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
            tokens = max(1, len(prompt.content) // 4)
            cost = tokens * 0.00002
            latency = 150
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

    @action(detail=False, methods=['post'])
    def run(self, request):
        prompt_text = request.data.get("prompt", "").strip()
        provider = request.data.get("provider", "all").lower()
        temperature = float(request.data.get("temperature", 0.3))
        max_tokens = int(request.data.get("max_tokens", 2048))

        if not prompt_text:
            return Response({"detail": "Prompt text cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        # Map frontend provider name to normalized values
        prov_map = {
            "openai": ("OpenAI", "OPENAI_API_KEY"),
            "anthropic": ("Claude", "ANTHROPIC_API_KEY"),
            "claude": ("Claude", "ANTHROPIC_API_KEY"),
            "gemini": ("Gemini", "GEMINI_API_KEY")
        }

        # Resolve providers to run
        run_targets = []
        if provider == "all":
            for key, (p_name, key_var) in prov_map.items():
                if key == "claude": # avoid duplicate Claude keys
                    continue
                run_targets.append((p_name, key_var))
        else:
            target = prov_map.get(provider)
            if not target:
                return Response({"detail": f"Provider '{provider}' is not supported."}, status=status.HTTP_400_BAD_REQUEST)
            run_targets.append(target)

        # Filter targets to connected ones or return specific credentials missing
        connected_targets = []
        for p_name, key_var in run_targets:
            conn = ProviderConnection.objects.filter(user=request.user, provider=p_name, status="connected").first()
            api_key = os.environ.get(key_var)

            if not api_key:
                if provider != "all":
                    return Response({"detail": f"Credentials missing for {p_name} in server environment."}, status=status.HTTP_400_BAD_REQUEST)
                continue
            
            if not conn:
                if provider != "all":
                    return Response({"detail": f"{p_name} is not connected. Please connect it in the Connections panel."}, status=status.HTTP_400_BAD_REQUEST)
                continue

            connected_targets.append((p_name, api_key))

        if not connected_targets:
            return Response({"detail": "No active connected AI provider found. Please connect and verify a provider first."}, status=status.HTTP_400_BAD_REQUEST)

        # Worker run function
        def run_model(p_name, api_key):
            start = time.time()
            try:
                if p_name == "OpenAI":
                    import openai
                    client = openai.OpenAI(api_key=api_key)
                    resp = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt_text}],
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    latency = int((time.time() - start) * 1000)
                    in_t = resp.usage.prompt_tokens
                    out_t = resp.usage.completion_tokens
                    tot_t = resp.usage.total_tokens
                    cost = (in_t * 0.0005 / 1000) + (out_t * 0.0015 / 1000)

                    AnalyticsEvent.objects.create(
                        user=request.user,
                        provider="openai",
                        tokens_used=tot_t,
                        estimated_cost=cost,
                        latency_ms=latency,
                        status="success"
                    )
                    return {
                        "provider": "OpenAI",
                        "status": "success",
                        "response": resp.choices[0].message.content,
                        "latency": latency,
                        "tokens": tot_t,
                        "cost": cost
                    }

                elif p_name == "Claude":
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key)
                    resp = client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=[{"role": "user", "content": prompt_text}]
                    )
                    latency = int((time.time() - start) * 1000)
                    in_t = resp.usage.input_tokens
                    out_t = resp.usage.output_tokens
                    tot_t = in_t + out_t
                    cost = (in_t * 0.00025 / 1000) + (out_t * 0.00125 / 1000)

                    AnalyticsEvent.objects.create(
                        user=request.user,
                        provider="claude",
                        tokens_used=tot_t,
                        estimated_cost=cost,
                        latency_ms=latency,
                        status="success"
                    )
                    return {
                        "provider": "Claude",
                        "status": "success",
                        "response": resp.content[0].text,
                        "latency": latency,
                        "tokens": tot_t,
                        "cost": cost
                    }

                elif p_name == "Gemini":
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    resp = model.generate_content(
                        prompt_text,
                        generation_config=genai.types.GenerationConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens
                        )
                    )
                    latency = int((time.time() - start) * 1000)
                    in_t = 0
                    out_t = 0
                    try:
                        in_t = resp.usage_metadata.prompt_token_count
                        out_t = resp.usage_metadata.candidates_token_count
                    except Exception:
                        in_t = len(prompt_text) // 4
                        out_t = len(resp.text) // 4

                    tot_t = in_t + out_t
                    cost = (in_t * 0.000075 / 1000) + (out_t * 0.0003 / 1000)

                    AnalyticsEvent.objects.create(
                        user=request.user,
                        provider="gemini",
                        tokens_used=tot_t,
                        estimated_cost=cost,
                        latency_ms=latency,
                        status="success"
                    )
                    return {
                        "provider": "Gemini",
                        "status": "success",
                        "response": resp.text,
                        "latency": latency,
                        "tokens": tot_t,
                        "cost": cost
                    }

            except Exception as e:
                latency = int((time.time() - start) * 1000)
                AnalyticsEvent.objects.create(
                    user=request.user,
                    provider=p_name.lower(),
                    tokens_used=0,
                    estimated_cost=0.0,
                    latency_ms=latency,
                    status="failed"
                )
                return {
                    "provider": p_name,
                    "status": "error",
                    "detail": str(e),
                    "latency": latency
                }

        # Run targets sequentially to prevent database locking issues
        results = []
        for p_name, api_key in connected_targets:
            results.append(run_model(p_name, api_key))

        return Response({"results": results}, status=status.HTTP_200_OK)


class PromptVersionViewSet(viewsets.ModelViewSet):
    serializer_class = PromptVersionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PromptVersion.objects.filter(
            created_by=self.request.user
        ).order_by("-version_number")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)