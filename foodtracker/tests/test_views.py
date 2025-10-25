from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from foodtracker.models import FoodLog
from foodtracker.views import get_food_logs


def _make_foodlog(
    *,
    hour: int,
    food_qty: int,
    water_qty: int,
) -> FoodLog:
    """
    Create a FoodLog row for testing.
    """
    return FoodLog.objects.create(
        feeddatetime=datetime(2025, 5, 11, hour, 30, 0, tzinfo=ZoneInfo("UTC")),
        food_qty=food_qty,
        water_qty=water_qty,
        teeth_brush=False,
    )


class TestListFoodLogsView(TestCase):
    def setUp(self):
        self.client = Client()
        _make_foodlog(hour=14, food_qty=100, water_qty=200)
        _make_foodlog(hour=15, food_qty=300, water_qty=400)

    @patch("foodtracker.views.get_agent_suggestion", return_value="stub suggestion")
    def test_list_food_logs(self, mock_agent):
        response = self.client.get(reverse("list_food_logs"))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # Data from first row
        self.assertIn('data-utc-dt="2025-05-11T14:30:00+00:00"', content)
        self.assertIn("100", content)
        self.assertIn("200", content)

        # Data from second row
        self.assertIn('data-utc-dt="2025-05-11T15:30:00+00:00"', content)
        self.assertIn("300", content)
        self.assertIn("400", content)

        # Verify order (newest first: 15:30 appears before 14:30)
        first_pos = content.find('data-utc-dt="2025-05-11T15:30:00+00:00"')
        second_pos = content.find('data-utc-dt="2025-05-11T14:30:00+00:00"')
        self.assertLess(first_pos, second_pos)

        # We should have injected the mocked agent suggestion into the template
        mock_agent.assert_called_once()
        self.assertIn("stub suggestion", content)

        # And the view should include the form (implicit check: submit button is present)
        self.assertIn('<form id="food-log-form"', content)


class TestAddFoodLogView(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("add_food_log")

    def test_valid_form_submission(self):
        """
        Valid POST should:
        - create a FoodLog
        - redirect to list_food_logs
        - stamp feeddatetime with "now"
        """
        initial_count = FoodLog.objects.count()

        response = self.client.post(
            self.url,
            {
                "food_qty": 42,
                "water_qty": 37,
                "teeth_brush": True,
            },
        )

        # Should redirect to the list view
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("list_food_logs"))

        # One new record created
        self.assertEqual(FoodLog.objects.count(), initial_count + 1)

        # Verify fields on the new record
        food_log = FoodLog.objects.latest("id")
        self.assertEqual(food_log.food_qty, 42)
        self.assertEqual(food_log.water_qty, 37)
        self.assertTrue(food_log.teeth_brush)
        self.assertIsNotNone(food_log.feeddatetime)

        # The feeddatetime should be very recent (within 1 minute of now)
        now = timezone.now()
        self.assertLess((now - food_log.feeddatetime).total_seconds(), 60)

    def test_invalid_form_submission(self):
        """
        Invalid POST should:
        - NOT create a FoodLog
        - return 200
        - re-render the page with errors
        """
        initial_count = FoodLog.objects.count()

        response = self.client.post(
            self.url,
            {
                "food_qty": 150,  # Invalid (>99)
                "water_qty": 200,  # Invalid (>99)
                "teeth_brush": False,
            },
        )

        # Should NOT redirect; should re-render template with 200
        self.assertEqual(response.status_code, 200)

        # Should not create new record
        self.assertEqual(FoodLog.objects.count(), initial_count)

        content = response.content.decode()

        # Field should have is-invalid class for both inputs
        self.assertIn(
            'class="form-control form-control-sm form-control-dark bg-dark text-light is-invalid"',
            content,
        )

        # Custom validation messages
        self.assertIn("Food quantity must be less than 100", content)
        self.assertIn("Water quantity must be less than 100", content)


class TestGetFoodLogs(TestCase):
    def setUp(self):
        _make_foodlog(hour=15, food_qty=300, water_qty=400)
        _make_foodlog(hour=14, food_qty=100, water_qty=200)

    def test_get_food_logs_returns_sorted_list(self):
        """
        get_food_logs() should return a list of FoodLog objects,
        newest first, limited to 50.
        """
        logs = get_food_logs()

        self.assertEqual(len(logs), 2)

        self.assertEqual(logs[0].food_qty, 300)
        self.assertEqual(logs[1].food_qty, 100)
