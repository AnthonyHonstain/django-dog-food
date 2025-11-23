import json
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

import httpx
from django.conf import settings
from django.utils import timezone

from foodtracker.models import FoodLog

PACIFIC_TZ = ZoneInfo("America/Los_Angeles")


@dataclass
class DailyFoodTotal:
    pt_day: str
    food_total_g: int


@dataclass
class FeedingSummary:
    median_daily_food_g: float
    total_food_last_20_days_g: int
    daily_totals_last_20_days: list[DailyFoodTotal]


def _call_agent_with_prompt(prompt: str) -> str:
    """
    Low-level HTTP call to the agent. Mirrors the old inline logic in views.py.
    Raises if the request fails.
    """
    url = f"{settings.AGENT_ENDPOINT.rstrip('/')}/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.AGENT_ACCESS_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "include_functions_info": False,
        "include_retrieval_info": False,
        "include_guardrails_info": False,
    }

    resp = httpx.post(url, json=payload, headers=headers, timeout=10.0)
    resp.raise_for_status()
    body = resp.json()

    response = body["choices"][0]["message"]["content"]

    return response


def _window_start_utc(now_dt: datetime) -> datetime:
    """
    Compute the UTC datetime representing 00:00 PT 19 days ago so we have a
    20-day inclusive window ending today (in PT).
    """
    now_pt = timezone.localtime(now_dt, PACIFIC_TZ)
    start_pt_date = now_pt.date() - timedelta(days=19)
    start_of_day_pt = datetime.combine(start_pt_date, time.min, tzinfo=PACIFIC_TZ)
    return start_of_day_pt.astimezone(dt_timezone.utc)


def _feeding_summary_last_20_days(food_logs: list[FoodLog]) -> FeedingSummary:
    """
    Summaries keyed off PT calendar days because the DB stores UTC timestamps.
    """
    window_start = _window_start_utc(timezone.now())

    totals_by_day: defaultdict[date, int] = defaultdict(int)
    for log in food_logs:
        if log.feeddatetime < window_start:
            continue
        pt_day = timezone.localtime(log.feeddatetime, PACIFIC_TZ).date()
        totals_by_day[pt_day] += log.food_qty

    if not totals_by_day:
        return FeedingSummary(
            median_daily_food_g=0,
            total_food_last_20_days_g=0,
            daily_totals_last_20_days=[],
        )

    daily_totals_sorted = sorted(totals_by_day.items())
    totals_only = [total for _, total in daily_totals_sorted]

    return FeedingSummary(
        median_daily_food_g=statistics.median(totals_only),
        total_food_last_20_days_g=sum(totals_only),
        daily_totals_last_20_days=[
            DailyFoodTotal(pt_day=day.isoformat(), food_total_g=total)
            for day, total in daily_totals_sorted
        ],
    )


def _build_prompt(food_logs: list[FoodLog]) -> str:
    """
    Build the prompt string we send to the agent.
    """
    now_pt = timezone.localtime(timezone.now(), PACIFIC_TZ).isoformat()
    recent_entries = [log.to_llm_dict() for log in food_logs]
    recent_json = json.dumps(recent_entries, separators=(",", ":"))
    feeding_summary = _feeding_summary_last_20_days(food_logs)
    feeding_summary_json = json.dumps(asdict(feeding_summary), separators=(",", ":"))
    prompt = (
        "Recent feeding so far is: "
        + recent_json
        + " Feeding summary for last 20 PT days: "
        + feeding_summary_json
        + f" Given that Biscuit needs regular meals and it is currently {now_pt}, what should the next portion be?"
    )
    # TODO - add in logging framework
    # print(prompt)
    return prompt


def get_agent_suggestion(food_logs: list[FoodLog]) -> str:
    """
    Public helper the view will call:
    - builds the prompt using the provided food_logs
    - calls the agent
    - returns the agent's text suggestion
    """
    prompt = _build_prompt(food_logs)
    return _call_agent_with_prompt(prompt)
