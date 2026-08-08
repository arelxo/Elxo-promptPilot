from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from connections.models import ProviderConnection
import os
from unittest import mock

class ConnectionsAPITests(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(username="testuser1", email="testuser1@gmail.com", password="password123")
        self.user2 = User.objects.create_user(username="testuser2", email="testuser2@gmail.com", password="password123")

    def test_unauthenticated_connections_get(self):
        url = reverse("connections-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_connections_get(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("connections-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify 3 default providers OpenAI, Claude, Gemini returned
        self.assertEqual(len(response.data["connections"]), 3)
        for conn in response.data["connections"]:
            self.assertEqual(conn["status"], "not_connected")

    def test_connect_without_credentials(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("connections-connect", kwargs={"provider": "openai"})
        
        # Ensure environment key is missing
        with mock.patch.dict(os.environ, {}, clear=True):
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["detail"], "Provider connection is not configured yet.")

    def test_connect_with_credentials(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("connections-connect", kwargs={"provider": "openai"})
        
        # Mock environment variable present
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-testkey123"}):
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["status"], "connected")
            self.assertEqual(response.data["provider"], "OpenAI")

    def test_disconnect(self):
        self.client.force_authenticate(user=self.user1)
        
        # Set up connected provider first
        conn = ProviderConnection.objects.create(
            user=self.user1,
            provider="OpenAI",
            status="connected"
        )
        
        url = reverse("connections-disconnect", kwargs={"provider": "openai"})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "not_connected")
        
        # Verify db status updated
        conn.refresh_from_db()
        self.assertEqual(conn.status, "not_connected")

    def test_user_isolation(self):
        # Set up connected provider for user1
        ProviderConnection.objects.create(
            user=self.user1,
            provider="OpenAI",
            status="connected"
        )
        
        # User2 should still see OpenAI as not_connected
        self.client.force_authenticate(user=self.user2)
        url = reverse("connections-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        openai_conn = next(c for c in response.data["connections"] if c["provider"] == "OpenAI")
        self.assertEqual(openai_conn["status"], "not_connected")
