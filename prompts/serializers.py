from rest_framework import serializers
from .models import Prompt, PromptVersion


class PromptSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = Prompt
        fields = "__all__"
        read_only_fields = (
            "owner",
            "created_at",
            "updated_at",
        )


class PromptVersionSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source="created_by.username")

    class Meta:
        model = PromptVersion
        fields = "__all__"
        read_only_fields = ("created_by", "created_at")