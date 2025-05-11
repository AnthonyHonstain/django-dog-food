from django.shortcuts import render
from foodtracker.models import FoodLog


def list_food_logs(request):
    food_logs = FoodLog.objects.all().order_by("-feeddatetime")
    return render(request, "foodtracker/food_log_list.html", {"food_logs": food_logs})
