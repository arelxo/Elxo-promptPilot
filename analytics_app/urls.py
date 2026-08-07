from django.urls import path
from .views import AnalyticsDataView

urlpatterns = [
    path("", AnalyticsDataView.as_view(), name="analytics_data"),
]
