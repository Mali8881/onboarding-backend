from django.urls import path
from .views import *
from .views import MyProfileAPIView, MyProfilePasswordAPIView



urlpatterns = [
    path("login/", LoginView.as_view()),
    path("me/profile/", MyProfileAPIView.as_view(), name="my-profile"),
    path("me/profile/password/", MyProfilePasswordAPIView.as_view(), name="my-profile-password"),
    path("employee/home/", EmployeeHomeAPIView.as_view(), name="employee-home"),
    path("company/structure/", CompanyStructureAPIView.as_view(), name="company-structure"),
    path("positions/", PositionListAPIView.as_view()),
    path("password-reset/request/", PasswordResetRequestAPIView.as_view()),
    path("password-reset/confirm/", PasswordResetConfirmAPIView.as_view()),
    path("org/departments/", DepartmentListCreateAPIView.as_view(), name="org-department-list-create"),
    path("org/departments/<int:pk>/", DepartmentDetailAPIView.as_view(), name="org-department-detail"),
    path("org/positions/", PositionListCreateAPIView.as_view(), name="org-position-list-create"),
    path("org/positions/<int:pk>/", PositionDetailAPIView.as_view(), name="org-position-detail"),
    path("org/structure/", OrgStructureAPIView.as_view(), name="org-structure"),
]

