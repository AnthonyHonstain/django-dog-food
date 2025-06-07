from django import forms
from foodtracker.models import FoodLog


class FoodLogForm(forms.ModelForm):
    teeth_brush = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Teeth"
    )
    
    class Meta:
        model = FoodLog
        fields = ["food_qty", "water_qty", "teeth_brush"]

    def clean_food_qty(self):
        food_qty = self.cleaned_data["food_qty"]
        if food_qty >= 100:
            raise forms.ValidationError("Food quantity must be less than 100.")
        return food_qty

    def clean_water_qty(self):
        water_qty = self.cleaned_data["water_qty"]
        if water_qty >= 100:
            raise forms.ValidationError("Water quantity must be less than 100.")
        return water_qty
