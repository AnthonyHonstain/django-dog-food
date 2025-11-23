import json
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx

from foodtracker.models import FoodLog
from foodtracker.agent_service import (
    DailyFoodTotal,
    FeedingSummary,
    _feeding_summary_last_20_days,
    _build_prompt,
    get_agent_suggestion,
)


def _make_foodlog_at_utc(
    *,
    day: int,
    hour: int,
    food_qty: int,
    minute: int = 0,
    year: int = 2025,
    month: int = 10,
) -> FoodLog:
    """
    Create a FoodLog row for testing.
    """
    dt_utc = datetime(year, month, day, hour, minute, 0, tzinfo=ZoneInfo("UTC"))
    return FoodLog.objects.create(
        feeddatetime=dt_utc,
        food_qty=food_qty,
        water_qty=0,
        teeth_brush=False,
    )


@pytest.mark.django_db
def test_build_prompt_exact(monkeypatch):
    """
    _build_prompt should embed recent logs and the aggregated 20-day PT summary.
    """
    log1 = _make_foodlog_at_utc(day=24, hour=9, minute=30, food_qty=100)
    log2 = _make_foodlog_at_utc(day=24, hour=10, minute=30, food_qty=300)

    fixed_now = datetime(2025, 10, 25, 19, 16, 47, 123456, tzinfo=ZoneInfo("UTC"))
    monkeypatch.setattr(
        "foodtracker.agent_service.timezone.now",
        lambda: fixed_now,
    )

    prompt = _build_prompt([log1, log2])

    recent_json = (
        '[{"feeddatetime":"2025-10-24T02:30:00-07:00",'
        '"food_qty_g":100,"water_qty_ml":0,"teeth_brush":false},'
        '{"feeddatetime":"2025-10-24T03:30:00-07:00",'
        '"food_qty_g":300,"water_qty_ml":0,"teeth_brush":false}]'
    )

    feeding_summary_json = (
        '{"median_daily_food_g":400,"total_food_last_20_days_g":400,'
        '"daily_totals_last_20_days":[{"pt_day":"2025-10-24","food_total_g":400}]}'
    )

    expected_prompt = (
        "Recent feeding so far is: "
        + recent_json
        + " Feeding summary for last 20 PT days: "
        + feeding_summary_json
        + " Given that Biscuit needs regular meals and it is currently "
        + "2025-10-25T12:16:47.123456-07:00"
        + ", what should the next portion be?"
    )

    assert prompt == expected_prompt


@pytest.mark.django_db
@respx.mock
def test_get_agent_suggestion_success(settings, monkeypatch):
    """
    get_agent_suggestion should:
    - build the prompt from food_logs
    - POST to {AGENT_ENDPOINT}/api/v1/chat/completions
    - return the model message content
    """

    _make_foodlog_at_utc(day=25, hour=15, minute=30, food_qty=10)
    _make_foodlog_at_utc(day=25, hour=16, minute=30, food_qty=20)

    # Freeze timezone.now() same as above
    fixed_now = datetime(2025, 10, 25, 19, 16, 47, 123456, tzinfo=ZoneInfo("UTC"))
    monkeypatch.setattr(
        "foodtracker.agent_service.timezone.now",
        lambda: fixed_now,
    )

    settings.AGENT_ENDPOINT = "https://agent.example.test"
    settings.AGENT_ACCESS_KEY = "sekret-token"
    mock_route = respx.post("https://agent.example.test/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "next meal should be 15g of kibble"}}
                ]
            },
        )
    )

    food_logs = list(FoodLog.objects.all().order_by("-feeddatetime")[:50])
    suggestion = get_agent_suggestion(food_logs)

    assert suggestion == "next meal should be 15g of kibble"
    assert mock_route.called

    request = mock_route.calls.last.request

    # Authorization header should have the bearer token
    assert request.headers["Authorization"] == "Bearer sekret-token"

    # Body should contain messages[0].content with the built prompt
    sent_json = json.loads(request.content.decode("utf-8"))

    assert sent_json["stream"] is False
    assert sent_json["include_functions_info"] is False
    assert sent_json["include_retrieval_info"] is False
    assert sent_json["include_guardrails_info"] is False

    recent_json = (
        '[{"feeddatetime":"2025-10-25T09:30:00-07:00",'
        '"food_qty_g":20,"water_qty_ml":0,"teeth_brush":false},'
        '{"feeddatetime":"2025-10-25T08:30:00-07:00",'
        '"food_qty_g":10,"water_qty_ml":0,"teeth_brush":false}]'
    )

    feeding_summary_json = (
        '{"median_daily_food_g":30,"total_food_last_20_days_g":30,'
        '"daily_totals_last_20_days":[{"pt_day":"2025-10-25","food_total_g":30}]}'
    )

    expected_prompt = (
        "Recent feeding so far is: "
        + recent_json
        + " Feeding summary for last 20 PT days: "
        + feeding_summary_json
        + " Given that Biscuit needs regular meals and it is currently "
        + "2025-10-25T12:16:47.123456-07:00"
        + ", what should the next portion be?"
    )

    assert sent_json["messages"][0]["content"] == expected_prompt


@pytest.mark.django_db
@respx.mock
def test_get_agent_suggestion_http_error_raises(settings):
    """
    If the agent returns a non-2xx response, httpx.raise_for_status() should
    bubble an HTTPStatusError. We don't swallow here; the view handles it.
    """

    # Minimal row so _build_prompt works
    _make_foodlog_at_utc(day=11, month=5, hour=14, minute=30, food_qty=5)

    settings.AGENT_ENDPOINT = "https://agent.example.test"
    settings.AGENT_ACCESS_KEY = "sekret-token"

    respx.post("https://agent.example.test/api/v1/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "boom"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        food_logs = FoodLog.objects.all()
        get_agent_suggestion(food_logs)


@pytest.mark.django_db
def test_feeding_summary_respects_pt_days_and_window(monkeypatch):
    """
    Median/total should ignore rows before the 20-day PT window and group by PT day.
    """

    fixed_now = datetime(2025, 10, 25, 8, 0, 0, tzinfo=ZoneInfo("UTC"))
    monkeypatch.setattr(
        "foodtracker.agent_service.timezone.now",
        lambda: fixed_now,
    )

    # Before the window start: 2025-10-06T00:00:00-07:00 -> 07:00 UTC.
    _make_foodlog_at_utc(day=6, hour=6, minute=59, food_qty=999)

    # Inside window and exercises PT day bucketing.
    _make_foodlog_at_utc(day=6, hour=7, food_qty=10)
    _make_foodlog_at_utc(day=24, hour=6, minute=30, food_qty=20)  # PT day is 2025-10-23
    _make_foodlog_at_utc(day=25, hour=7, minute=30, food_qty=30)

    summary = _feeding_summary_last_20_days(list(FoodLog.objects.all()))

    assert summary == FeedingSummary(
        median_daily_food_g=20,
        total_food_last_20_days_g=60,
        daily_totals_last_20_days=[
            DailyFoodTotal(pt_day="2025-10-06", food_total_g=10),
            DailyFoodTotal(pt_day="2025-10-23", food_total_g=20),
            DailyFoodTotal(pt_day="2025-10-25", food_total_g=30),
        ],
    )
