from django.db import models


class FoodLog(models.Model):
    feeddatetime = models.DateTimeField()
    food_qty = models.IntegerField()
    water_qty = models.IntegerField()

    class Meta:
        db_table = "foodlog"
