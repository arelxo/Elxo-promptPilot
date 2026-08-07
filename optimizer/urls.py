from django.urls import path
from .views import OptimizePromptView

urlpatterns = [
    path("optimize/", OptimizePromptView.as_view(), name="optimize_prompt"),
]
