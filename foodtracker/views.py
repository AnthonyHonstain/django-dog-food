from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone
from foodtracker.models import FoodLog
from foodtracker.forms import FoodLogForm


def list_food_logs(request):
    food_logs = FoodLog.objects.all().order_by("-feeddatetime")[:100]
    form = FoodLogForm()
    return render(request, "foodtracker/food_log_list.html", {"food_logs": food_logs, "form": form})


def add_food_log(request):
    if request.method == "POST":
        form = FoodLogForm(request.POST)
        if form.is_valid():
            food_log = form.save(commit=False)
            food_log.feeddatetime = timezone.now()
            food_log.save()
            # Render just the new row
            return render(request, "foodtracker/partials/food_log_row.html", {"log": food_log})
        else:
            # Return the form with errors
            return render(request, "foodtracker/partials/food_log_form.html", {"form": form})
    else:
        form = FoodLogForm()
        return render(request, "foodtracker/partials/food_log_form.html", {"form": form})
