from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from unittest import mock
import os

from prompts.models import Prompt
from connections.models import ProviderConnection
from analytics_app.models import AnalyticsEvent

class PromptsAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="testuser@gmail.com", password="password123")
        self.client.force_authenticate(user=self.user)

    def test_run_prompt_validation_error(self):
        url = reverse("prompt-run")
        response = self.client.post(url, {"prompt": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Prompt text cannot be empty", response.data["detail"])

    def test_run_prompt_no_connections(self):
        url = reverse("prompt-run")
        # Ensure no connections exist
        ProviderConnection.objects.all().delete()
        response = self.client.post(url, {"prompt": "Hello"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No active connected AI provider found", response.data["detail"])

    def test_run_prompt_credentials_missing(self):
        url = reverse("prompt-run")
        # Connect provider but remove key
        ProviderConnection.objects.create(
            user=self.user,
            provider="OpenAI",
            status="connected"
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            response = self.client.post(url, {"prompt": "Hello", "provider": "openai"})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Credentials missing for OpenAI", response.data["detail"])

    @mock.patch("openai.OpenAI")
    def test_run_prompt_success_openai(self, mock_openai):
        url = reverse("prompt-run")
        # Setup connection and environment
        ProviderConnection.objects.create(
            user=self.user,
            provider="OpenAI",
            status="connected"
        )
        
        # Configure mock OpenAI response
        mock_client = mock.Mock()
        mock_openai.return_value = mock_client
        mock_response = mock.Mock()
        mock_response.choices = [mock.Mock(message=mock.Mock(content="Mocked OpenAI response"))]
        mock_response.usage = mock.Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_client.chat.completions.create.return_value = mock_response

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-openai-key"}):
            response = self.client.post(url, {"prompt": "Hello", "provider": "openai"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data["results"]), 1)
            result = response.data["results"][0]
            self.assertEqual(result["provider"], "OpenAI")
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["response"], "Mocked OpenAI response")
            self.assertEqual(result["tokens"], 30)

            # Verify AnalyticsEvent creation
            events = AnalyticsEvent.objects.filter(user=self.user, provider="openai")
            self.assertEqual(events.count(), 1)
            self.assertEqual(events.first().status, "success")
            self.assertEqual(events.first().tokens_used, 30)

    @mock.patch("anthropic.Anthropic")
    def test_run_prompt_success_claude(self, mock_anthropic):
        url = reverse("prompt-run")
        ProviderConnection.objects.create(
            user=self.user,
            provider="Claude",
            status="connected"
        )

        mock_client = mock.Mock()
        mock_anthropic.return_value = mock_client
        mock_response = mock.Mock()
        mock_response.content = [mock.Mock(text="Mocked Claude response")]
        mock_response.usage = mock.Mock(input_tokens=15, output_tokens=25)
        mock_client.messages.create.return_value = mock_response

        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-anthropic-key"}):
            response = self.client.post(url, {"prompt": "Hello", "provider": "claude"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data["results"]), 1)
            result = response.data["results"][0]
            self.assertEqual(result["provider"], "Claude")
            self.assertEqual(result["response"], "Mocked Claude response")
            self.assertEqual(result["tokens"], 40)

            # Verify AnalyticsEvent creation
            events = AnalyticsEvent.objects.filter(user=self.user, provider="claude")
            self.assertEqual(events.count(), 1)
            self.assertEqual(events.first().status, "success")
            self.assertEqual(events.first().tokens_used, 40)
