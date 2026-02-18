"""
API Tools - Make HTTP requests to REST APIs.
"""

from typing import Any, Dict, Optional
import json

from agent_tooling.tools.decorator import tool
from agent_tooling.tools.base import ToolError

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

SAMPLES = {
    "call_api": [
        {
            "name": "get_ip",
            "description": "Fetch public IP information",
            "input": {"url": "https://httpbin.org/ip", "method": "GET"},
            "requires": "network",
        },
    ],
    "fetch_json": [
        {
            "name": "fetch_uuid",
            "description": "Fetch a random UUID from httpbin",
            "input": {"url": "https://httpbin.org/uuid"},
            "requires": "network",
        },
    ],
}


@tool(name="call_api", category="data", mcp_enabled=True)
def call_api(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> dict:
    """Make an HTTP API request.

    Args:
        url: The URL to request
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        headers: Optional request headers
        body: Optional request body (for POST, PUT, etc.)
        timeout: Request timeout in seconds (default: 30)

    Returns:
        Dictionary with status code, headers, and response body
    """
    if not HAS_HTTPX:
        raise ToolError(
            "httpx is required for API calls. Install with: pip install httpx",
            tool_name="call_api"
        )

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=body if body else None,
            )

            # Try to parse JSON response
            try:
                response_body = response.json()
            except json.JSONDecodeError:
                response_body = response.text

            return {
                "success": response.is_success,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
            }

    except httpx.TimeoutException:
        raise ToolError(f"Request timed out after {timeout}s", tool_name="call_api")
    except httpx.RequestError as e:
        raise ToolError(str(e), tool_name="call_api")


@tool(name="fetch_json", category="data", mcp_enabled=True)
def fetch_json(url: str, timeout: int = 30) -> Any:
    """Fetch JSON data from a URL.

    Args:
        url: The URL to fetch JSON from
        timeout: Request timeout in seconds (default: 30)

    Returns:
        Parsed JSON data
    """
    if not HAS_HTTPX:
        raise ToolError(
            "httpx is required for API calls. Install with: pip install httpx",
            tool_name="fetch_json"
        )

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        raise ToolError(f"Request timed out after {timeout}s", tool_name="fetch_json")
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP {e.response.status_code}: {e.response.text[:200]}", tool_name="fetch_json")
    except json.JSONDecodeError:
        raise ToolError("Response is not valid JSON", tool_name="fetch_json")
    except Exception as e:
        raise ToolError(str(e), tool_name="fetch_json")
