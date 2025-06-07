from django.test import TestCase
from django.utils import timezone
from datetime import datetime
from zoneinfo import ZoneInfo
from foodtracker.models import FoodLog


class TestFoodLogModel(TestCase):
    def test_create_and_retrieve_foodlog(self):
        # Create a fixed UTC datetime for testing
        test_datetime = datetime(2025, 5, 11, 14, 30, 0, tzinfo=ZoneInfo("UTC"))

        # Create a food log entry
        food_log = FoodLog.objects.create(
            feeddatetime=test_datetime,
            food_qty=500,
            water_qty=1000,
        )

        # Retrieve the entry
        retrieved_log = FoodLog.objects.get(id=food_log.id)

        # Verify the data
        self.assertEqual(retrieved_log.food_qty, 500)
        self.assertEqual(retrieved_log.water_qty, 1000)
        self.assertEqual(retrieved_log.feeddatetime, test_datetime)
        # Verify datetime is in UTC
        self.assertTrue(timezone.is_aware(retrieved_log.feeddatetime))
        # Both datetime.timezone.utc and ZoneInfo("UTC") are valid UTC timezone objects
        self.assertEqual(str(retrieved_log.feeddatetime.tzinfo), "UTC")
