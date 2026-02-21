from rest_framework import serializers

from .models import Regulation, RegulationAcknowledgement


class RegulationSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()
    is_acknowledged = serializers.SerializerMethodField()
    acknowledged_at = serializers.SerializerMethodField()

    class Meta:
        model = Regulation
        fields = (
            "id",
            "title",
            "description",
            "type",
            "content",
            "action",
            "is_mandatory_on_day_one",
            "is_acknowledged",
            "acknowledged_at",
            "position",
            "language",
        )

    def get_content(self, obj):
        if obj.type == Regulation.RegulationType.LINK:
            return obj.external_url
        if obj.type == Regulation.RegulationType.FILE and obj.file:
            return obj.file.url
        return None

    def get_action(self, obj):
        if obj.type == Regulation.RegulationType.LINK:
            return "open"
        return "download"

    def _ack(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        ack_map = self.context.get("ack_map")
        if ack_map is not None:
            return ack_map.get(obj.id)

        return RegulationAcknowledgement.objects.filter(
            user=request.user,
            regulation=obj,
        ).first()

    def get_is_acknowledged(self, obj):
        return self._ack(obj) is not None

    def get_acknowledged_at(self, obj):
        ack = self._ack(obj)
        return ack.acknowledged_at if ack else None


class RegulationAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regulation
        fields = (
            "id",
            "title",
            "description",
            "type",
            "external_url",
            "file",
            "position",
            "is_active",
            "is_mandatory_on_day_one",
            "language",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        reg_type = attrs.get("type", getattr(self.instance, "type", None))
        external_url = attrs.get("external_url", getattr(self.instance, "external_url", None))
        file = attrs.get("file", getattr(self.instance, "file", None))

        if reg_type == Regulation.RegulationType.LINK:
            if not external_url:
                raise serializers.ValidationError(
                    {"external_url": "Для типа 'link' ссылка обязательна."}
                )
            attrs["file"] = None

        if reg_type == Regulation.RegulationType.FILE:
            if not file:
                raise serializers.ValidationError(
                    {"file": "Для типа 'file' файл обязателен."}
                )
            attrs["external_url"] = None

        return attrs


class RegulationAcknowledgementSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulationAcknowledgement
        fields = (
            "id",
            "user",
            "regulation",
            "acknowledged_at",
            "user_full_name",
            "regulation_title",
        )
        read_only_fields = fields

