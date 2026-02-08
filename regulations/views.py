from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from .models import Regulation
from .serializers import RegulationSerializer


class RegulationListAPIView(ListAPIView):
    serializer_class = RegulationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        language = self.request.query_params.get("language", "ru")
        return Regulation.objects.filter(
            is_active=True,
            language=language,
        ).order_by("position")

