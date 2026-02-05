from rest_framework import serializers
from django.contrib.auth import get_user_model
# ВАЖНО: Импортируем модели из их новых мест
from accounts.models import ReportReview, ReportComment
from reports.models import Report

User = get_user_model()

class ReportCommentSerializer(serializers.ModelSerializer):
    admin_id = serializers.PrimaryKeyRelatedField(
        source='admin',
        # Теперь User.Role.ADMIN будет доступен, так как нет циклического импорта
        queryset=User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN]),
        write_only=True
    )
    admin_name = serializers.CharField(source='admin.get_full_name', read_only=True)

    class Meta:
        model = ReportComment
        fields = ['id', 'report', 'admin_id', 'admin_name', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']

class ReportReviewSerializer(serializers.ModelSerializer):
    comment = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ReportReview
        fields = ['id', 'report', 'reviewer', 'status', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['id', 'reviewer', 'created_at', 'updated_at']

    def validate(self, data):
        status = data.get('status')
        comment = data.get('comment', '')
        if status in [ReportReview.ReviewStatus.REVISION, ReportReview.ReviewStatus.REJECTED]:
            if not comment or not comment.strip():
                raise serializers.ValidationError({'comment': 'Комментарий обязателен для этого статуса'})
        return data

    def create(self, validated_data):
        comment = validated_data.pop('comment', None)
        request = self.context.get('request')
        if request and request.user:
            validated_data['reviewer'] = request.user

        report = validated_data['report']
        review, created = ReportReview.objects.update_or_create(
            report=report,
            defaults=validated_data
        )

        if comment and comment.strip():
            ReportComment.objects.create(
                report=report,
                admin=request.user,
                comment=comment.strip()
            )
        return review


class ReportListSerializer:
    pass