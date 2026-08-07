from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import RegisterSerializer, EmailTokenObtainPairSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer


class EmailTokenObtainPairView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = EmailTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        user = request.user
        email = request.data.get("email")
        full_name = request.data.get("full_name")

        if email:
            user.email = email
        
        if full_name:
            try:
                user.profile.full_name = full_name
                user.profile.save()
            except Exception:
                parts = full_name.strip().split(None, 1)
                user.first_name = parts[0]
                if len(parts) > 1:
                    user.last_name = parts[1]
        
        user.save()
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)