from django.urls import path

from .views import (
    DeskAvailabilityAPIView,
    DeskBookingCreateAPIView,
    DeskBookingDeleteAPIView,
    DeskListAPIView,
    MeetingRoomAvailabilityAPIView,
    MeetingRoomBookingCreateAPIView,
    MeetingRoomBookingDeleteAPIView,
    MeetingRoomBookingOptionsAPIView,
    MeetingRoomListAPIView,
)

urlpatterns = [
    path("", DeskListAPIView.as_view()),
    path("availability/", DeskAvailabilityAPIView.as_view()),
    path("bookings/", DeskBookingCreateAPIView.as_view()),
    path("bookings/<int:booking_id>/", DeskBookingDeleteAPIView.as_view()),
    path("rooms/", MeetingRoomListAPIView.as_view()),
    path("rooms/options/", MeetingRoomBookingOptionsAPIView.as_view()),
    path("rooms/availability/", MeetingRoomAvailabilityAPIView.as_view()),
    path("rooms/bookings/", MeetingRoomBookingCreateAPIView.as_view()),
    path("rooms/bookings/<int:booking_id>/", MeetingRoomBookingDeleteAPIView.as_view()),
]
