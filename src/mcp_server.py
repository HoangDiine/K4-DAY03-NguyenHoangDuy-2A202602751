"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Mô phỏng kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa.
"""

import json
import sys
from typing import Any, Dict, List

try:
    from .tools import TOOLS_SCHEMA, dispatch_tool_call
except ImportError:  # Allows `python src/mcp_server.py` as documented in the lab.
    from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MCPAcademicServer:
    """
    Giả lập MCP Server tuân thủ chuẩn giao thức Model Context Protocol
    """
    def __init__(self, server_name: str = "vinbus-customer-service-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        [TASK 2.1] HỌC VIÊN HOÀN THIỆN HÀM THỰC THI TOOL TRÊN MCP SERVER
        Thực thi request gọi Tool theo chuẩn MCP JSON-RPC
        """
        if not isinstance(tool_name, str) or not tool_name.strip():
            result = {
                "status": "INVALID_INPUT",
                "message": "tool_name phải là chuỗi không rỗng.",
            }
        elif not isinstance(arguments, dict):
            result = {
                "status": "INVALID_INPUT",
                "message": "arguments phải là một JSON object.",
            }
        else:
            raw_result = dispatch_tool_call(tool_name, arguments)
            try:
                result = json.loads(raw_result)
            except json.JSONDecodeError:
                result = {
                    "status": "EXECUTION_ERROR",
                    "message": "Tool trả về dữ liệu không phải JSON hợp lệ.",
                }

        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": result,
        }


if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER (VinBus)")
    print("==========================================================")
    
    server = MCPAcademicServer()
    tools = server.list_tools()
    print(f"✅ Khởi tạo thành công MCP Server: {server.server_name} (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố: {len(tools)}")
    
    print(f"🛠️ Tools: {', '.join(tool['name'] for tool in tools)}")

    test_result = server.call_tool("route_lookup", {"route_code": "E05"})
    print("✅ [TASK 2.1]: MCP dispatch 'route_lookup' thành công:")
    print(f"   Phản hồi JSON-RPC: {json.dumps(test_result, ensure_ascii=False)}")
