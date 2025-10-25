import json

import httpx
from django.conf import settings
from django.utils import timezone

from foodtracker.models import FoodLog


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


def _build_prompt(food_logs: list[FoodLog]) -> str:
    """
    Build the prompt string we send to the agent.
    """
    now_utc = timezone.now().isoformat()
    recent_entries = [log.to_llm_dict() for log in food_logs]
    recent_json = json.dumps(recent_entries, separators=(",", ":"))
    prompt = (
        "Recent feeding so far is: "
        + recent_json
        + f" Given that Biscuit needs regular meals and it is currently {now_utc}, what should the next portion be?"
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
