import json
import unittest

from src.tools import (
    TOOLS_SCHEMA,
    dispatch_tool_call,
    execute_monthly_pass_register,
    execute_route_lookup,
)


class VinBusToolTests(unittest.TestCase):
    def test_tool_schemas_expose_route_lookup_and_monthly_pass_registration(self):
        schemas = {tool["name"]: tool["parameters"] for tool in TOOLS_SCHEMA}

        self.assertEqual(set(schemas), {"route_lookup", "monthly_pass_register"})
        self.assertIn("route_code", schemas["route_lookup"]["properties"])
        self.assertEqual(
            schemas["monthly_pass_register"]["required"],
            ["passenger_name", "phone_number", "route_code", "effective_date"],
        )

    def test_route_lookup_returns_billable_e05_route(self):
        result = json.loads(execute_route_lookup(route_code="E05"))

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["data"]["route_code"], "E05")
        self.assertTrue(result["data"]["fare_payment_required"])
        self.assertEqual(result["data"]["mock_fare_vnd"], 10000)

    def test_route_lookup_recommends_e01_for_my_dinh_to_ocean_park(self):
        result = json.loads(
            execute_route_lookup(
                origin="Bến xe Mỹ Đình",
                destination="Ocean Park",
            )
        )

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["recommended_route_code"], "E01")

    def test_route_lookup_returns_not_found_for_unknown_route(self):
        result = json.loads(execute_route_lookup(route_code="E99"))

        self.assertEqual(result["status"], "NOT_FOUND")

    def test_monthly_pass_registers_supported_e_route_without_payment(self):
        result = json.loads(
            execute_monthly_pass_register(
                passenger_name="Nguyễn Minh Anh",
                phone_number="0901234567",
                route_code="E05",
                effective_date="01/10/2026",
                passenger_type="regular",
            )
        )

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["route_code"], "E05")
        self.assertEqual(result["monthly_pass_price_vnd"], 140000)
        self.assertTrue(result["registration_id"].startswith("SIM-PASS-E05-"))
        self.assertTrue(result["simulated_only"])

    def test_monthly_pass_rejects_free_ocp_route(self):
        result = json.loads(
            execute_monthly_pass_register(
                passenger_name="Nguyễn Minh Anh",
                phone_number="0901234567",
                route_code="OCP2",
                effective_date="2026-10-01",
            )
        )

        self.assertEqual(result["status"], "NOT_ELIGIBLE")

    def test_dispatch_returns_unknown_tool_for_unsupported_name(self):
        result = json.loads(dispatch_tool_call("unsupported_tool", {}))

        self.assertEqual(result["status"], "UNKNOWN_TOOL")


if __name__ == "__main__":
    unittest.main()
