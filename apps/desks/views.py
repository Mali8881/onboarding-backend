from collections import defaultdict
from datetime import date, datetime
from datetime import time as dt_time

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role
from common.models import Notification
from work_schedule.services import resolve_user_shift_for_date

from .models import Desk, DeskBooking, MeetingRoom, MeetingRoomBooking
from .serializers import (
    DeskBookingCreateSerializer,
    DeskSerializer,
    MeetingRoomBookingCreateSerializer,
    MeetingRoomSerializer,
)

User = get_user_model()

DEFAULT_BOOKING_START = dt_time(hour=9, minute=0)
DEFAULT_BOOKING_END = dt_time(hour=18, minute=0)
ROOM_DAY_START = dt_time(hour=9, minute=0)
ROOM_DAY_END = dt_time(hour=21, minute=0)
DEFAULT_ROOM_BOOKING_DURATION_MINUTES = 30


def _parse_iso_date(value, *, default_today=False):
    if value in (None, ""):
        return timezone.localdate() if default_today else None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _parse_iso_time(value):
    if value in (None, ""):
        return None
    try:
        return dt_time.fromisoformat(str(value))
    except ValueError:
        return None


def _format_hhmm(value):
    return value.strftime("%H:%M") if value else None


def _time_to_minutes(value):
    return value.hour * 60 + value.minute


