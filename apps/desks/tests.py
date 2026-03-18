from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Role, User
from common.models import Notification
from work_schedule.models import UserWorkSchedule, WeeklyWorkPlan, WorkSchedule

from .models import Desk, DeskBooking, MeetingRoom, MeetingRoomBooking


class DeskBookingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.user = User.objects.create_user(
            username="desk_user",
            password="StrongPass123!",
            role=self.employee_role,
            first_name="Desk",
            last_name="User",
        )
        self.other_user = User.objects.create_user(
            username="desk_other",
            password="StrongPass123!",
            role=self.employee_role,
            first_name="Other",
            last_name="User",
        )
        self.schedule = WorkSchedule.objects.create(
            name="Desk office",
            work_days=[0, 1, 2, 3, 4, 5, 6],
            start_time="09:00",
            end_time="18:00",
            is_active=True,
        )
        UserWorkSchedule.objects.create(user=self.user, schedule=self.schedule, approved=True)
        UserWorkSchedule.objects.create(user=self.other_user, schedule=self.schedule, approved=True)
        self.desk = Desk.objects.get(code="L1")
        self.target_date = timezone.localdate() + timedelta(days=1)

    def test_availability_returns_booking_intervals_and_booker(self):
        DeskBooking.objects.create(
            desk=self.desk,
            user=self.other_user,
            date=self.target_date,
            start_time="09:00",
            end_time="12:00",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            "/api/v1/desks/availability/",
            {
                "date": self.target_date.isoformat(),
                "start_time": "09:00",
                "end_time": "18:00",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["requested_interval"]["start_time"], "09:00")
        self.assertEqual(response.data["requested_interval"]["end_time"], "18:00")
        desk_payload = next(item for item in response.data["desks"] if item["id"] == self.desk.id)
        self.assertFalse(desk_payload["is_available"])
        self.assertEqual(len(desk_payload["bookings"]), 1)
        self.assertEqual(desk_payload["bookings"][0]["start_time"], "09:00")
        self.assertEqual(desk_payload["bookings"][0]["end_time"], "12:00")
        self.assertEqual(desk_payload["bookings"][0]["booked_by"]["name"], "Other User")

    def test_can_book_same_desk_after_previous_booking_ends(self):
        DeskBooking.objects.create(
            desk=self.desk,
            user=self.other_user,
            date=self.target_date,
            start_time="09:00",
            end_time="12:00",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/desks/bookings/",
            {
                "desk_id": self.desk.id,
                "date": self.target_date.isoformat(),
                "start_time": "12:00",
                "end_time": "18:00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["start_time"], "12:00")
        self.assertEqual(response.data["end_time"], "18:00")
        self.assertEqual(DeskBooking.objects.filter(desk=self.desk, date=self.target_date).count(), 2)

    def test_cannot_book_overlapping_interval(self):
        DeskBooking.objects.create(
            desk=self.desk,
            user=self.other_user,
            date=self.target_date,
            start_time="09:00",
            end_time="12:00",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/desks/bookings/",
            {
                "desk_id": self.desk.id,
                "date": self.target_date.isoformat(),
                "start_time": "11:00",
                "end_time": "13:00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["detail"], "Desk is already booked for this time range.")
        if "conflict" in response.data:
            self.assertEqual(response.data["conflict"]["start_time"], "09:00")
            self.assertEqual(response.data["conflict"]["end_time"], "12:00")

    def test_cannot_book_without_schedule(self):
        UserWorkSchedule.objects.filter(user=self.user).delete()

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/desks/bookings/",
            {
                "desk_id": self.desk.id,
                "date": self.target_date.isoformat(),
                "start_time": "09:00",
                "end_time": "18:00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Desk booking requires an approved office schedule for this day.")

    def test_cannot_book_on_online_day(self):
        week_start = self.target_date - timedelta(days=self.target_date.weekday())
        WeeklyWorkPlan.objects.create(
            user=self.user,
            week_start=week_start,
            status=WeeklyWorkPlan.Status.APPROVED,
            days=[
                {
                    "date": (week_start + timedelta(days=i)).isoformat(),
                    "start_time": "14:00" if i == self.target_date.weekday() else None,
                    "end_time": "21:00" if i == self.target_date.weekday() else None,
                    "mode": "online" if i == self.target_date.weekday() else "day_off",
                    "comment": "",
                    "breaks": [],
                    "lunch_start": None,
                    "lunch_end": None,
                }
                for i in range(7)
            ],
            office_hours=0,
            online_hours=7,
            online_reason="Remote work",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/desks/bookings/",
            {
                "desk_id": self.desk.id,
                "date": self.target_date.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Desk booking is available only for office shifts.")

    def test_uses_office_shift_time_when_time_not_passed(self):
        week_start = self.target_date - timedelta(days=self.target_date.weekday())
        WeeklyWorkPlan.objects.create(
            user=self.user,
            week_start=week_start,
            status=WeeklyWorkPlan.Status.APPROVED,
            days=[
                {
                    "date": (week_start + timedelta(days=i)).isoformat(),
                    "start_time": "14:00" if i == self.target_date.weekday() else None,
                    "end_time": "21:00" if i == self.target_date.weekday() else None,
                    "mode": "office" if i == self.target_date.weekday() else "day_off",
                    "comment": "",
                    "breaks": [],
                    "lunch_start": None,
                    "lunch_end": None,
                }
                for i in range(7)
            ],
            office_hours=7,
            online_hours=0,
            online_reason="Office shift for this week",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/desks/bookings/",
            {
                "desk_id": self.desk.id,
                "date": self.target_date.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["start_time"], "14:00")
        self.assertEqual(response.data["end_time"], "21:00")


class MeetingRoomBookingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.teamlead_role, _ = Role.objects.get_or_create(
            name=Role.Name.TEAMLEAD,
            defaults={"level": Role.Level.TEAMLEAD},
        )
        self.admin_role, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )
        self.employee = User.objects.create_user(
            username="room_employee",
            password="StrongPass123!",
            role=self.employee_role,
            first_name="Room",
            last_name="Employee",
        )
        self.teamlead = User.objects.create_user(
            username="room_teamlead",
            password="StrongPass123!",
            role=self.teamlead_role,
            first_name="Room",
            last_name="Teamlead",
        )
        self.subordinate = User.objects.create_user(
            username="room_employee_subordinate",
            password="StrongPass123!",
            role=self.employee_role,
            first_name="Direct",
            last_name="Report",
            manager=self.teamlead,
        )
        self.outsider = User.objects.create_user(
            username="room_employee_outsider",
            password="StrongPass123!",
            role=self.employee_role,
            first_name="Outside",
            last_name="Employee",
        )
        self.admin = User.objects.create_user(
            username="room_admin",
            password="StrongPass123!",
            role=self.admin_role,
            first_name="Room",
            last_name="Admin",
        )
        self.other_admin = User.objects.create_user(
            username="room_admin_2",
            password="StrongPass123!",
            role=self.admin_role,
            first_name="Other",
            last_name="Admin",
        )
        self.room, _ = MeetingRoom.objects.get_or_create(name="Пещера вождя")
        self.target_date = timezone.localdate() + timedelta(days=1)

    def test_employee_cannot_book_meeting_room(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.post(
            "/api/v1/desks/rooms/bookings/",
            {
                "room_id": self.room.id,
                "date": self.target_date.isoformat(),
                "start_time": "10:00",
                "end_time": "11:00",
                "purpose": "discussion",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Meeting rooms can be booked only by managers and admins.")

    def test_admin_can_book_meeting_room(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/v1/desks/rooms/bookings/",
            {
                "room_id": self.room.id,
                "date": self.target_date.isoformat(),
                "start_time": "10:00",
                "end_time": "11:00",
                "purpose": "discussion",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["start_time"], "10:00")
        self.assertEqual(response.data["end_time"], "11:00")

    def test_meeting_room_conflict_is_blocked(self):
        MeetingRoomBooking.objects.create(
            room=self.room,
            user=self.other_admin,
            date=self.target_date,
            start_time="10:00",
            end_time="11:00",
            purpose="discussion",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/v1/desks/rooms/bookings/",
            {
                "room_id": self.room.id,
                "date": self.target_date.isoformat(),
                "start_time": "10:30",
                "end_time": "11:30",
                "purpose": "discussion",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["detail"], "Meeting room is already booked for this time range.")

    def test_meeting_room_availability_returns_bookings(self):
        MeetingRoomBooking.objects.create(
            room=self.room,
            user=self.other_admin,
            date=self.target_date,
            start_time="12:00",
            end_time="13:00",
            purpose="discussion",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            "/api/v1/desks/rooms/availability/",
            {
                "date": self.target_date.isoformat(),
                "start_time": "12:00",
                "end_time": "13:00",
            },
        )

        self.assertEqual(response.status_code, 200)
        room_payload = next(item for item in response.data["rooms"] if item["id"] == self.room.id)
        self.assertFalse(room_payload["is_available"])
        self.assertEqual(room_payload["bookings"][0]["booked_by"]["name"], "Other Admin")

    def test_room_availability_returns_free_slots_for_fragmented_bookings(self):
        MeetingRoomBooking.objects.create(
            room=self.room,
            user=self.other_admin,
            date=self.target_date,
            start_time="14:00",
            end_time="14:30",
            purpose="discussion",
        )
        MeetingRoomBooking.objects.create(
            room=self.room,
            user=self.other_admin,
            date=self.target_date,
            start_time="16:00",
            end_time="16:40",
            purpose="planning",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            "/api/v1/desks/rooms/availability/",
            {"date": self.target_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        room_payload = next(item for item in response.data["rooms"] if item["id"] == self.room.id)
        free_slots = room_payload["free_slots"]
        self.assertTrue(any(slot["start_time"] == "14:30" and slot["end_time"] == "16:00" for slot in free_slots))
        self.assertTrue(any(slot["start_time"] == "16:40" and slot["end_time"] == "21:00" for slot in free_slots))

    def test_teamlead_can_book_with_default_duration_and_notify_participant(self):
        self.client.force_authenticate(user=self.teamlead)
        response = self.client.post(
            "/api/v1/desks/rooms/bookings/",
            {
                "room_id": self.room.id,
                "date": self.target_date.isoformat(),
                "start_time": "15:00",
                "purpose": "one_on_one",
                "participant_ids": [self.subordinate.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["start_time"], "15:00")
        self.assertEqual(response.data["end_time"], "15:30")
        booking = MeetingRoomBooking.objects.get(id=response.data["id"])
        self.assertEqual(booking.participants.count(), 1)
        self.assertEqual(booking.participants.first().id, self.subordinate.id)

        notification = Notification.objects.get(user=self.subordinate, event_key=f"meeting-room-booking:{booking.id}")
        self.assertTrue(notification.is_pinned)
        self.assertIsNotNone(notification.expires_at)
        self.assertIn("Пещера", notification.title)

    def test_teamlead_cannot_invite_employee_outside_team(self):
        self.client.force_authenticate(user=self.teamlead)
        response = self.client.post(
            "/api/v1/desks/rooms/bookings/",
            {
                "room_id": self.room.id,
                "date": self.target_date.isoformat(),
                "start_time": "15:00",
                "end_time": "15:30",
                "purpose": "discussion",
                "participant_ids": [self.outsider.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "You can select only subordinates and lower-ranked employees for this meeting.",
        )

    def test_room_options_return_allowed_participants(self):
        self.client.force_authenticate(user=self.teamlead)
        response = self.client.get("/api/v1/desks/rooms/options/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["default_duration_minutes"], 30)
        participant_ids = [item["id"] for item in response.data["participants"]]
        self.assertIn(self.subordinate.id, participant_ids)
        self.assertNotIn(self.outsider.id, participant_ids)
