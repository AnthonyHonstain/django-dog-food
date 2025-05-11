from django.urls import path
from foodtracker import views

urlpatterns = [
    path("", views.list_food_logs, name="list_food_logs"),
]
