from django.urls import path
from .views import BillingProfileView, BillingHistoryView

urlpatterns = [
    path("", BillingProfileView.as_view(), name="billing-profile"),
    path("history/", BillingHistoryView.as_view(), name="billing-history"),
]
