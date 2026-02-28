from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    NewsListAPIView,
    NewsDetailAPIView,
    EmployeeListAPIView,
    InstructionAPIView,
    EnabledLanguagesAPIView,
    NewsSliderSettingsAPIView,
    WelcomeBlockAPIView,
    FeedbackCreateView,
    FeedbackAdminView,
    CoursesMenuAccessAPIView,
    AdminCourseViewSet,
    AdminCourseAssignAPIView,
    AvailableCoursesListAPIView,
    MyCoursesListAPIView,
    CourseSelfEnrollAPIView,
    AcceptAssignedCourseAPIView,
    StartCourseAPIView,
    UpdateCourseProgressAPIView,
)

router = DefaultRouter()
router.register("admin/courses", AdminCourseViewSet, basename="admin-courses")

urlpatterns = [
    # Новости
    path("news/", NewsListAPIView.as_view(), name='news-list'),
    path("news/<uuid:id>/", NewsDetailAPIView.as_view(), name='news-detail'), # Поменял pk на id для соответствия view
    path("news/slider-settings/", NewsSliderSettingsAPIView.as_view(), name='slider-settings'),

    # Приветственный блок
    path("welcome/", WelcomeBlockAPIView.as_view(), name='welcome'),

    # Сотрудники
    path("employees/", EmployeeListAPIView.as_view(), name='employee-list'),

    # Инструкции и языки
    path("instruction/", InstructionAPIView.as_view(), name='instruction'),
    path("languages/", EnabledLanguagesAPIView.as_view(), name='languages'),
    path("feedback/", FeedbackCreateView.as_view(), name="feedback-create"),
    path(
        "admin/feedback/",
        FeedbackAdminView.as_view({"get": "list"}),
        name="feedback-admin-list",
    ),
    path(
        "admin/feedback/stats/",
        FeedbackAdminView.as_view({"get": "stats"}),
        name="feedback-admin-stats",
    ),
    path(
        "admin/feedback/meta/",
        FeedbackAdminView.as_view({"get": "meta"}),
        name="feedback-admin-meta",
    ),
    path(
        "admin/feedback/<uuid:pk>/",
        FeedbackAdminView.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="feedback-admin-detail",
    ),
    path(
        "admin/feedback/<uuid:pk>/set-status/",
        FeedbackAdminView.as_view({"post": "set_status"}),
        name="feedback-admin-set-status",
    ),
    path("courses/menu-access/", CoursesMenuAccessAPIView.as_view(), name="courses-menu-access"),
    path("courses/available/", AvailableCoursesListAPIView.as_view(), name="courses-available"),
    path("courses/my/", MyCoursesListAPIView.as_view(), name="courses-my"),
    path("courses/self-enroll/", CourseSelfEnrollAPIView.as_view(), name="courses-self-enroll"),
    path("courses/accept/", AcceptAssignedCourseAPIView.as_view(), name="courses-accept"),
    path("courses/start/", StartCourseAPIView.as_view(), name="courses-start"),
    path("courses/progress/", UpdateCourseProgressAPIView.as_view(), name="courses-progress"),
    path("admin/courses/assign/", AdminCourseAssignAPIView.as_view(), name="admin-courses-assign"),

]

urlpatterns += router.urls
