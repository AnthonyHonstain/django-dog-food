from django.urls import path
from foodtracker import views

urlpatterns = [
    path("", views.list_food_logs, name="list_food_logs"),
    path("chart/", views.food_logs_chart, name="food_logs_chart"),
    path("chart/data/", views.food_logs_chart_data, name="food_logs_chart_data"),
    path("add/", views.add_food_log, name="add_food_log"),
]
