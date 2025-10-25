from django.shortcuts import render, redirect
from django.utils import timezone

from foodtracker.agent_service import get_agent_suggestion
from foodtracker.models import FoodLog
from foodtracker.forms import FoodLogForm


def get_food_logs() -> list[FoodLog]:
    """Helper function to get the common context for food log views."""
    return list(FoodLog.objects.all().order_by("-feeddatetime")[:50])


def list_food_logs(request):
    """
    Display all food logs with a form to add new ones — and try to include a GenAI suggestion.
    If any Exception we fall back to '(agent error: ...)'.
    """
    food_logs = get_food_logs()
    ctx = {}
    ctx["form"] = FoodLogForm()
    ctx["food_logs"] = food_logs

    try:
        ctx["agent_suggestion"] = get_agent_suggestion(food_logs)
    except Exception as e:
        ctx["agent_suggestion"] = f"(agent error: {e})"

    return render(request, "foodtracker/food_log_list.html", ctx)


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
        ctx = {"form": form, "food_logs": get_food_logs()}

        return render(request, "foodtracker/food_log_list.html", ctx)

    # For GET requests, redirect to the list view
    return redirect("list_food_logs")
