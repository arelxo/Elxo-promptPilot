from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PromptViewSet, PromptVersionViewSet

router = DefaultRouter()
router.register(r"prompts", PromptViewSet, basename="prompt")
router.register(r"versions", PromptVersionViewSet, basename="prompt-version")

urlpatterns = [
    path("", include(router.urls)),
]