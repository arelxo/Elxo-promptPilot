from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    THEME_CHOICES = [
        ("light", "Light"),
        ("dark", "Dark"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    full_name = models.CharField(max_length=150)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    bio = models.TextField(blank=True)

    company = models.CharField(max_length=150, blank=True)

    timezone = models.CharField(max_length=100, default="UTC")

    language = models.CharField(max_length=50, default="English")

    theme = models.CharField(
        max_length=20,
        choices=THEME_CHOICES,
        default="dark"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username