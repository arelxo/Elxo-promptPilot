from django.contrib import admin
from .models import Prompt, PromptVersion

admin.site.register(Prompt)
admin.site.register(PromptVersion)