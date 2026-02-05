from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

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
