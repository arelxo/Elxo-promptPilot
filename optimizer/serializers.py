from rest_framework import serializers

class OptimizePromptRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(required=True, allow_blank=True)
    remove_boilerplate = serializers.BooleanField(default=True)
    inject_guardrails = serializers.BooleanField(default=True)
    detect_variables = serializers.BooleanField(default=True)

class OptimizePromptResponseSerializer(serializers.Serializer):
    original_prompt = serializers.CharField()
    optimized_prompt = serializers.CharField()
    original_tokens = serializers.IntegerField()
    optimized_tokens = serializers.IntegerField()
    reduction_percentage = serializers.IntegerField()
