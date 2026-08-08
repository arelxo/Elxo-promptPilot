from django.db import models
from django.contrib.auth.models import User

class UserBillingProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="billing_profile")
    plan_name = models.CharField(max_length=100, default="Free")
    plan_status = models.CharField(max_length=50, default="active")
    billing_cycle = models.CharField(max_length=50, default="monthly")
    requests_limit = models.IntegerField(default=1000)
    tokens_limit = models.IntegerField(default=100000)
    next_billing_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan_name}"

class Invoice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invoices")
    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default="Paid")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice {self.id} - {self.user.username} - {self.amount}"

# Signal receiver to create billing profile automatically on user creation
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_billing_profile(sender, instance, created, **kwargs):
    if created:
        UserBillingProfile.objects.create(user=instance)
