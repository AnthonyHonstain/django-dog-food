import json
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx

from foodtracker.models import FoodLog
from foodtracker.agent_service import (
    _build_prompt,
    get_agent_suggestion,
)


def _make_foodlog(
    *,
    hour: int,
    food_qty: int,
) -> FoodLog:
    """
    Create a FoodLog row for testing.
    """
    return FoodLog.objects.create(
        feeddatetime=datetime(2025, 5, 11, hour, 30, 0, tzinfo=ZoneInfo("UTC")),
        food_qty=food_qty,
        water_qty=0,
        teeth_brush=False,
    )


@pytest.mark.django_db
def test_build_prompt_exact(monkeypatch):
    """
    _build_prompt should sum .food_qty across provided logs and embed that value in the exact phrasing we expect.
    """
    log1 = _make_foodlog(hour=9, food_qty=100)
    log2 = _make_foodlog(hour=10, food_qty=300)

    fixed_now = datetime(2025, 10, 25, 19, 16, 47, 123456, tzinfo=ZoneInfo("UTC"))
    monkeypatch.setattr(
        "foodtracker.agent_service.timezone.now",
        lambda: fixed_now,
    )

    prompt = _build_prompt([log1, log2])

    recent_json = (
        '[{"feeddatetime":"2025-05-11T02:30:00-07:00",'
        '"food_qty_g":100,"water_qty_ml":0,"teeth_brush":false},'
        '{"feeddatetime":"2025-05-11T03:30:00-07:00",'
        '"food_qty_g":300,"water_qty_ml":0,"teeth_brush":false}]'
    )

    expected_prompt = (
        "Recent feeding so far is: "
        + recent_json
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

    _make_foodlog(hour=14, food_qty=10)
    _make_foodlog(hour=15, food_qty=20)

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
        '[{"feeddatetime":"2025-05-11T08:30:00-07:00",'
        '"food_qty_g":20,"water_qty_ml":0,"teeth_brush":false},'
        '{"feeddatetime":"2025-05-11T07:30:00-07:00",'
        '"food_qty_g":10,"water_qty_ml":0,"teeth_brush":false}]'
    )

    expected_prompt = (
        "Recent feeding so far is: "
        + recent_json
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
    FoodLog.objects.create(
        feeddatetime=datetime(2025, 5, 11, 14, 30, 0, tzinfo=ZoneInfo("UTC")),
        food_qty=5,
        water_qty=1,
        teeth_brush=False,
    )

    settings.AGENT_ENDPOINT = "https://agent.example.test"
    settings.AGENT_ACCESS_KEY = "sekret-token"

    respx.post("https://agent.example.test/api/v1/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "boom"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        food_logs = FoodLog.objects.all()
        get_agent_suggestion(food_logs)
