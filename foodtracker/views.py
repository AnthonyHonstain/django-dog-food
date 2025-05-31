from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDate
from foodtracker.models import FoodLog
from foodtracker.forms import FoodLogForm


def list_food_logs(request):
    food_logs = FoodLog.objects.all().order_by("-feeddatetime")
    form = FoodLogForm()
    
    context = {
        "food_logs": food_logs,
        "form": form,
        "is_htmx": request.headers.get('HX-Request') == 'true'
    }
    
    if context["is_htmx"]:
        return render(request, "foodtracker/partials/food_log_list_content.html", context)
    return render(request, "foodtracker/food_log_list.html", context)


def food_logs_chart(request):
    if request.headers.get('HX-Request') == 'true':
        return render(request, "foodtracker/partials/food_chart.html")
    return render(request, "foodtracker/food_log_list.html", {"show_chart": True})


def food_logs_chart_data(request):
    # Group food logs by date and sum the quantities
    daily_totals = FoodLog.objects.annotate(
        date=TruncDate('feeddatetime')
    ).values('date').annotate(
        total_food=Sum('food_qty')
    ).order_by('date')
    
    # Format the data for the chart
    labels = [entry['date'].strftime('%Y-%m-%d') for entry in daily_totals]
    data = [float(entry['total_food']) for entry in daily_totals]
    
    return JsonResponse({
        'labels': labels,
        'data': data
    })


def add_food_log(request):
    if request.method == "POST":
        form = FoodLogForm(request.POST)
        if form.is_valid():
            food_log = form.save(commit=False)
            food_log.feeddatetime = timezone.now()
            food_log.save()
            # Return empty response for HTMX to handle the redirect
            if request.headers.get('HX-Request') == 'true':
                return HttpResponse(status=204, headers={
                    'HX-Trigger': 'foodLogAdded'
                })
            return redirect('list_food_logs')
        else:
            # Return the form with errors
            return render(request, "foodtracker/partials/food_log_form.html", {"form": form})
    else:
        form = FoodLogForm()
        return render(request, "foodtracker/partials/food_log_form.html", {"form": form})
