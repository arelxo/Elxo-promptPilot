from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from billing.models import UserBillingProfile, Invoice

class BillingAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.user1 = User.objects.create_user(username="testuser1", email="testuser1@gmail.com", password="password123")
        self.user2 = User.objects.create_user(username="testuser2", email="testuser2@gmail.com", password="password123")
        
        # Invoices for user1
        self.invoice = Invoice.objects.create(
            user=self.user1,
            date="2026-08-01",
            description="Test Invoice",
            amount=79.00,
            status="Paid"
        )

    def test_new_user_default_billing_profile(self):
        # UserBillingProfile should be created automatically via signals
        profile = UserBillingProfile.objects.filter(user=self.user2).first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.plan_name, "Free")
        self.assertEqual(profile.plan_status, "active")
        self.assertEqual(profile.requests_limit, 1000)

    def test_unauthenticated_billing_get(self):
        url = reverse("billing-profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_billing_get(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("billing-profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["plan"]["name"], "Free")
        self.assertEqual(response.data["usage"]["requests_limit"], 1000)
        self.assertEqual(len(response.data["billing_history"]), 1)

    def test_authenticated_billing_history(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("billing-history")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["amount"], 79.00)

    def test_user_isolation(self):
        # User2 should not see User1's invoices
        self.client.force_authenticate(user=self.user2)
        url = reverse("billing-profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["billing_history"]), 0)
