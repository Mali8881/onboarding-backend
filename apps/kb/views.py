from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from accounts.access_policy import AccessPolicy
from accounts.models import Role

from .models import KBArticle, KBCategory, KBViewLog
from .permissions import IsAdminLike
from .serializers import KBArticleSerializer, KBCategorySerializer


User = get_user_model()


def _visible_articles_for(user):
    qs = KBArticle.objects.filter(is_published=True).select_related("category", "department", "created_by")
    if AccessPolicy.is_admin_like(user):
        return qs
    role_name = user.role.name if getattr(user, "role_id", None) else ""
    return qs.filter(
        Q(visibility=KBArticle.Visibility.ALL)
        | Q(visibility=KBArticle.Visibility.DEPARTMENT, department_id=user.department_id)
        | Q(visibility=KBArticle.Visibility.ROLE, role_name=role_name)
    )


class KBArticleListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = _visible_articles_for(request.user)
        category_id = request.query_params.get("category_id")
        tag = request.query_params.get("tag")
        if category_id:
            qs = qs.filter(category_id=category_id)
        if tag:
            qs = qs.filter(tags__contains=[tag])
        return Response(KBArticleSerializer(qs, many=True).data)


class KBArticleDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        article = get_object_or_404(_visible_articles_for(request.user), pk=pk)
        KBViewLog.objects.create(user=request.user, article=article)
        return Response(KBArticleSerializer(article).data)


class KBReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _audience_count(self, article: KBArticle) -> int:
        users = User.objects.filter(is_active=True)
        if article.visibility == KBArticle.Visibility.ALL:
            return users.count()
        if article.visibility == KBArticle.Visibility.DEPARTMENT:
            return users.filter(department_id=article.department_id).count()
        if article.visibility == KBArticle.Visibility.ROLE:
            return users.filter(role__name=article.role_name).count()
        return 0

    def _serialize_row(self, row, window_start=None):
        article = row["article"]
        unique_views = row["unique_views"]
        views = row["views"]
        audience = self._audience_count(article)
        percent = round((unique_views / audience) * 100, 2) if audience else 0.0
        payload = {
            "article_id": article.id,
            "title": article.title,
            "views": views,
            "unique_views": unique_views,
            "audience_count": audience,
            "view_percent": percent,
        }
        if window_start:
            payload["window_start"] = window_start.date().isoformat()
        return payload

    def get(self, request):
        if not (AccessPolicy.is_admin_like(request.user) or AccessPolicy.is_teamlead(request.user)):
            return Response({"detail": "Access denied."}, status=403)

        base_qs = KBViewLog.objects.select_related("article")
        if AccessPolicy.is_teamlead(request.user):
            subordinate_ids = list(request.user.team_members.values_list("id", flat=True))
            allowed_ids = subordinate_ids + [request.user.id]
            base_qs = base_qs.filter(user_id__in=allowed_ids)

        thirty_days_ago = timezone.now() - timedelta(days=30)
        rows_30 = (
            base_qs.filter(viewed_at__gte=thirty_days_ago)
            .values("article_id")
            .annotate(views=Count("id"), unique_views=Count("user_id", distinct=True))
            .order_by("-views")[:20]
        )
        rows_all = (
            base_qs.values("article_id")
            .annotate(views=Count("id"), unique_views=Count("user_id", distinct=True))
            .order_by("-views")[:20]
        )

        article_map = {
            a.id: a
            for a in KBArticle.objects.filter(
                id__in={r["article_id"] for r in rows_30} | {r["article_id"] for r in rows_all}
            )
        }
        top_30 = [
            self._serialize_row({**row, "article": article_map[row["article_id"]]}, window_start=thirty_days_ago)
            for row in rows_30
            if row["article_id"] in article_map
        ]
        top_all = [
            self._serialize_row({**row, "article": article_map[row["article_id"]]})
            for row in rows_all
            if row["article_id"] in article_map
        ]
        return Response({"top_30_days": top_30, "top_all_time": top_all})


class KBCategoryAdminViewSet(ModelViewSet):
    queryset = KBCategory.objects.all().order_by("name")
    serializer_class = KBCategorySerializer
    permission_classes = [IsAuthenticated, IsAdminLike]


class KBArticleAdminViewSet(ModelViewSet):
    queryset = KBArticle.objects.select_related("category", "department", "created_by").all()
    serializer_class = KBArticleSerializer
    permission_classes = [IsAuthenticated, IsAdminLike]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
