from rest_framework import serializers

from .models import KBArticle, KBCategory


class KBCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = KBCategory
        fields = ("id", "name", "parent")


class KBArticleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = KBArticle
        fields = (
            "id",
            "title",
            "content",
            "category",
            "category_name",
            "tags",
            "visibility",
            "department",
            "role_name",
            "created_by",
            "created_by_username",
            "updated_at",
            "is_published",
        )
        read_only_fields = ("created_by", "updated_at")

    def validate(self, attrs):
        visibility = attrs.get("visibility", getattr(self.instance, "visibility", KBArticle.Visibility.ALL))
        department = attrs.get("department", getattr(self.instance, "department", None))
        role_name = attrs.get("role_name", getattr(self.instance, "role_name", None))
        if visibility == KBArticle.Visibility.DEPARTMENT and not department:
            raise serializers.ValidationError({"department": "Department is required for department visibility."})
        if visibility == KBArticle.Visibility.ROLE and not role_name:
            raise serializers.ValidationError({"role_name": "Role is required for role visibility."})
        return attrs
