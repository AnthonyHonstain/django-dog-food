from django.db import models


class FoodLog(models.Model):
    feeddatetime = models.DateTimeField()
    food_qty = models.IntegerField()
    water_qty = models.IntegerField()
    teeth_brush = models.BooleanField(default=False)

    class Meta:
        db_table = "foodlog"
