from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.core.management import call_command
from rest_framework.test import APIClient

from accounts.models import Role, User
from work_schedule.models import ProductionCalendar, WeeklyWorkPlan

from .models import AttendanceMark, AttendanceSession, OfficeNetwork, WorkCalendarDay


class AttendanceApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.intern_role, _ = Role.objects.get_or_create(
            name=Role.Name.INTERN,
            defaults={"level": Role.Level.INTERN},
        )
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

        self.teamlead = User.objects.create_user(
            username="teamlead",
            password="StrongPass123!",
            role=self.teamlead_role,
        )
        self.subordinate = User.objects.create_user(
            username="subordinate",
            password="StrongPass123!",
            role=self.employee_role,
            manager=self.teamlead,
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="StrongPass123!",
            role=self.employee_role,
        )
        self.admin = User.objects.create_user(
            username="admin_att",
            password="StrongPass123!",
            role=self.admin_role,
        )
        self.super_admin_role, _ = Role.objects.get_or_create(
            name=Role.Name.SUPER_ADMIN,
            defaults={"level": Role.Level.SUPER_ADMIN},
        )
        self.super_admin = User.objects.create_user(
            username="super_admin_att",
            password="StrongPass123!",
            role=self.super_admin_role,
        )

    def _create_approved_plan_for_today(self, *, mode_for_today: str):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        days = []
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            if day_date.weekday() < 5:
                mode = "office"
                if day_date == today:
                    mode = mode_for_today
                days.append(
                    {
                        "date": day_date.isoformat(),
                        "mode": mode,
                        "start_time": "10:00",
                        "end_time": "18:00",
                        "comment": "",
                    }
                )
            else:
                if day_date == today:
                    days.append(
                        {
                            "date": day_date.isoformat(),
                            "mode": mode_for_today,
                            "start_time": "11:00",
                            "end_time": "17:00",
                            "comment": "",
                        }
                    )
                else:
                    days.append(
                        {
                            "date": day_date.isoformat(),
                            "mode": "day_off",
                            "comment": "",
                        }
                    )

        WeeklyWorkPlan.objects.update_or_create(
            user=self.subordinate,
            week_start=week_start,
            defaults={
                "days": days,
                "status": WeeklyWorkPlan.Status.APPROVED,
                "online_reason": "",
                "employee_comment": "",
            },
        )

    @patch("apps.attendance.views.AttendanceAuditService.log_mark_created")
    def test_post_own_mark_creates(self, log_mark_created):
        self.client.force_authenticate(user=self.subordinate)
        response = self.client.post(
            "/api/v1/attendance/mark/",
            {"date": str(date.today()), "status": "present", "comment": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            AttendanceMark.objects.filter(user=self.subordinate, date=date.today()).exists()
        )
        log_mark_created.assert_called_once()

    @patch("apps.attendance.views.AttendanceAuditService.log_mark_updated")
    def test_post_same_date_updates_existing(self, log_mark_updated):
        self.client.force_authenticate(user=self.subordinate)
        AttendanceMark.objects.create(
            user=self.subordinate,
            date=date.today(),
            status=AttendanceMark.Status.PRESENT,
            comment="old",
            created_by=self.subordinate,
        )
        response = self.client.post(
            "/api/v1/attendance/mark/",
            {"date": str(date.today()), "status": "remote", "comment": "new"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        mark = AttendanceMark.objects.get(user=self.subordinate, date=date.today())
        self.assertEqual(mark.status, AttendanceMark.Status.REMOTE)
        self.assertEqual(mark.comment, "new")
        log_mark_updated.assert_called_once()

    def test_teamlead_can_mark_subordinate(self):
        self.client.force_authenticate(user=self.teamlead)
        response = self.client.post(
            "/api/v1/attendance/mark/",
            {
                "user_id": self.subordinate.id,
                "date": str(date.today()),
                "status": "present",
                "comment": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            AttendanceMark.objects.filter(user=self.subordinate, date=date.today()).exists()
        )

    @patch("apps.attendance.views.AttendanceAuditService.log_mark_change_denied")
    def test_teamlead_cannot_mark_non_subordinate(self, log_denied):
        self.client.force_authenticate(user=self.teamlead)
        response = self.client.post(
            "/api/v1/attendance/mark/",
            {
                "user_id": self.other_user.id,
                "date": str(date.today()),
                "status": "present",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)
        log_denied.assert_called_once()

    def test_future_date_denied(self):
        self.client.force_authenticate(user=self.subordinate)
        response = self.client.post(
            "/api/v1/attendance/mark/",
            {"date": str(date.today() + timedelta(days=1)), "status": "present"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_get_my_month_marks(self):
        self.client.force_authenticate(user=self.subordinate)
        AttendanceMark.objects.create(
            user=self.subordinate,
            date=date(2026, 2, 1),
            status=AttendanceMark.Status.PRESENT,
            created_by=self.subordinate,
        )
        AttendanceMark.objects.create(
            user=self.other_user,
            date=date(2026, 2, 1),
            status=AttendanceMark.Status.PRESENT,
            created_by=self.other_user,
        )

        response = self.client.get("/api/v1/attendance/my/?year=2026&month=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["user"], self.subordinate.id)

    def test_get_team_marks_for_teamlead(self):
        self.client.force_authenticate(user=self.teamlead)
        AttendanceMark.objects.create(
            user=self.subordinate,
            date=date(2026, 2, 2),
            status=AttendanceMark.Status.REMOTE,
            created_by=self.teamlead,
        )
        AttendanceMark.objects.create(
            user=self.other_user,
            date=date(2026, 2, 2),
            status=AttendanceMark.Status.REMOTE,
            created_by=self.other_user,
        )
        response = self.client.get("/api/v1/attendance/team/?year=2026&month=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["user"], self.subordinate.id)

    def test_get_team_marks_denied_for_regular_user_without_team(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get("/api/v1/attendance/team/?year=2026&month=2")
        self.assertEqual(response.status_code, 403)

    def test_calendar_uses_work_calendar_day_and_fallbacks(self):
        self.client.force_authenticate(user=self.subordinate)
        WorkCalendarDay.objects.create(
            date=date(2026, 2, 1),
            is_working_day=False,
            is_holiday=True,
            note="Holiday",
        )
        ProductionCalendar.objects.create(
            date=date(2026, 2, 2),
            is_working_day=False,
            is_holiday=True,
            holiday_name="Prod holiday",
        )
        response = self.client.get("/api/v1/attendance/calendar/?year=2026&month=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 28)
        by_date = {str(item["date"]): item for item in response.data}
        self.assertTrue(by_date["2026-02-01"]["is_holiday"])
        self.assertTrue(by_date["2026-02-02"]["is_holiday"])

    def test_admin_can_view_all_team_endpoint(self):
        self.client.force_authenticate(user=self.admin)
        AttendanceMark.objects.create(
            user=self.subordinate,
            date=date(2026, 2, 3),
            status=AttendanceMark.Status.PRESENT,
            created_by=self.subordinate,
        )
        AttendanceMark.objects.create(
            user=self.other_user,
            date=date(2026, 2, 3),
            status=AttendanceMark.Status.PRESENT,
            created_by=self.other_user,
        )
        response = self.client.get("/api/v1/attendance/team/?year=2026&month=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_overview_endpoint_returns_table_shape(self):
        self.client.force_authenticate(user=self.teamlead)
        AttendanceMark.objects.create(
            user=self.subordinate,
            date=date(2026, 2, 4),
            status=AttendanceMark.Status.PRESENT,
            created_by=self.teamlead,
        )
        response = self.client.get("/api/v1/attendance/?year=2026&month=2")
        self.assertEqual(response.status_code, 200)
        self.assertIn("days", response.data)
        self.assertIn("rows", response.data)
        self.assertEqual(len(response.data["rows"]), 1)

    @patch("apps.attendance.views.AttendanceAuditService.log_mark_deleted")
    def test_admin_can_delete_mark(self, log_mark_deleted):
        mark = AttendanceMark.objects.create(
            user=self.subordinate,
            date=date(2026, 2, 5),
            status=AttendanceMark.Status.PRESENT,
            created_by=self.subordinate,
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(
            "/api/v1/attendance/mark/",
            {"user_id": self.subordinate.id, "date": "2026-02-05"},
            format="json",
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(AttendanceMark.objects.filter(id=mark.id).exists())
        log_mark_deleted.assert_called_once()

    def test_work_calendar_admin_crud_requires_admin(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(
            "/api/v1/attendance/work-calendar/",
            {
                "date": "2026-02-10",
                "is_working_day": True,
                "is_holiday": False,
                "note": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/v1/attendance/work-calendar/",
            {
                "date": "2026-02-10",
                "is_working_day": True,
                "is_holiday": False,
                "note": "working day",
            },
            format="json",
        )
        self.assertIn(response.status_code, [200, 201])
        self.assertTrue(WorkCalendarDay.objects.filter(date=date(2026, 2, 10)).exists())

    def test_work_calendar_generate_command(self):
        call_command("generate_work_calendar_month", year=2026, month=3)
        self.assertEqual(
            WorkCalendarDay.objects.filter(date__year=2026, date__month=3).count(),
            31,
        )

    @patch("apps.attendance.views.AttendanceAuditService.log_office_checkin_in_office")
    def test_check_in_in_office_creates_session_and_mark(self, log_in_office):
        self._create_approved_plan_for_today(mode_for_today="office")
        OfficeNetwork.objects.create(name="HQ", cidr="192.168.10.0/24", is_active=True)
        self.client.force_authenticate(user=self.subordinate)
        response = self.client.post(
            "/api/v1/attendance/check-in/",
            {"work_mode": "office"},
            format="json",
            HTTP_X_FORWARDED_FOR="192.168.10.55",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["in_office"])
        self.assertTrue(response.data["status"] == "IN_OFFICE")
        self.assertTrue(response.data["ip_valid"])
        self.assertEqual(response.data["result"], "IN_OFFICE")
        self.assertTrue(
            AttendanceMark.objects.filter(
                user=self.subordinate,
                date=date.today(),
                status=AttendanceMark.Status.PRESENT,
            ).exists()
        )
        self.assertEqual(AttendanceSession.objects.filter(user=self.subordinate).count(), 1)
        log_in_office.assert_called_once()

    @patch("apps.attendance.views.AttendanceAuditService.log_office_checkin_outside")
    def test_check_in_outside_returns_403_and_does_not_mark_attendance(self, log_outside):
        self._create_approved_plan_for_today(mode_for_today="office")
        OfficeNetwork.objects.create(name="HQ", cidr="192.168.10.0/24", is_active=True)
        self.client.force_authenticate(user=self.subordinate)
        response = self.client.post(
            "/api/v1/attendance/check-in/",
            {"work_mode": "office"},
            format="json",
            HTTP_X_FORWARDED_FOR="203.0.113.42",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("detail", response.data)
        self.assertFalse(
            AttendanceMark.objects.filter(user=self.subordinate, date=date.today()).exists()
        )
        self.assertEqual(AttendanceSession.objects.filter(user=self.subordinate).count(), 1)
        log_outside.assert_called_once()

    def test_check_in_returns_403_when_office_ip_networks_do_not_match(self):
        self._create_approved_plan_for_today(mode_for_today="office")
        self.client.force_authenticate(user=self.subordinate)
        response = self.client.post(
            "/api/v1/attendance/check-in/",
            {"work_mode": "office"},
            format="json",
            HTTP_X_FORWARDED_FOR="192.168.10.55",
        )
        self.assertEqual(response.status_code, 403)

    @patch("apps.attendance.views.AttendanceAuditService.log_office_checkin_in_office")
    def test_check_in_in_office_by_ip_network(self, log_in_office):
        self._create_approved_plan_for_today(mode_for_today="office")
        OfficeNetwork.objects.create(name="HQ", cidr="192.168.10.0/24", is_active=True)
        self.client.force_authenticate(user=self.subordinate)
        response = self.client.post(
            "/api/v1/attendance/check-in/",
            {"work_mode": "office"},
            format="json",
            HTTP_X_FORWARDED_FOR="192.168.10.55",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["in_office"])
        self.assertTrue(response.data["ip_valid"])
        self.assertEqual(response.data["status"], "IN_OFFICE")
        log_in_office.assert_called_once()

    def test_online_check_in_requires_schedule_and_sets_remote_mark(self):
        self._create_approved_plan_for_today(mode_for_today="online")
        self.client.force_authenticate(user=self.subordinate)
        response = self.client.post("/api/v1/attendance/check-in/", {"work_mode": "online"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "ONLINE")
        self.assertFalse(response.data["in_office"])
        self.assertTrue(
            AttendanceMark.objects.filter(
                user=self.subordinate,
                date=date.today(),
                status=AttendanceMark.Status.REMOTE,
            ).exists()
        )

    def test_check_in_rejects_when_mode_mismatches_schedule(self):
        self._create_approved_plan_for_today(mode_for_today="online")
        self.client.force_authenticate(user=self.subordinate)
        response = self.client.post(
            "/api/v1/attendance/check-in/",
            {"work_mode": "office"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_superadmin_can_manage_office_networks_via_api(self):
        self.client.force_authenticate(user=self.super_admin)
        created = self.client.post(
            "/api/v1/attendance/admin/office-networks/",
            {"name": "HQ", "cidr": "192.168.50.0/24", "is_active": True},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        network_id = created.data["id"]

        listed = self.client.get("/api/v1/attendance/admin/office-networks/")
        self.assertEqual(listed.status_code, 200)
        self.assertGreaterEqual(len(listed.data), 1)

        patched = self.client.patch(
            f"/api/v1/attendance/admin/office-networks/{network_id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertFalse(patched.data["is_active"])

    def test_admin_cannot_manage_office_networks_via_api(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/attendance/admin/office-networks/")
        self.assertEqual(response.status_code, 403)

    @patch("apps.attendance.views.AttendanceAuditService.log_office_checkin_in_office")
    def test_check_in_uses_database_office_network_whitelist(self, log_in_office):
        self._create_approved_plan_for_today(mode_for_today="office")
        OfficeNetwork.objects.create(name="HQ DB", cidr="10.10.10.0/24", is_active=True)
        self.client.force_authenticate(user=self.subordinate)
        response = self.client.post(
            "/api/v1/attendance/check-in/",
            {"work_mode": "office"},
            format="json",
            HTTP_X_FORWARDED_FOR="10.10.10.55",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["ip_valid"])
        log_in_office.assert_called_once()
