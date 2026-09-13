"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return (
            "[Mock Chatbot Response]: Tôi có thể giới thiệu phạm vi hỗ trợ VinBus, "
            "nhưng Chatbot Baseline không tra cứu tuyến hoặc đăng ký vé tháng."
        )

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        prompt_lower = prompt.lower()

        if "mcp observation" in prompt_lower:
            observation = self._extract_observation(prompt)
            if observation.get("registration_id"):
                return {
                    "type": "text",
                    "content": (
                        "Đã tạo đăng ký vé tháng giả lập thành công"
                        f" (mã: {observation['registration_id']}). "
                        "Không có thanh toán hoặc vé thật được phát hành."
                    ),
                    "thought": "Observation đã có mã đăng ký; có thể trả lời cuối cùng.",
                }

            if observation.get("status") != "SUCCESS":
                return {
                    "type": "text",
                    "content": observation.get(
                        "message",
                        "Không thể hoàn tất yêu cầu vì Tool không trả về kết quả thành công.",
                    ),
                    "thought": "Observation là lỗi nên không gọi Tool tiếp.",
                }

            recommended_route_code = observation.get("recommended_route_code")
            if recommended_route_code and "đăng ký" in prompt_lower:
                return {
                    "type": "tool_call",
                    "tool_name": "monthly_pass_register",
                    "arguments": self._monthly_pass_arguments(prompt, recommended_route_code),
                    "thought": "Đã có tuyến được đề xuất; tiến hành đăng ký vé tháng giả lập.",
                }

            route = observation.get("data", {})
            return {
                "type": "text",
                "content": (
                    f"Tuyến {route.get('route_code', 'được yêu cầu')}: {route.get('name', '')}. "
                    f"Khung giờ mock {route.get('service_window', 'không có')}; "
                    f"tần suất khoảng {route.get('typical_frequency_minutes', 'không có')} phút/lượt. "
                    "Thông tin này chỉ phục vụ lab, không phải dữ liệu vận hành thời gian thực."
                ),
                "thought": "Observation tra tuyến đã đủ để trả lời.",
            }

        route_code = self._extract_route_code(prompt)
        if "đăng ký" in prompt_lower and route_code:
            return {
                "type": "tool_call",
                "tool_name": "monthly_pass_register",
                "arguments": self._monthly_pass_arguments(prompt, route_code),
                "thought": "Người dùng yêu cầu đăng ký vé tháng cho mã tuyến đã nêu.",
            }

        if "bến xe mỹ đình" in prompt_lower and "ocean park" in prompt_lower:
            return {
                "type": "tool_call",
                "tool_name": "route_lookup",
                "arguments": {"origin": "Bến xe Mỹ Đình", "destination": "Ocean Park"},
                "thought": "Cần tra tuyến phù hợp từ Bến xe Mỹ Đình đến Ocean Park.",
            }

        if route_code and ("tra cứu" in prompt_lower or "tuyến" in prompt_lower):
            return {
                "type": "tool_call",
                "tool_name": "route_lookup",
                "arguments": {"route_code": route_code},
                "thought": "Người dùng cần tra cứu thông tin của một tuyến cụ thể.",
            }

        return {
            "type": "text",
            "content": "Tôi hỗ trợ tra cứu tuyến VinBus trong mock data và tạo đăng ký vé tháng giả lập cho các tuyến E được hỗ trợ.",
            "thought": "Câu hỏi giới thiệu không cần gọi Tool.",
        }

    @staticmethod
    def _extract_route_code(prompt: str) -> str:
        match = re.search(r"\b(?:E|OCP|OCT)\s*\d{1,2}\b", prompt, flags=re.IGNORECASE)
        return re.sub(r"\s+", "", match.group(0)).upper() if match else ""

    @staticmethod
    def _extract_observation(prompt: str) -> Dict[str, Any]:
        marker = "MCP Observation sau khi gọi "
        if marker not in prompt:
            return {}
        observation_section = prompt.split(marker, 1)[1]
        observation_text = observation_section.split(":\n", 1)[1].split(
            "\n\nDựa hoàn toàn", 1
        )[0]
        try:
            return json.loads(observation_text)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _monthly_pass_arguments(prompt: str, route_code: str) -> Dict[str, Any]:
        name_match = re.search(r"cho tôi:\s*([^,]+),", prompt, flags=re.IGNORECASE)
        if not name_match:
            name_match = re.search(r"tôi là\s+([^,]+),", prompt, flags=re.IGNORECASE)
        phone_match = re.search(r"\b0\d{9,10}\b", prompt)
        date_match = re.search(r"\b\d{2}/\d{2}/\d{4}\b", prompt)
        passenger_type = "priority_hs_sv_or_worker" if "ưu tiên" in prompt.lower() else "regular"
        return {
            "passenger_name": name_match.group(1).strip() if name_match else "Khách hàng mock",
            "phone_number": phone_match.group(0) if phone_match else "0900000000",
            "route_code": route_code,
            "effective_date": date_match.group(0) if date_match else "01/10/2026",
            "passenger_type": passenger_type,
        }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
