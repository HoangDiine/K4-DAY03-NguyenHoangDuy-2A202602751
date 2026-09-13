import os
import unittest
from unittest.mock import patch

from src.providers import (
    GeminiProvider,
    gemini_live_error_response,
    to_gemini_parameters,
)


class GeminiProviderTests(unittest.TestCase):
    def test_uses_current_default_model_when_env_model_is_empty(self):
        with patch.dict(os.environ, {"LLM_MODEL": ""}):
            provider = GeminiProvider(api_key="test-key")

        self.assertEqual(provider.model_name, "gemini-3.6-flash")

    def test_removes_additional_properties_from_gemini_function_schema(self):
        parameters = {
            "type": "object",
            "properties": {
                "route_code": {
                    "type": "string",
                    "additionalProperties": False,
                }
            },
            "additionalProperties": False,
        }

        sanitized = to_gemini_parameters(parameters)

        self.assertNotIn("additionalProperties", sanitized)
        self.assertNotIn(
            "additionalProperties", sanitized["properties"]["route_code"]
        )
        self.assertEqual(sanitized["properties"]["route_code"]["type"], "string")

    def test_live_api_error_does_not_masquerade_as_mock_response(self):
        result = gemini_live_error_response(RuntimeError("quota exhausted"))

        self.assertEqual(result["type"], "text")
        self.assertIn("Gemini", result["content"])
        self.assertIn("không chuyển sang Mock", result["content"])
        self.assertNotIn("Offline-Mock-Model-2026", result["content"])


if __name__ == "__main__":
    unittest.main()