def _minutes_to_time(value):
    return dt_time(hour=value // 60, minute=value % 60)


def _add_minutes(value, minutes):
    total = _time_to_minutes(value) + minutes
    if total < 0 or total > 24 * 60:
        return None
    if total == 24 * 60:
        return dt_time(hour=23, minute=59)
    return _minutes_to_time(total)


def _is_intern(user) -> bool:
    return bool(user and user.role and user.role.name == Role.Name.INTERN)


def _is_admin_like(user) -> bool:
    return bool(
        user
        and user.role
        and user.role.name in {Role.Name.ADMIN, Role.Name.SUPER_ADMIN, Role.Name.DEPARTMENT_HEAD}
    )


def _can_book_meeting_rooms(user) -> bool:
    return bool(user and user.role and user.role.name not in {Role.Name.EMPLOYEE, Role.Name.INTERN})


def _meeting_room_purpose_options():
    return [{"value": value, "label": label} for value, label in MeetingRoomBooking.Purpose.choices]


def _meeting_room_event_key(booking_id: int) -> str:
    return f"meeting-room-booking:{booking_id}"


def _meeting_notification_message(*, actor_name, room_name, start_time, end_time, purpose_label):
    return (
        f'{actor_name} добавил вас на переговоры "{purpose_label}" '
        f'в переговорную "{room_name}" с {start_time} до {end_time}.'
    )


def _serialize_person(user):
    return {
        "id": user.id,
        "name": user.get_full_name() or user.username,
    }


def _role_label(role_name):
    labels = {
        Role.Name.SUPER_ADMIN: "Суперадмин",
        Role.Name.ADMIN: "Админ",
        Role.Name.DEPARTMENT_HEAD: "Руководитель отдела",
        Role.Name.TEAMLEAD: "Тимлид",
        Role.Name.EMPLOYEE: "Сотрудник",
        Role.Name.INTERN: "Стажер",
    }
    return labels.get(role_name, role_name or "")


def _serialize_user_option(user):
    return {
        "id": user.id,
        "name": user.get_full_name() or user.username,
        "role": user.role.name if user.role_id else None,
        "role_label": _role_label(user.role.name) if user.role_id else "",
    }


def _serialize_booking(booking, *, current_user_id):
    return {
        "id": booking.id,
        "date": booking.date.isoformat(),
        "start_time": _format_hhmm(booking.start_time),
        "end_time": _format_hhmm(booking.end_time),
        "booked_by_me": booking.user_id == current_user_id,
        "booked_by": _serialize_person(booking.user),
        "desk": {
            "id": booking.desk_id,
            "code": booking.desk.code,
            "side": booking.desk.side,
            "row": booking.desk.row,
        },
    }


def _serialize_room_booking(booking, *, current_user_id):
    return {
        "id": booking.id,
        "date": booking.date.isoformat(),
        "start_time": _format_hhmm(booking.start_time),
        "end_time": _format_hhmm(booking.end_time),
        "purpose": booking.purpose,
        "purpose_label": booking.get_purpose_display(),
        "booked_by_me": booking.user_id == current_user_id,
        "booked_by": _serialize_person(booking.user),
        "participants": [_serialize_user_option(user) for user in booking.participants.all()],
        "room": {
            "id": booking.room_id,
            "name": booking.room.name,
        },
    }


def _build_booking_context(user, target_date: date):
    shift = resolve_user_shift_for_date(user, target_date)
    mode = shift.get("mode") or ""
    start_time = shift.get("start_time")
    end_time = shift.get("end_time")

    if mode == "office" and start_time and end_time:
        return {
            "shift": shift,
            "allowed": True,
            "reason": None,
            "message": "",
        }

    if mode == "day_off":
        return {
            "shift": shift,
            "allowed": False,
            "reason": "day_off",
            "message": "Cannot book on a non-working day.",
        }

    if mode == "online":
        return {
            "shift": shift,
            "allowed": False,
            "reason": "online_day",
            "message": "Desk booking is available only for office shifts.",
        }

    return {
        "shift": shift,
        "allowed": False,
        "reason": "no_schedule",
        "message": "Desk booking requires an approved office schedule for this day.",
    }


def _resolve_requested_interval(user, target_date: date, start_time=None, end_time=None):
    context = _build_booking_context(user, target_date)
    shift = context["shift"]
    interval_start = start_time
    interval_end = end_time

    if not interval_start and not interval_end and context["allowed"]:
        interval_start = shift.get("start_time") or DEFAULT_BOOKING_START
        interval_end = shift.get("end_time") or DEFAULT_BOOKING_END

    return context, interval_start, interval_end


def _validate_interval(*, shift, start_time, end_time):
    if not start_time or not end_time:
        return "Invalid booking interval."
    if end_time <= start_time:
        return "End time must be after start time."

    shift_start = shift.get("start_time")
    shift_end = shift.get("end_time")
    if shift_start and start_time < shift_start:
        return f"Booking cannot start earlier than your shift: {_format_hhmm(shift_start)}."
    if shift_end and end_time > shift_end:
        return f"Booking cannot end later than your shift: {_format_hhmm(shift_end)}."
    return None


def _validate_room_interval(start_time, end_time):
    if not start_time or not end_time:
        return "Invalid booking interval."
    if end_time <= start_time:
        return "End time must be after start time."
    if start_time < ROOM_DAY_START:
        return f"Meeting room booking cannot start earlier than {_format_hhmm(ROOM_DAY_START)}."
    if end_time > ROOM_DAY_END:
        return f"Meeting room booking cannot end later than {_format_hhmm(ROOM_DAY_END)}."
    return None


def _compute_room_free_slots(bookings):
    free_slots = []
    cursor = _time_to_minutes(ROOM_DAY_START)
    day_end = _time_to_minutes(ROOM_DAY_END)

    for booking in bookings:
        start_minutes = _time_to_minutes(booking.start_time)
        end_minutes = _time_to_minutes(booking.end_time)
        if start_minutes > cursor:
            free_slots.append((cursor, start_minutes))
        cursor = max(cursor, end_minutes)

    if cursor < day_end:
        free_slots.append((cursor, day_end))

    return [
        {
            "start_time": _format_hhmm(_minutes_to_time(start)),
            "end_time": _format_hhmm(_minutes_to_time(end)),
            "duration_minutes": end - start,
        }
        for start, end in free_slots
        if end > start
    ]


def _meeting_room_participants_queryset(user):
    if not _can_book_meeting_rooms(user) or not user.role_id:
        return User.objects.none()

    qs = User.objects.filter(is_active=True).exclude(id=user.id).select_related("role")

    if user.role.name == Role.Name.SUPER_ADMIN:
        return qs.filter(role__level__lt=user.role.level).order_by("first_name", "last_name", "username")
    if user.role.name == Role.Name.ADMIN:
        return qs.filter(role__level__lt=user.role.level).order_by("first_name", "last_name", "username")
    if user.role.name == Role.Name.DEPARTMENT_HEAD:
        return qs.filter(
            role__level__lt=user.role.level,
            department_id=user.department_id,
        ).order_by("first_name", "last_name", "username")
    if user.role.name == Role.Name.TEAMLEAD:
        return qs.filter(
            role__level__lt=user.role.level,
            manager_id=user.id,
        ).order_by("first_name", "last_name", "username")
    return User.objects.none()


class DeskListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        desks = Desk.objects.filter(is_active=True).order_by("row", "side")
        return Response(DeskSerializer(desks, many=True).data)


class DeskAvailabilityAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_date = _parse_iso_date(request.query_params.get("date"), default_today=True)
        if not target_date:
            return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        raw_start_time = request.query_params.get("start_time")
        raw_end_time = request.query_params.get("end_time")
        if bool(raw_start_time) != bool(raw_end_time):
            return Response(
                {"detail": "start_time and end_time must be provided together."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_time = _parse_iso_time(raw_start_time)
        end_time = _parse_iso_time(raw_end_time)
        if raw_start_time and not start_time:
            return Response({"detail": "Invalid start_time format. Use HH:MM."}, status=status.HTTP_400_BAD_REQUEST)
        if raw_end_time and not end_time:
            return Response({"detail": "Invalid end_time format. Use HH:MM."}, status=status.HTTP_400_BAD_REQUEST)

        context, requested_start, requested_end = _resolve_requested_interval(request.user, target_date, start_time, end_time)
        shift = context["shift"]
        if requested_start and requested_end:
            interval_error = _validate_interval(shift=shift, start_time=requested_start, end_time=requested_end) if context["allowed"] else (
                "End time must be after start time." if requested_end <= requested_start else None
            )
        else:
            interval_error = None

        if interval_error:
            return Response({"detail": interval_error}, status=status.HTTP_400_BAD_REQUEST)

        desks = list(Desk.objects.filter(is_active=True).order_by("row", "side"))
        bookings = list(
            DeskBooking.objects.filter(date=target_date, desk__in=desks)
            .select_related("desk", "user")
            .order_by("start_time", "end_time", "id")
        )
        bookings_by_desk = defaultdict(list)
        my_booking = None
        for booking in bookings:
            bookings_by_desk[booking.desk_id].append(booking)
            if booking.user_id == request.user.id:
                my_booking = booking

        items = []
        for desk in desks:
            desk_bookings = bookings_by_desk.get(desk.id, [])
            if requested_start and requested_end:
                conflicting_bookings = [
                    booking
                    for booking in desk_bookings
                    if booking.start_time < requested_end and booking.end_time > requested_start
                ]
            else:
                conflicting_bookings = desk_bookings
            my_desk_booking = next((booking for booking in desk_bookings if booking.user_id == request.user.id), None)
            primary_booking = conflicting_bookings[0] if conflicting_bookings else (desk_bookings[0] if desk_bookings else None)
            items.append(
                {
                    "id": desk.id,
                    "code": desk.code,
                    "side": desk.side,
                    "row": desk.row,
                    "is_available": not conflicting_bookings,
                    "booking_id": my_desk_booking.id if my_desk_booking else None,
                    "booked_by_me": bool(my_desk_booking),
                    "booked_by": _serialize_person(primary_booking.user) if primary_booking else None,
                    "bookings": [_serialize_booking(booking, current_user_id=request.user.id) for booking in desk_bookings],
                    "conflicting_bookings": [
                        _serialize_booking(booking, current_user_id=request.user.id)
                        for booking in conflicting_bookings
                    ],
                }
            )

        total = len(items)
        occupied = sum(1 for item in items if not item["is_available"])
        available = total - occupied

        return Response(
            {
                "date": target_date.isoformat(),
                "is_working_day": context["allowed"],
                "booking_allowed": context["allowed"],
                "booking_reason": context["reason"],
                "booking_message": context["message"],
                "requested_interval": {
                    "start_time": _format_hhmm(requested_start) if requested_start else None,
                    "end_time": _format_hhmm(requested_end) if requested_end else None,
                } if requested_start and requested_end else None,
                "user_shift": {
                    "mode": shift.get("mode"),
                    "start_time": _format_hhmm(shift.get("start_time")),
                    "end_time": _format_hhmm(shift.get("end_time")),
                    "source": shift.get("source"),
                },
                "total": total,
                "available": available,
                "occupied": occupied,
                "my_booking": _serialize_booking(my_booking, current_user_id=request.user.id) if my_booking else None,
                "desks": items,
            }
        )


class DeskBookingCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if _is_intern(request.user):
            return Response({"detail": "Interns cannot book desks."}, status=status.HTTP_403_FORBIDDEN)

        serializer = DeskBookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_date = serializer.validated_data["date"]
        desk_id = serializer.validated_data["desk_id"]
        start_time = serializer.validated_data.get("start_time")
        end_time = serializer.validated_data.get("end_time")

        if target_date < timezone.localdate():
            return Response({"detail": "Cannot book in the past."}, status=status.HTTP_400_BAD_REQUEST)

        context, requested_start, requested_end = _resolve_requested_interval(request.user, target_date, start_time, end_time)
        shift = context["shift"]
        if not context["allowed"]:
            return Response(
                {"detail": context["message"], "reason": context["reason"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        interval_error = _validate_interval(shift=shift, start_time=requested_start, end_time=requested_end)
        if interval_error:
            return Response({"detail": interval_error}, status=status.HTTP_400_BAD_REQUEST)

        desk = Desk.objects.filter(id=desk_id, is_active=True).first()
        if not desk:
            return Response({"detail": "Desk not found."}, status=status.HTTP_404_NOT_FOUND)

        if DeskBooking.objects.filter(user=request.user, date=target_date).exists():
            return Response({"detail": "You already have a booking for this date."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            overlapping_booking = (
                DeskBooking.objects.select_for_update()
                .select_related("user", "desk")
                .filter(
                    desk=desk,
                    date=target_date,
                    start_time__lt=requested_end,
                    end_time__gt=requested_start,
                )
                .order_by("start_time", "end_time", "id")
                .first()
            )
            if overlapping_booking:
                return Response(
                    {
                        "detail": "Desk is already booked for this time range.",
                        "conflict": _serialize_booking(overlapping_booking, current_user_id=request.user.id),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            booking = DeskBooking.objects.create(
                desk=desk,
                user=request.user,
                date=target_date,
                start_time=requested_start,
                end_time=requested_end,
            )

        return Response(
            {
                "id": booking.id,
                "desk_id": booking.desk_id,
                "date": booking.date.isoformat(),
                "start_time": _format_hhmm(booking.start_time),
                "end_time": _format_hhmm(booking.end_time),
            },
            status=status.HTTP_201_CREATED,
        )


class DeskBookingDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, booking_id: int):
        booking = DeskBooking.objects.select_related("user").filter(id=booking_id).first()
        if not booking:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        if booking.user_id != request.user.id and not _is_admin_like(request.user):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        booking.delete()
        return Response({"status": "deleted"})


class MeetingRoomListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rooms = MeetingRoom.objects.filter(is_active=True).order_by("name")
        return Response(MeetingRoomSerializer(rooms, many=True).data)


class MeetingRoomBookingOptionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        booking_allowed = _can_book_meeting_rooms(request.user)
        participants = _meeting_room_participants_queryset(request.user) if booking_allowed else User.objects.none()
        return Response(
            {
                "booking_allowed": booking_allowed,
                "booking_reason": None if booking_allowed else "role_not_allowed",
                "booking_message": "" if booking_allowed else "Meeting rooms can be booked only by managers and admins.",
                "default_duration_minutes": DEFAULT_ROOM_BOOKING_DURATION_MINUTES,
                "day_bounds": {
                    "start_time": _format_hhmm(ROOM_DAY_START),
                    "end_time": _format_hhmm(ROOM_DAY_END),
                },
                "purposes": _meeting_room_purpose_options(),
                "participants": [_serialize_user_option(user) for user in participants],
            }
        )


class MeetingRoomAvailabilityAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_date = _parse_iso_date(request.query_params.get("date"), default_today=True)
        if not target_date:
            return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        raw_start_time = request.query_params.get("start_time")
        raw_end_time = request.query_params.get("end_time")
        if bool(raw_start_time) != bool(raw_end_time):
            return Response(
                {"detail": "start_time and end_time must be provided together."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_time = _parse_iso_time(raw_start_time) if raw_start_time else None
        end_time = _parse_iso_time(raw_end_time) if raw_end_time else None
        if raw_start_time and not start_time:
            return Response({"detail": "Invalid start_time format. Use HH:MM."}, status=status.HTTP_400_BAD_REQUEST)
        if raw_end_time and not end_time:
            return Response({"detail": "Invalid end_time format. Use HH:MM."}, status=status.HTTP_400_BAD_REQUEST)
        if start_time and end_time:
            interval_error = _validate_room_interval(start_time, end_time)
            if interval_error:
                return Response({"detail": interval_error}, status=status.HTTP_400_BAD_REQUEST)

        rooms = list(MeetingRoom.objects.filter(is_active=True).order_by("name"))
        bookings = list(
            MeetingRoomBooking.objects.filter(date=target_date, room__in=rooms)
            .select_related("room", "user")
            .prefetch_related("participants")
            .order_by("start_time", "end_time", "id")
        )
        bookings_by_room = defaultdict(list)
        my_bookings = []
        for booking in bookings:
            bookings_by_room[booking.room_id].append(booking)
            if booking.user_id == request.user.id:
                my_bookings.append(booking)

        items = []
        for room in rooms:
            room_bookings = bookings_by_room.get(room.id, [])
            conflicting_bookings = []
            if start_time and end_time:
                conflicting_bookings = [
                    booking
                    for booking in room_bookings
                    if booking.start_time < end_time and booking.end_time > start_time
                ]
            my_room_bookings = [booking for booking in room_bookings if booking.user_id == request.user.id]
            free_slots = _compute_room_free_slots(room_bookings)
            items.append(
                {
                    "id": room.id,
                    "name": room.name,
                    "is_available": not conflicting_bookings if start_time and end_time else bool(free_slots),
                    "booked_by_me": bool(my_room_bookings),
                    "bookings": [_serialize_room_booking(booking, current_user_id=request.user.id) for booking in room_bookings],
                    "conflicting_bookings": [
                        _serialize_room_booking(booking, current_user_id=request.user.id)
                        for booking in conflicting_bookings
                    ],
                    "my_bookings": [
                        _serialize_room_booking(booking, current_user_id=request.user.id)
                        for booking in my_room_bookings
                    ],
                    "free_slots": free_slots,
                }
            )

        total = len(items)
        occupied = sum(1 for item in items if not item["is_available"])
        available = total - occupied
        booking_allowed = _can_book_meeting_rooms(request.user)

        return Response(
            {
                "date": target_date.isoformat(),
                "booking_allowed": booking_allowed,
                "booking_reason": None if booking_allowed else "role_not_allowed",
                "booking_message": "" if booking_allowed else "Meeting rooms can be booked only by managers and admins.",
                "requested_interval": {
                    "start_time": _format_hhmm(start_time),
                    "end_time": _format_hhmm(end_time),
                } if start_time and end_time else None,
                "day_bounds": {
                    "start_time": _format_hhmm(ROOM_DAY_START),
                    "end_time": _format_hhmm(ROOM_DAY_END),
                },
                "default_duration_minutes": DEFAULT_ROOM_BOOKING_DURATION_MINUTES,
                "total": total,
                "available": available,
                "occupied": occupied,
                "my_bookings": [_serialize_room_booking(booking, current_user_id=request.user.id) for booking in my_bookings],
                "rooms": items,
            }
        )


class MeetingRoomBookingCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _can_book_meeting_rooms(request.user):
            return Response(
                {
                    "detail": "Meeting rooms can be booked only by managers and admins.",
                    "reason": "role_not_allowed",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MeetingRoomBookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_date = serializer.validated_data["date"]
        room_id = serializer.validated_data["room_id"]
        start_time = serializer.validated_data["start_time"]
        end_time = serializer.validated_data.get("end_time") or _add_minutes(
            start_time,
            DEFAULT_ROOM_BOOKING_DURATION_MINUTES,
        )
        purpose = serializer.validated_data["purpose"]
        participant_ids = list(dict.fromkeys(serializer.validated_data.get("participant_ids") or []))

        if target_date < timezone.localdate():
            return Response({"detail": "Cannot book in the past."}, status=status.HTTP_400_BAD_REQUEST)

        interval_error = _validate_room_interval(start_time, end_time)
        if interval_error:
            return Response({"detail": interval_error}, status=status.HTTP_400_BAD_REQUEST)

        room = MeetingRoom.objects.filter(id=room_id, is_active=True).first()
        if not room:
            return Response({"detail": "Meeting room not found."}, status=status.HTTP_404_NOT_FOUND)

        allowed_participants_qs = _meeting_room_participants_queryset(request.user)
        allowed_participants = list(allowed_participants_qs.filter(id__in=participant_ids))
        if len(allowed_participants) != len(participant_ids):
            return Response(
                {"detail": "You can select only subordinates and lower-ranked employees for this meeting."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            overlapping_booking = (
                MeetingRoomBooking.objects.select_for_update()
                .select_related("user", "room")
                .filter(
                    room=room,
                    date=target_date,
                    start_time__lt=end_time,
                    end_time__gt=start_time,
                )
                .order_by("start_time", "end_time", "id")
                .first()
            )
            if overlapping_booking:
                return Response(
                    {
                        "detail": "Meeting room is already booked for this time range.",
                        "conflict": _serialize_room_booking(overlapping_booking, current_user_id=request.user.id),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            booking = MeetingRoomBooking.objects.create(
                room=room,
                user=request.user,
                date=target_date,
                start_time=start_time,
                end_time=end_time,
                purpose=purpose,
            )
            if allowed_participants:
                booking.participants.set(allowed_participants)

            meeting_end = timezone.make_aware(
                datetime.combine(target_date, end_time),
                timezone.get_current_timezone(),
            )
            actor_name = request.user.get_full_name() or request.user.username
            notifications = [
                Notification(
                    user=participant,
                    title=f"Переговорная: {room.name}",
                    message=_meeting_notification_message(
                        actor_name=actor_name,
                        room_name=room.name,
                        start_time=_format_hhmm(start_time),
                        end_time=_format_hhmm(end_time),
                        purpose_label=booking.get_purpose_display(),
                    ),
                    type=Notification.Type.INFO,
                    event_key=_meeting_room_event_key(booking.id),
                    is_pinned=True,
                    expires_at=meeting_end,
                )
                for participant in allowed_participants
            ]
            if notifications:
                Notification.objects.bulk_create(notifications)

        booking = (
            MeetingRoomBooking.objects.select_related("room", "user")
            .prefetch_related("participants")
            .get(id=booking.id)
        )
        return Response(_serialize_room_booking(booking, current_user_id=request.user.id), status=status.HTTP_201_CREATED)


class MeetingRoomBookingDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, booking_id: int):
        booking = MeetingRoomBooking.objects.select_related("user").filter(id=booking_id).first()
        if not booking:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        if booking.user_id != request.user.id and not _is_admin_like(request.user):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        Notification.objects.filter(event_key=_meeting_room_event_key(booking.id)).delete()
        booking.delete()
        return Response({"status": "deleted"})
