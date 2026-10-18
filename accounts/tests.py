
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import GovernmentScheme


class GovernmentSchemePortalTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPass123!"
        )

    def test_login_page_opens(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)

    def test_registration_page_opens(self):
        response = self.client.get(reverse("accounts:register"))

        self.assertEqual(response.status_code, 200)

    def test_home_requires_login(self):
        response = self.client.get(reverse("accounts:home"))

        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_can_open_home(self):
        self.client.login(
            username="testuser",
            password="TestPass123!"
        )

        response = self.client.get(reverse("accounts:home"))

        self.assertEqual(response.status_code, 200)

    def test_dashboard_counts_schemes(self):
        GovernmentScheme.objects.create(
            name="Test Scholarship",
            slug="test-scholarship",
            category="Education",
            description="Test description",
            eligibility="Test eligibility",
            benefits="Test benefits",
            official_url="https://example.com/",
        )

        self.client.login(
            username="testuser",
            password="TestPass123!"
        )

        response = self.client.get(reverse("accounts:home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_schemes"], 1)

    def test_user_can_log_in(self):
        login_successful = self.client.login(
            username="testuser",
            password="TestPass123!"
        )

        self.assertTrue(login_successful)

    def test_scheme_is_saved_in_database(self):
        scheme = GovernmentScheme.objects.create(
            name="Test Pension Scheme",
            slug="test-pension-scheme",
            category="Pension",
            description="Test description",
            eligibility="Test eligibility",
            benefits="Test benefits",
            official_url="https://example.com/",
        )

        self.assertTrue(
            GovernmentScheme.objects.filter(
                slug="test-pension-scheme"
            ).exists()
        )

        self.assertEqual(scheme.name, "Test Pension Scheme")
