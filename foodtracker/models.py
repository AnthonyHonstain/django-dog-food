from zoneinfo import ZoneInfo

from django.db import models
from django.utils import timezone

PACIFIC_TZ = ZoneInfo("America/Los_Angeles")


class FoodLog(models.Model):
    feeddatetime = models.DateTimeField()
    food_qty = models.IntegerField()
    water_qty = models.IntegerField()
    teeth_brush = models.BooleanField(default=False)

    class Meta:
        db_table = "foodlog"

    def to_llm_dict(self) -> dict:
        dt_pt = timezone.localtime(self.feeddatetime, PACIFIC_TZ)
        return {
            "feeddatetime": dt_pt.isoformat(),
            "food_qty_g": self.food_qty,
            "water_qty_ml": self.water_qty,
            "teeth_brush": self.teeth_brush,
        }
