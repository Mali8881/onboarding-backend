from rest_framework import generics, permissions

from .models import OnboardingDay
from .serializers import OnboardingDayListSerializer, OnboardingDayDetailSerializer


class OnboardingDayListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OnboardingDayListSerializer

    def get_queryset(self):
        # пока так: показываем только активные
        return OnboardingDay.objects.filter(is_active=True).order_by("position", "day_number")


class OnboardingDayDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OnboardingDayDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return OnboardingDay.objects.filter(is_active=True).prefetch_related("materials")
