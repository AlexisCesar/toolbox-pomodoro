"""A dependency-free Pomodoro Addon for Toolbox API version 1."""

from __future__ import annotations

import json
import math
import sys
import time
from typing import Any


FOCUS_SECONDS = 25 * 60
SHORT_BREAK_SECONDS = 5 * 60
LONG_BREAK_SECONDS = 15 * 60
FOCUS_SESSIONS_PER_LONG_BREAK = 4

PHASE_LABELS = {
    "focus": "Focus",
    "short_break": "Short break",
    "long_break": "Long break",
}


def default_state() -> dict[str, Any]:
    """Return a fresh paused focus session."""
    return {
        "phase": "focus",
        "remaining_seconds": FOCUS_SECONDS,
        "deadline": None,
        "completed_focus_sessions": 0,
    }


def _phase_duration(phase: str) -> int:
    if phase == "short_break":
        return SHORT_BREAK_SECONDS
    if phase == "long_break":
        return LONG_BREAK_SECONDS
    return FOCUS_SECONDS


def _normalise_state(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return default_state()

    phase = value.get("phase")
    if phase not in PHASE_LABELS:
        phase = "focus"

    duration = _phase_duration(phase)
    remaining = value.get("remaining_seconds", duration)
    if (
        not isinstance(remaining, (int, float))
        or isinstance(remaining, bool)
        or not math.isfinite(remaining)
    ):
        remaining = duration
    remaining = max(0, min(duration, math.ceil(remaining)))

    deadline = value.get("deadline")
    if (
        not isinstance(deadline, (int, float))
        or isinstance(deadline, bool)
        or not math.isfinite(deadline)
    ):
        deadline = None

    completed = value.get("completed_focus_sessions", 0)
    if not isinstance(completed, int) or isinstance(completed, bool) or completed < 0:
        completed = 0

    return {
        "phase": phase,
        "remaining_seconds": remaining,
        "deadline": deadline,
        "completed_focus_sessions": completed,
    }


def _settle_finished_phase(state: dict[str, Any], now: float) -> None:
    deadline = state["deadline"]
    if deadline is None or deadline > now:
        return

    state["deadline"] = None
    if state["phase"] == "focus":
        state["completed_focus_sessions"] += 1
        if state["completed_focus_sessions"] % FOCUS_SESSIONS_PER_LONG_BREAK == 0:
            state["phase"] = "long_break"
        else:
            state["phase"] = "short_break"
    else:
        state["phase"] = "focus"
    state["remaining_seconds"] = _phase_duration(state["phase"])


def _remaining_seconds(state: dict[str, Any], now: float) -> int:
    deadline = state["deadline"]
    if deadline is not None:
        return max(0, math.ceil(deadline - now))
    return state["remaining_seconds"]


def _format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"


def _render_view(state: dict[str, Any], now: float) -> dict[str, Any]:
    remaining = _remaining_seconds(state, now)
    running = state["deadline"] is not None
    status = "Running" if running else "Paused"
    phase_label = PHASE_LABELS[state["phase"]]
    body = (
        f"{phase_label}\n"
        f"Time remaining: {_format_duration(remaining)}\n"
        f"Timer: {status}\n"
        f"Completed focus sessions: {state['completed_focus_sessions']}\n\n"
        "A completed focus session selects the next break. Start it when you are ready."
    )
    actions = (
        [{"id": "pause", "label": "Pause"}]
        if running
        else [{"id": "start", "label": "Start"}]
    )
    actions.append({"id": "reset", "label": "Reset"})
    return {
        "title": f"Pomodoro | {phase_label}",
        "body": body,
        "state": state,
        "actions": actions,
    }


def handle_request(request: object, *, now: float | None = None) -> dict[str, Any]:
    """Handle one Toolbox view, refresh, or action request."""
    if not isinstance(request, dict):
        raise ValueError("The request must be a JSON object.")

    protocol = request.get("protocol")
    request_id = request.get("id")
    method = request.get("method")
    if (
        not isinstance(protocol, int)
        or isinstance(protocol, bool)
        or protocol != 1
        or not isinstance(request_id, str)
        or not request_id
    ):
        raise ValueError("The request protocol or id is invalid.")
    if method not in {"view", "refresh", "action"}:
        raise ValueError("The request method is unsupported.")

    current_time = time.time() if now is None else now
    state = _normalise_state(request.get("state"))
    _settle_finished_phase(state, current_time)

    if method == "action":
        action = request.get("action")
        if action == "start" and state["deadline"] is None:
            if state["remaining_seconds"] <= 0:
                state["remaining_seconds"] = _phase_duration(state["phase"])
            state["deadline"] = current_time + state["remaining_seconds"]
        elif action == "pause" and state["deadline"] is not None:
            state["remaining_seconds"] = _remaining_seconds(state, current_time)
            state["deadline"] = None
        elif action == "reset":
            completed_sessions = state["completed_focus_sessions"]
            state = default_state()
            state["completed_focus_sessions"] = completed_sessions

    return {
        "protocol": 1,
        "id": request_id,
        "view": _render_view(state, current_time),
    }


def main() -> int:
    """Read one JSON Lines request and write one JSON Lines response."""
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    line = sys.stdin.readline()
    if not line:
        return 0
    try:
        request = json.loads(line)
        response = handle_request(request)
    except (json.JSONDecodeError, ValueError) as error:
        print(f"Invalid Toolbox Addon request: {error}", file=sys.stderr)
        return 1

    print(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
