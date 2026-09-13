import unittest

from src.mcp_server import MCPAcademicServer


class MCPServerTests(unittest.TestCase):
    def setUp(self):
        self.server = MCPAcademicServer()

    def test_call_tool_wraps_route_result_as_json_rpc_observation(self):
        response = self.server.call_tool("route_lookup", {"route_code": "E05"})

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["server"], self.server.server_name)
        self.assertEqual(response["tool"], "route_lookup")
        self.assertEqual(response["result"]["status"], "SUCCESS")
        self.assertEqual(response["result"]["data"]["route_code"], "E05")

    def test_call_tool_returns_unknown_tool_observation(self):
        response = self.server.call_tool("unsupported_tool", {})

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["result"]["status"], "UNKNOWN_TOOL")

    def test_call_tool_returns_invalid_input_observation(self):
        response = self.server.call_tool("monthly_pass_register", {"route_code": "E05"})

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["result"]["status"], "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
