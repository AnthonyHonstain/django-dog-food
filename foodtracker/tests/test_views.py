from django.test import TestCase, Client
from django.urls import reverse
from datetime import datetime
from zoneinfo import ZoneInfo
from foodtracker.models import FoodLog


class TestListFoodLogsView(TestCase):
    def setUp(self):
        self.client = Client()
        # Create test data with fixed datetimes
        FoodLog.objects.create(
            feeddatetime=datetime(2025, 5, 11, 14, 30, 0, tzinfo=ZoneInfo("UTC")),
            food_qty=100,
            water_qty=200
        )
        FoodLog.objects.create(
            feeddatetime=datetime(2025, 5, 11, 15, 30, 0, tzinfo=ZoneInfo("UTC")),
            food_qty=300,
            water_qty=400
        )

    def test_list_food_logs(self):
        response = self.client.get(reverse("list_food_logs"))
        self.assertEqual(response.status_code, 200)
        
        # Check that the response contains our test data
        content = response.content.decode()
        self.assertIn("2025-05-11 14:30:00", content)  # First datetime
        self.assertIn("2025-05-11 15:30:00", content)  # Second datetime
        self.assertIn("100", content)  # First food_qty
        self.assertIn("200", content)  # First water_qty
        self.assertIn("300", content)  # Second food_qty
        self.assertIn("400", content)  # Second water_qty
        
        # Verify order (newest first)
        first_pos = content.find("2025-05-11 15:30:00")
        second_pos = content.find("2025-05-11 14:30:00")
        self.assertLess(first_pos, second_pos)  # Newer date should appear first
