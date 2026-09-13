import unittest

from src.app import load_test_cases, run_react_agent
from src.mcp_server import MCPAcademicServer
from src.providers import MockOfflineProvider


class ScriptedProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate_with_tools(self, prompt, tools_schema, system_prompt=""):
        self.prompts.append(prompt)
        return self.responses.pop(0)


class ReActAgentTests(unittest.TestCase):
    def test_react_loop_uses_observation_to_make_a_second_tool_call(self):
        provider = ScriptedProvider(
            [
                {
                    "type": "tool_call",
                    "tool_name": "route_lookup",
                    "arguments": {
                        "origin": "Bến xe Mỹ Đình",
                        "destination": "Ocean Park",
                    },
                    "thought": "Cần tra tuyến trước khi đăng ký.",
                },
                {
                    "type": "tool_call",
                    "tool_name": "monthly_pass_register",
                    "arguments": {
                        "passenger_name": "Trần Gia Huy",
                        "phone_number": "0987654321",
                        "route_code": "E01",
                        "effective_date": "01/10/2026",
                        "passenger_type": "regular",
                    },
                    "thought": "Observation cho thấy E01 hỗ trợ vé tháng mock.",
                },
                {
                    "type": "text",
                    "content": "Đã tạo đăng ký giả lập cho tuyến E01.",
                    "thought": "Đã có đủ dữ liệu để trả lời.",
                },
            ]
        )

        traces = run_react_agent(
            "Tìm tuyến từ Bến xe Mỹ Đình đến Ocean Park rồi đăng ký vé tháng.",
            provider,
            MCPAcademicServer(),
        )

        self.assertEqual([trace["action_type"] for trace in traces], [
            "TOOL_EXECUTION",
            "TOOL_EXECUTION",
            "FINAL_ANSWER",
        ])
        self.assertEqual(traces[0]["observation"]["status"], "SUCCESS")
        self.assertEqual(traces[1]["observation"]["status"], "SUCCESS")
        self.assertEqual(traces[2]["output"], "Đã tạo đăng ký giả lập cho tuyến E01.")
        self.assertEqual(len(provider.prompts), 3)
        self.assertIn("recommended_route_code", provider.prompts[1])
        self.assertIn("registration_id", provider.prompts[2])

    def test_react_loop_returns_direct_llm_answer_without_tool(self):
        provider = ScriptedProvider(
            [
                {
                    "type": "text",
                    "content": "Tôi có thể tra tuyến và tạo đăng ký vé tháng giả lập.",
                    "thought": "Câu hỏi giới thiệu không cần Tool.",
                }
            ]
        )

        traces = run_react_agent("Bạn hỗ trợ những gì?", provider, MCPAcademicServer())

        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]["action_type"], "FINAL_ANSWER")

    def test_offline_provider_completes_vinbus_lookup_then_registration(self):
        traces = run_react_agent(
            (
                "Tôi đi từ Bến xe Mỹ Đình đến Ocean Park hằng ngày. "
                "Hãy tìm tuyến phù hợp, rồi đăng ký vé tháng giả lập loại phổ thông "
                "cho tôi: Trần Gia Huy, 0987654321, hiệu lực từ 01/10/2026."
            ),
            MockOfflineProvider(),
            MCPAcademicServer(),
        )

        self.assertEqual([trace["action_type"] for trace in traces], [
            "TOOL_EXECUTION",
            "TOOL_EXECUTION",
            "FINAL_ANSWER",
        ])
        self.assertEqual(traces[0]["tool_name"], "route_lookup")
        self.assertEqual(traces[1]["tool_name"], "monthly_pass_register")
        self.assertIn("SIM-PASS-E01", traces[2]["output"])

    def test_offline_provider_finishes_each_configured_test_case(self):
        expected_first_actions = {
            "TC01": "FINAL_ANSWER",
            "TC02": "TOOL_EXECUTION",
            "TC03": "TOOL_EXECUTION",
            "TC04": "TOOL_EXECUTION",
            "TC05": "TOOL_EXECUTION",
        }

        for test_case in load_test_cases():
            with self.subTest(test_case=test_case["id"]):
                traces = run_react_agent(
                    test_case["question"],
                    MockOfflineProvider(),
                    MCPAcademicServer(),
                )

                self.assertEqual(traces[0]["action_type"], expected_first_actions[test_case["id"]])
                self.assertEqual(traces[-1]["action_type"], "FINAL_ANSWER")
                if test_case["id"] == "TC02":
                    self.assertIn("Royal City", traces[-1]["output"])
                    self.assertIn("06:00-23:59", traces[-1]["output"])
                if test_case["id"] == "TC05":
                    self.assertIn("E99", traces[-1]["output"])


if __name__ == "__main__":
    unittest.main()
