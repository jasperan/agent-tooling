"""
Web Scraping Tools - Extract content from web pages.
"""

from typing import Optional
import re

from agent_tooling.tools.decorator import tool
from agent_tooling.tools.base import ToolError

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


def _extract_text(html: str) -> str:
    """Extract readable text from HTML."""
    # Remove script and style elements
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)

    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return text


def _extract_links(html: str, base_url: str = "") -> list:
    """Extract links from HTML."""
    links = []
    pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'

    for match in re.finditer(pattern, html, re.IGNORECASE):
        href, text = match.groups()
        text = text.strip()

        # Make relative URLs absolute
        if href.startswith("/") and base_url:
            href = base_url.rstrip("/") + href

        links.append({"url": href, "text": text})

    return links


@tool(name="scrape_webpage", category="data", mcp_enabled=True)
def scrape_webpage(
    url: str,
    extract_links: bool = False,
    timeout: int = 30,
) -> dict:
    """Scrape content from a webpage.

    Args:
        url: URL of the webpage to scrape
        extract_links: Whether to extract links from the page (default: false)
        timeout: Request timeout in seconds (default: 30)

    Returns:
        Dictionary with page title, text content, and optionally links
    """
    if not HAS_HTTPX:
        raise ToolError(
            "httpx is required for web scraping. Install with: pip install httpx",
            tool_name="scrape_webpage"
        )

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AgentTooling/0.1; +https://github.com/jasperan/agent-tooling)"
                }
            )
            response.raise_for_status()
            html = response.text

        # Extract title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""

        # Extract text content
        text = _extract_text(html)

        result = {
            "url": str(response.url),
            "title": title,
            "text": text[:10000],  # Limit text length
            "text_length": len(text),
            "status_code": response.status_code,
        }

        if extract_links:
            base_url = f"{response.url.scheme}://{response.url.host}"
            result["links"] = _extract_links(html, base_url)[:50]  # Limit links

        return result

    except httpx.TimeoutException:
        raise ToolError(f"Request timed out after {timeout}s", tool_name="scrape_webpage")
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP {e.response.status_code}", tool_name="scrape_webpage")
    except Exception as e:
        raise ToolError(str(e), tool_name="scrape_webpage")
