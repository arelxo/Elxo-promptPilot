from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user


class EmailTokenObtainPairSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = User.objects.filter(email=email).first()
        if not user:
            user = User.objects.filter(username=email).first()

        if user:
            authenticated_user = authenticate(username=user.username, password=password)
        else:
            authenticated_user = None

        if not authenticated_user:
            raise serializers.ValidationError("No active account found with the given credentials")

        if not authenticated_user.is_active:
            raise serializers.ValidationError("This user account is inactive.")

        refresh = RefreshToken.for_user(authenticated_user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name"]

    def get_full_name(self, obj):
        try:
            return obj.profile.full_name
        except Exception:
            if obj.first_name or obj.last_name:
                return f"{obj.first_name} {obj.last_name}".strip()
            return obj.username