"""VinBus tool schemas and offline execution backend for the ReAct lab."""

import json
import re
import unicodedata
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


TOOLS_SCHEMA = [
    {
        "name": "route_lookup",
        "description": (
            "Tra cứu tuyến VinBus trong dữ liệu giả lập. Cung cấp route_code khi đã "
            "biết mã tuyến; nếu chưa biết, cung cấp cả origin và destination để nhận "
            "tuyến được đề xuất. Dữ liệu chỉ là snapshot offline, không phải lịch chạy thực tế."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "route_code": {
                    "type": "string",
                    "description": "Mã tuyến, ví dụ: E01, E05, OCP1 hoặc OCT1.",
                },
                "origin": {
                    "type": "string",
                    "description": "Điểm đi khi chưa biết mã tuyến, ví dụ: 'Bến xe Mỹ Đình'.",
                },
                "destination": {
                    "type": "string",
                    "description": "Điểm đến khi chưa biết mã tuyến, ví dụ: 'Ocean Park'.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "monthly_pass_register",
        "description": (
            "Tạo đăng ký vé tháng VinBus GIẢ LẬP cho các tuyến E được hỗ trợ. "
            "Tool không thu thập thông tin thanh toán, không thu tiền và không phát hành vé thật."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "passenger_name": {
                    "type": "string",
                    "description": "Họ tên hành khách đăng ký.",
                },
                "phone_number": {
                    "type": "string",
                    "description": "Số điện thoại liên hệ của hành khách.",
                },
                "route_code": {
                    "type": "string",
                    "description": "Mã tuyến E cần đăng ký, ví dụ: E01, E02, E03 hoặc E05.",
                },
                "effective_date": {
                    "type": "string",
                    "description": "Ngày hiệu lực theo YYYY-MM-DD hoặc DD/MM/YYYY.",
                },
                "passenger_type": {
                    "type": "string",
                    "enum": ["regular", "priority_hs_sv_or_worker", "group_30_or_more"],
                    "description": "Loại hành khách; mặc định là regular nếu không cung cấp.",
                },
            },
            "required": ["passenger_name", "phone_number", "route_code", "effective_date"],
            "additionalProperties": False,
        },
    },
]


@lru_cache(maxsize=1)
def _load_mock_data() -> Dict[str, Any]:
    """Load the checked-in offline snapshot once per process."""
    data_path = Path(__file__).resolve().parents[1] / "config" / "mock_vinbus_data.json"
    with data_path.open(encoding="utf-8") as data_file:
        return json.load(data_file)


def _normalise(value: str) -> str:
    """Make Vietnamese text comparable without changing displayed data."""
    decomposed = unicodedata.normalize("NFD", value.strip().lower())
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", without_marks.replace("đ", "d"))


def _json_response(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _find_route(route_code: str) -> Optional[Dict[str, Any]]:
    wanted_code = route_code.strip().upper()
    for route in _load_mock_data()["routes"]:
        if route["route_code"].upper() == wanted_code:
            return route
    return None


def _route_match_score(route: Dict[str, Any], origin: str, destination: str) -> int:
    """Score a route by matching both endpoints, prioritising route names."""
    fields: List[Tuple[str, int]] = [
        (route["name"], 3),
        (route["route_summary"], 2),
        (" ".join(route["key_stops"]), 1),
    ]
    score = 0
    for location in (origin, destination):
        normalised_location = _normalise(location)
        if not normalised_location:
            return 0
        location_score = max(
            (
                weight
                for field, weight in fields
                if normalised_location in _normalise(field)
            ),
            default=0,
        )
        if not location_score:
            return 0
        score += location_score
    return score


def execute_route_lookup(
    route_code: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
) -> str:
    """Return an offline route by code or recommend one from two endpoints."""
    if route_code and route_code.strip():
        route = _find_route(route_code)
        if route:
            return _json_response({"status": "SUCCESS", "data": route})
        return _json_response(
            {
                "status": "NOT_FOUND",
                "message": f"Không tìm thấy tuyến '{route_code.strip().upper()}' trong mock data.",
            }
        )

    if not (origin and origin.strip() and destination and destination.strip()):
        return _json_response(
            {
                "status": "INVALID_INPUT",
                "message": "Cần cung cấp route_code hoặc đồng thời origin và destination.",
            }
        )

    matches = [
        (route, _route_match_score(route, origin, destination))
        for route in _load_mock_data()["routes"]
    ]
    matches = [match for match in matches if match[1] > 0]
    if not matches:
        return _json_response(
            {
                "status": "NOT_FOUND",
                "message": "Không tìm thấy tuyến phù hợp với điểm đi và điểm đến trong mock data.",
            }
        )

    matches.sort(key=lambda match: match[1], reverse=True)
    recommended_route, _ = matches[0]
    return _json_response(
        {
            "status": "SUCCESS",
            "origin": origin.strip(),
            "destination": destination.strip(),
            "recommended_route_code": recommended_route["route_code"],
            "data": recommended_route,
            "alternative_route_codes": [route["route_code"] for route, _ in matches[1:]],
        }
    )


def _parse_effective_date(effective_date: str) -> Optional[str]:
    for date_format in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(effective_date.strip(), date_format).date().isoformat()
        except ValueError:
            continue
    return None


def execute_monthly_pass_register(
    passenger_name: str,
    phone_number: str,
    route_code: str,
    effective_date: str,
    passenger_type: str = "regular",
) -> str:
    """Create a deterministic, non-payment mock monthly-pass registration."""
    if not passenger_name or not passenger_name.strip():
        return _json_response({"status": "INVALID_INPUT", "message": "Thiếu passenger_name."})

    digits_only = re.sub(r"\D", "", phone_number or "")
    if not 9 <= len(digits_only) <= 11:
        return _json_response(
            {"status": "INVALID_INPUT", "message": "phone_number phải có từ 9 đến 11 chữ số."}
        )

    parsed_effective_date = _parse_effective_date(effective_date or "")
    if not parsed_effective_date:
        return _json_response(
            {
                "status": "INVALID_INPUT",
                "message": "effective_date phải theo YYYY-MM-DD hoặc DD/MM/YYYY.",
            }
        )

    route = _find_route(route_code or "")
    if not route:
        return _json_response(
            {
                "status": "NOT_FOUND",
                "message": f"Không tìm thấy tuyến '{(route_code or '').strip().upper()}' trong mock data.",
            }
        )

    registration_config = _load_mock_data()["monthly_pass_registration"]
    if route["route_code"] not in registration_config["supported_route_codes"]:
        return _json_response(
            {
                "status": "NOT_ELIGIBLE",
                "message": (
                    f"Tuyến {route['route_code']} không hỗ trợ đăng ký vé tháng trong mock data. "
                    "Các tuyến OCP/OCT được mô phỏng là miễn phí."
                ),
            }
        )

    option = next(
        (
            candidate
            for candidate in registration_config["monthly_pass_options"]
            if candidate["passenger_type"] == passenger_type
        ),
        None,
    )
    if not option:
        return _json_response(
            {
                "status": "INVALID_INPUT",
                "message": "passenger_type không hợp lệ.",
            }
        )

    registration_id = (
        f"SIM-PASS-{route['route_code']}-{parsed_effective_date.replace('-', '')}-{digits_only[-4:]}"
    )
    return _json_response(
        {
            "status": "SUCCESS",
            "registration_id": registration_id,
            "passenger_name": passenger_name.strip(),
            "route_code": route["route_code"],
            "effective_date": parsed_effective_date,
            "passenger_type": passenger_type,
            "monthly_pass_price_vnd": option["mock_price_vnd"],
            "simulated_only": True,
            "message": "Đã tạo đăng ký vé tháng giả lập; không có giao dịch thanh toán hoặc vé thật được phát hành.",
        }
    )


TOOL_ROUTER = {
    "route_lookup": execute_route_lookup,
    "monthly_pass_register": execute_monthly_pass_register,
}


def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Route an MCP tool call and serialise input/execution errors."""
    if tool_name not in TOOL_ROUTER:
        return _json_response(
            {"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại."}
        )
    try:
        return TOOL_ROUTER[tool_name](**arguments)
    except TypeError as error:
        return _json_response({"status": "INVALID_INPUT", "error": str(error)})
    except Exception as error:
        return _json_response({"status": "EXECUTION_ERROR", "error": str(error)})
