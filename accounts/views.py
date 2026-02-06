from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token

from .serializers import MeSerializer, MeUpdateSerializer, PhotoUploadSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user, context={"request": request}).data)

    def patch(self, request):
        ser = MeUpdateSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(MeSerializer(request.user, context={"request": request}).data, status=status.HTTP_200_OK)


class MePhotoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = PhotoUploadSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(MeSerializer(request.user, context={"request": request}).data, status=status.HTTP_200_OK)
class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "full_name": user.get_full_name(),
            "email": user.email,
            "language": getattr(user, "language", "ru"),
        })

class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"detail": "Logged out"})

class ChangeLanguageAPIView(APIView):
        permission_classes = [IsAuthenticated]

        def post(self, request):
            request.user.language = request.data["language"]
            request.user.save()
            return Response({"detail": "Language updated"})
