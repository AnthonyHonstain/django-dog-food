from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from datetime import datetime
from django.utils import timezone
from zoneinfo import ZoneInfo
from foodtracker.models import FoodLog
from foodtracker.views import get_food_logs_context
from foodtracker.forms import FoodLogForm


class TestListFoodLogsView(TestCase):
    def setUp(self):
        self.client = Client()
        # Create test data with fixed datetimes
        FoodLog.objects.create(
            feeddatetime=datetime(2025, 5, 11, 14, 30, 0, tzinfo=ZoneInfo("UTC")),
            food_qty=100,
            water_qty=200,
        )
        FoodLog.objects.create(
            feeddatetime=datetime(2025, 5, 11, 15, 30, 0, tzinfo=ZoneInfo("UTC")),
            food_qty=300,
            water_qty=400,
        )

    def test_list_food_logs(self):
        response = self.client.get(reverse("list_food_logs"))
        self.assertEqual(response.status_code, 200)

        # Check that the response contains our test data
        content = response.content.decode()
        self.assertIn(
            'data-utc-dt="2025-05-11T14:30:00+00:00"', content
        )  # First datetime (ISO8601)
        self.assertIn(
            'data-utc-dt="2025-05-11T15:30:00+00:00"', content
        )  # Second datetime (ISO8601)
        self.assertIn("100", content)  # First food_qty
        self.assertIn("200", content)  # First water_qty
        self.assertIn("300", content)  # Second food_qty
        self.assertIn("400", content)  # Second water_qty

        # Verify order (newest first)
        first_pos = content.find('data-utc-dt="2025-05-11T15:30:00+00:00"')
        second_pos = content.find('data-utc-dt="2025-05-11T14:30:00+00:00"')
        self.assertLess(first_pos, second_pos)  # Newer date should appear first


class TestAddFoodLogView(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("add_food_log")

    def test_valid_form_submission(self):
        """Test that a valid form submission creates a new FoodLog and redirects"""
        initial_count = FoodLog.objects.count()

        response = self.client.post(
            self.url,
            {
                "food_qty": 42,
                "water_qty": 37,
            },
        )

        # Should redirect to the list view
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("list_food_logs"))

        # Should have created one new record
        self.assertEqual(FoodLog.objects.count(), initial_count + 1)

        # Verify the record was created with correct values
        food_log = FoodLog.objects.latest("id")
        self.assertEqual(food_log.food_qty, 42)
        self.assertEqual(food_log.water_qty, 37)
        self.assertIsNotNone(food_log.feeddatetime)

        # The feeddatetime should be recent (within 1 minute of now)
        now = timezone.now()
        self.assertLess((now - food_log.feeddatetime).total_seconds(), 60)

    def test_invalid_form_submission(self):
        """Test that an invalid form submission redisplays the form with errors"""
        initial_count = FoodLog.objects.count()

        # Submit with invalid data (values that will trigger our form validation)
        response = self.client.post(
            self.url,
            {
                "food_qty": 150,  # Invalid: exceeds max of 99
                "water_qty": 200,  # Invalid: exceeds max of 99
            },
        )

        # Should return 200 with form errors
        self.assertEqual(response.status_code, 200)

        # No new records should be created
        self.assertEqual(FoodLog.objects.count(), initial_count)

        # Check that the response contains form with errors
        content = response.content.decode()

        # Check that the form inputs have the is-invalid class
        self.assertIn(
            'class="form-control form-control-sm form-control-dark bg-dark text-light is-invalid"',
            content,
        )

        # Check that our custom validation messages are present
        self.assertIn("Food quantity must be less than 100", content)
        self.assertIn("Water quantity must be less than 100", content)


class TestGetFoodLogsContext(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        # Create test data
        FoodLog.objects.create(
            feeddatetime=datetime(2025, 5, 11, 14, 30, 0, tzinfo=ZoneInfo("UTC")),
            food_qty=100,
            water_qty=200,
        )
        FoodLog.objects.create(
            feeddatetime=datetime(2025, 5, 11, 15, 30, 0, tzinfo=ZoneInfo("UTC")),
            food_qty=300,
            water_qty=400,
        )

    def test_get_food_logs_context_default(self):
        """Test that context contains food logs and a new form when no form is provided."""
        context = get_food_logs_context()

        # Verify context keys
        self.assertIn("food_logs", context)
        self.assertIn("form", context)

        # Verify food logs
        self.assertEqual(len(context["food_logs"]), 2)
        self.assertEqual(context["food_logs"][0].food_qty, 300)  # Newest first
        self.assertEqual(context["food_logs"][1].food_qty, 100)  # Oldest last

        # Verify form is a new instance
        form = context["form"]
        self.assertIsInstance(form, FoodLogForm)
        # Check that the form is not bound to any data
        self.assertFalse(form.is_bound)
        # Check that the form's instance doesn't have an id (meaning it's a new instance)
        if hasattr(form, "instance") and form.instance is not None:
            self.assertIsNone(form.instance.id)

    def test_get_food_logs_context_with_form(self):
        """Test that context uses the provided form instance."""
        test_form = FoodLogForm(data={"food_qty": 50, "water_qty": 30})
        context = get_food_logs_context(form=test_form)

        # Verify the form in context is the same instance we passed in
        self.assertIs(context["form"], test_form)

        # Verify food logs are still included
        self.assertEqual(len(context["food_logs"]), 2)
