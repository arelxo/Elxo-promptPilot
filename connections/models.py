from django.db import models
from django.contrib.auth.models import User

class ProviderConnection(models.Model):
    PROVIDER_CHOICES = [
        ("OpenAI", "OpenAI"),
        ("Claude", "Claude"),
        ("Gemini", "Gemini")
    ]
    
    STATUS_CHOICES = [
        ("connected", "Connected"),
        ("not_connected", "Not Connected")
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="provider_connections")
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="not_connected")
    connected_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    display_name = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ("user", "provider")

    def __str__(self):
        return f"{self.user.username} - {self.provider} ({self.status})"
