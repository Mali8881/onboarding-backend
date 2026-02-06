from rest_framework import serializers
from .models import Regulation


class RegulationSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()

    class Meta:
        model = Regulation
        fields = (
            "id",
            "title",
            "description",
            "type",
            "content",
            "position",
            "language",
        )

    def get_content(self, obj):
        if obj.type == "link":
            return obj.external_url
        if obj.type == "file" and obj.file:
            return obj.file.url
        return None
