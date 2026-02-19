from django.urls import path
from .views import (
    NewsListAPIView,
    NewsDetailAPIView,
    EmployeeListAPIView,
    InstructionAPIView,
    EnabledLanguagesAPIView,
    NewsSliderSettingsAPIView, WelcomeBlockAPIView
)

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


]