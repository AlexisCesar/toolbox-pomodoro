import unittest

from addon import FOCUS_SECONDS, LONG_BREAK_SECONDS, SHORT_BREAK_SECONDS, handle_request


def request(method: str, state=None, action: str | None = None) -> dict:
    value = {"protocol": 1, "id": "test-request", "method": method, "state": state}
    if action is not None:
        value["action"] = action
    return value


class PomodoroAddonTests(unittest.TestCase):
    def test_view_starts_paused_with_a_twenty_five_minute_focus(self) -> None:
        response = handle_request(request("view"), now=100.0)
        view = response["view"]

        self.assertEqual(response["protocol"], 1)
        self.assertEqual(response["id"], "test-request")
        self.assertEqual(view["state"]["phase"], "focus")
        self.assertEqual(view["state"]["remaining_seconds"], FOCUS_SECONDS)
        self.assertIsNone(view["state"]["deadline"])
        self.assertIn("25:00", view["body"])
        self.assertEqual(view["actions"][0]["id"], "start")

    def test_start_refresh_and_pause_preserve_the_remaining_time(self) -> None:
        started = handle_request(request("action", action="start"), now=100.0)
        state = started["view"]["state"]
        self.assertEqual(state["deadline"], 100.0 + FOCUS_SECONDS)

        refreshed = handle_request(request("refresh", state), now=161.0)
        self.assertEqual(refreshed["view"]["state"]["deadline"], state["deadline"])
        self.assertIn("23:59", refreshed["view"]["body"])

        paused = handle_request(
            request("action", refreshed["view"]["state"], "pause"),
            now=200.0,
        )
        paused_state = paused["view"]["state"]
        self.assertIsNone(paused_state["deadline"])
        self.assertEqual(paused_state["remaining_seconds"], FOCUS_SECONDS - 100)
        self.assertEqual(paused["view"]["actions"][0]["id"], "start")

    def test_completed_focus_selects_a_short_break(self) -> None:
        state = {
            "phase": "focus",
            "remaining_seconds": 3,
            "deadline": None,
            "completed_focus_sessions": 0,
        }
        started = handle_request(request("action", state, "start"), now=10.0)
        finished = handle_request(request("refresh", started["view"]["state"]), now=13.0)

        finished_state = finished["view"]["state"]
        self.assertEqual(finished_state["phase"], "short_break")
        self.assertEqual(finished_state["remaining_seconds"], SHORT_BREAK_SECONDS)
        self.assertIsNone(finished_state["deadline"])
        self.assertEqual(finished_state["completed_focus_sessions"], 1)

    def test_fourth_focus_selects_a_long_break(self) -> None:
        state = {
            "phase": "focus",
            "remaining_seconds": 1,
            "deadline": 10.0,
            "completed_focus_sessions": 3,
        }
        finished = handle_request(request("refresh", state), now=10.0)

        self.assertEqual(finished["view"]["state"]["phase"], "long_break")
        self.assertEqual(finished["view"]["state"]["remaining_seconds"], LONG_BREAK_SECONDS)
        self.assertEqual(finished["view"]["state"]["completed_focus_sessions"], 4)

    def test_completed_break_returns_to_focus(self) -> None:
        state = {
            "phase": "short_break",
            "remaining_seconds": 1,
            "deadline": 10.0,
            "completed_focus_sessions": 1,
        }
        finished = handle_request(request("refresh", state), now=10.0)

        self.assertEqual(finished["view"]["state"]["phase"], "focus")
        self.assertEqual(finished["view"]["state"]["remaining_seconds"], FOCUS_SECONDS)
        self.assertIsNone(finished["view"]["state"]["deadline"])

    def test_reset_restarts_focus_but_keeps_the_session_count(self) -> None:
        state = {
            "phase": "long_break",
            "remaining_seconds": 100,
            "deadline": 100.0,
            "completed_focus_sessions": 4,
        }
        reset = handle_request(request("action", state, "reset"), now=101.0)

        self.assertEqual(reset["view"]["state"]["phase"], "focus")
        self.assertEqual(reset["view"]["state"]["remaining_seconds"], FOCUS_SECONDS)
        self.assertEqual(reset["view"]["state"]["completed_focus_sessions"], 4)
        self.assertIsNone(reset["view"]["state"]["deadline"])

    def test_invalid_request_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            handle_request({"protocol": 2, "id": "wrong", "method": "view"}, now=0)


if __name__ == "__main__":
    unittest.main()
