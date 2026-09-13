import unittest

from src.web_server import MAX_MESSAGE_CHARS, run_agent_request, validate_chat_message


class WebServerTests(unittest.TestCase):
    def test_validate_chat_message_rejects_empty_and_oversized_inputs(self):
        with self.assertRaisesRegex(ValueError, "không được để trống"):
            validate_chat_message("   ")

        with self.assertRaisesRegex(ValueError, "quá dài"):
            validate_chat_message("x" * (MAX_MESSAGE_CHARS + 1))

    def test_run_agent_request_returns_final_answer_and_safe_trace_summary(self):
        def fake_runner(message, provider, mcp_server):
            self.assertEqual(message, "Tra cứu E01")
            return [
                {
                    "step": 1,
                    "action_type": "TOOL_EXECUTION",
                    "tool_name": "route_lookup",
                    "observation": {"status": "SUCCESS"},
                },
                {
                    "step": 2,
                    "action_type": "FINAL_ANSWER",
                    "output": "Tuyến E01 đang có trong dữ liệu giả lập.",
                },
            ]

        result = run_agent_request(
            "Tra cứu E01",
            provider=object(),
            mcp_server=object(),
            agent_runner=fake_runner,
        )

        self.assertEqual(
            result["answer"], "Tuyến E01 đang có trong dữ liệu giả lập."
        )
        self.assertEqual(
            result["trace"],
            [
                {
                    "step": 1,
                    "action_type": "TOOL_EXECUTION",
                    "tool_name": "route_lookup",
                    "status": "SUCCESS",
                },
                {"step": 2, "action_type": "FINAL_ANSWER"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
