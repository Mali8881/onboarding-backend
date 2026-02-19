from django.test import TestCase
from accounts.models import User
from onboarding_core.models import OnboardingDay
from .models import OnboardingReport


class OnboardingReportTests(TestCase):

    def setUp(self):
        self.user = User.objects.create(username="test")
        self.day = OnboardingDay.objects.create(
            day_number=1,
            title="Test Day",
            is_active=True
        )

    def test_cannot_review_non_sent_report(self):
        report = OnboardingReport.objects.create(
            user=self.user,
            day=self.day,
            did="a",
            will_do="b",
        )

        with self.assertRaises(ValueError):
            report.set_status(OnboardingReport.Status.ACCEPTED)

    def test_revision_requires_comment(self):
        report = OnboardingReport.objects.create(
            user=self.user,
            day=self.day,
            did="a",
            will_do="b",
            status=OnboardingReport.Status.SENT
        )

        with self.assertRaises(ValueError):
            report.set_status(OnboardingReport.Status.REVISION)

    def test_accept_report(self):
        report = OnboardingReport.objects.create(
            user=self.user,
            day=self.day,
            did="a",
            will_do="b",
            status=OnboardingReport.Status.SENT
        )

        report.set_status(OnboardingReport.Status.ACCEPTED)
        self.assertEqual(report.status, OnboardingReport.Status.ACCEPTED)

    def test_send_report(self):
        report = OnboardingReport.objects.create(
            user=self.user,
            day=self.day,
            did="a",
            will_do="b",
        )

        report.send()
        self.assertEqual(report.status, OnboardingReport.Status.SENT)
