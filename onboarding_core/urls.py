from django.urls import path
from .views import OnboardingDayListView, OnboardingDayDetailView

urlpatterns = [
    path("onboarding/days/", OnboardingDayListView.as_view()),
    path("onboarding/days/<uuid:id>/", OnboardingDayDetailView.as_view()),
]
