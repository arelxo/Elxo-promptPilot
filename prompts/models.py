from django.db import models
from django.contrib.auth.models import User


class Prompt(models.Model):

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    CATEGORY_CHOICES = [
        ("marketing", "Marketing"),
        ("coding", "Coding"),
        ("business", "Business"),
        ("design", "Design"),
        ("education", "Education"),
        ("productivity", "Productivity"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    content = models.TextField()

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="other"
    )

    tags = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma separated tags"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="prompts"
    )

    is_favorite = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class PromptVersion(models.Model):
    prompt = models.ForeignKey(
        Prompt,
        on_delete=models.CASCADE,
        related_name="versions"
    )

    version_number = models.PositiveIntegerField()

    content = models.TextField()

    change_note = models.CharField(
        max_length=255,
        blank=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = ("prompt", "version_number")

    def __str__(self):
        return f"{self.prompt.title} - v{self.version_number}"