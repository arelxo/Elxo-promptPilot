from django.contrib import admin
from django.urls import path, include
from accounts.views import EmailTokenObtainPairView

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/", include("prompts.urls")),

    path("api/dashboard/", include("dashboard.urls")),

    path("api/accounts/", include("accounts.urls")),

    path("api/optimizer/", include("optimizer.urls")),

    path("api/analytics/", include("analytics_app.urls")),

    path("api/billing/", include("billing.urls")),

    path("api/connections/", include("connections.urls")),

    path("api/token/", EmailTokenObtainPairView.as_view(), name="token_obtain_pair"),

    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]