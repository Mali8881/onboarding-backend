from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserBadge
from .services import award_on_time_badges, update_user_streak


class MyGamificationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        streak = update_user_streak(request.user)
        award_on_time_badges(request.user, current_streak=streak.current_streak)

        badges = (
            UserBadge.objects
            .filter(user=request.user)
            .select_related("badge")
            .order_by("-awarded_at")
        )
        return Response(
            {
                "current_streak": streak.current_streak,
                "longest_streak": streak.longest_streak,
                "last_report_date": streak.last_report_date,
                "badges": [
                    {
                        "code": item.badge.code,
                        "name": item.badge.name,
                        "description": item.badge.description,
                        "awarded_at": item.awarded_at,
                    }
                    for item in badges
                ],
            }
        )
