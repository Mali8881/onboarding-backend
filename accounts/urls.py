from django.urls import path
from .views import *
from .views import MyProfileAPIView, MyProfilePasswordAPIView
from config.frontend_compat_views import (
    FrontendPromotionRequestsActionAPIView,
    FrontendPromotionRequestsAPIView,
    FrontendUsersCollectionAPIView,
    FrontendUsersDetailAPIView,
    FrontendUsersSetRoleAPIView,
    FrontendUsersToggleStatusAPIView,
)



urlpatterns = [
    path("login/", LoginView.as_view()),
    path("me/profile/", MyProfileAPIView.as_view(), name="my-profile"),
    path("me/profile/password/", MyProfilePasswordAPIView.as_view(), name="my-profile-password"),
    path("me/team/", MeTeamAPIView.as_view(), name="my-team"),
    path("employee/home/", EmployeeHomeAPIView.as_view(), name="employee-home"),
    path("company/structure/", CompanyStructureAPIView.as_view(), name="company-structure"),
    path("positions/", PositionListAPIView.as_view()),
    path("password-reset/request/", PasswordResetRequestAPIView.as_view()),
    path("password-reset/confirm/", PasswordResetConfirmAPIView.as_view()),
    path("org/departments/", DepartmentListCreateAPIView.as_view(), name="org-department-list-create"),
    path("org/departments/<int:pk>/", DepartmentDetailAPIView.as_view(), name="org-department-detail"),
    # Alias: subdivisions are child departments.
    path("org/subdivisions/", DepartmentListCreateAPIView.as_view(), name="org-subdivision-list-create"),
    path("org/subdivisions/<int:pk>/", DepartmentDetailAPIView.as_view(), name="org-subdivision-detail"),
    path("org/positions/", PositionListCreateAPIView.as_view(), name="org-position-list-create"),
    path("org/positions/<int:pk>/", PositionDetailAPIView.as_view(), name="org-position-detail"),
    path("org/structure/", OrgStructureAPIView.as_view(), name="org-structure"),
    # Frontend compatibility aliases for promotion requests under /accounts/*
    path("promotion-requests/", FrontendPromotionRequestsAPIView.as_view(), name="accounts-promotion-requests"),
    path(
        "promotion-requests/<int:request_id>/<str:action>/",
        FrontendPromotionRequestsActionAPIView.as_view(),
        name="accounts-promotion-requests-action",
    ),
    # Frontend compatibility aliases for admin users management in /accounts/org/*
    path("org/users/", FrontendUsersCollectionAPIView.as_view(), name="org-users-list-create"),
    path("org/users/<int:user_id>/", FrontendUsersDetailAPIView.as_view(), name="org-users-detail"),
    path("org/users/<int:user_id>/toggle-status/", FrontendUsersToggleStatusAPIView.as_view(), name="org-users-toggle-status"),
    path("org/users/<int:user_id>/set-role/", FrontendUsersSetRoleAPIView.as_view(), name="org-users-set-role"),
]

