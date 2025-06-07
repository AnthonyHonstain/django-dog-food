from django.shortcuts import render, redirect
from django.utils import timezone
from foodtracker.models import FoodLog
from foodtracker.forms import FoodLogForm


def get_food_logs_context(form=None):
    """Helper function to get the common context for food log views."""
    return {
        "food_logs": FoodLog.objects.all().order_by("-feeddatetime")[:50],
        "form": form or FoodLogForm(),
    }


def list_food_logs(request):
    """Display all food logs with a form to add new ones."""
    return render(request, "foodtracker/food_log_list.html", get_food_logs_context())


def add_food_log(request):
    """Handle form submission for adding new food logs."""
    if request.method == "POST":
        form = FoodLogForm(request.POST)
        if form.is_valid():
            food_log = form.save(commit=False)
            food_log.feeddatetime = timezone.now()
            food_log.save()
            return redirect("list_food_logs")

        # If form is invalid, show the form with errors
        context = get_food_logs_context(form=form)
        return render(request, "foodtracker/food_log_list.html", context)

    # For GET requests, redirect to the list view
    return redirect("list_food_logs")
