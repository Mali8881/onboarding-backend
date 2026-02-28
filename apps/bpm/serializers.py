from rest_framework import serializers

from .models import ProcessInstance, ProcessTemplate, StepInstance, StepTemplate


class StepTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StepTemplate
        fields = (
            "id",
            "process_template",
            "name",
            "order",
            "role_responsible",
            "requires_comment",
            "sla_hours",
        )


class ProcessTemplateSerializer(serializers.ModelSerializer):
    steps = StepTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = ProcessTemplate
        fields = ("id", "name", "description", "is_active", "steps")


class StepInstanceSerializer(serializers.ModelSerializer):
    step_name = serializers.CharField(source="step_template.name", read_only=True)
    order = serializers.IntegerField(source="step_template.order", read_only=True)
    responsible_username = serializers.CharField(source="responsible_user.username", read_only=True)

    class Meta:
        model = StepInstance
        fields = (
            "id",
            "step_template",
            "step_name",
            "order",
            "status",
            "responsible_user",
            "responsible_username",
            "started_at",
            "finished_at",
            "comment",
        )


class ProcessInstanceSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    steps = StepInstanceSerializer(many=True, read_only=True)

    class Meta:
        model = ProcessInstance
        fields = (
            "id",
            "template",
            "template_name",
            "created_by",
            "created_by_username",
            "status",
            "created_at",
            "steps",
        )


class ProcessInstanceCreateSerializer(serializers.Serializer):
    template_id = serializers.IntegerField()
    responsible_by_step = serializers.DictField(
        child=serializers.IntegerField(),
        required=False,
        default=dict,
    )


class StepCompleteSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)
