from zoneinfo import ZoneInfo

from django.db import models


class FoodLog(models.Model):
    feeddatetime = models.DateTimeField()
    food_qty = models.IntegerField()
    water_qty = models.IntegerField()
    teeth_brush = models.BooleanField(default=False)

    class Meta:
        db_table = "foodlog"

    def to_llm_dict(self) -> dict:
        dt_utc = self.feeddatetime.astimezone(ZoneInfo("UTC"))
        return {
            "feeddatetime": dt_utc.isoformat(),
            "food_qty_g": self.food_qty,
            "water_qty_ml": self.water_qty,
            "teeth_brush": self.teeth_brush,
        }
