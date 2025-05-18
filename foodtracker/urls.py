from django.urls import path
from foodtracker import views

urlpatterns = [
    path("", views.list_food_logs, name="list_food_logs"),
    path("add/", views.add_food_log, name="add_food_log"),
]
