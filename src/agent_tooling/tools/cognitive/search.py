"""
Search Tools - Web search and Wikipedia lookup.
"""

from typing import List, Optional
import re
import json

from agent_tooling.tools.decorator import tool
from agent_tooling.tools.base import ToolError

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

SAMPLES = {
    "web_search": [
        {
            "name": "tech_search",
            "description": "Search for a technology topic",
            "input": {"query": "Python MCP protocol", "num_results": 3},
            "requires": "network",
        },
    ],
    "wikipedia_search": [
        {
            "name": "science_lookup",
            "description": "Look up a scientific topic",
            "input": {"query": "Large language model", "sentences": 3},
            "requires": "network",
        },
    ],
}


@tool(name="web_search", category="cognitive", mcp_enabled=True)
def web_search(query: str, num_results: int = 5) -> List[dict]:
    """Search the web for information.

    Args:
        query: Search query
        num_results: Maximum number of results to return (default: 5)

    Returns:
        List of search results with title, url, and snippet
    """
    if not HAS_HTTPX:
        raise ToolError(
            "httpx is required for web search. Install with: pip install httpx",
            tool_name="web_search"
        )

    # Use DuckDuckGo HTML search (no API key required)
    try:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.post(
                url,
                data=params,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AgentTooling/0.1)"
                }
            )
            response.raise_for_status()
            html = response.text

        # Parse results from HTML
        results = []
        pattern = r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'

        for match in re.finditer(pattern, html):
            href, title = match.groups()

            # Extract the actual URL from DuckDuckGo redirect
            url_match = re.search(r'uddg=([^&]+)', href)
            if url_match:
                from urllib.parse import unquote
                actual_url = unquote(url_match.group(1))
            else:
                actual_url = href

            results.append({
                "title": title.strip(),
                "url": actual_url,
            })

            if len(results) >= num_results:
                break

        if not results:
            return [{
                "message": f"No results found for: {query}",
                "query": query,
            }]

        return results

    except httpx.TimeoutException:
        raise ToolError("Search request timed out", tool_name="web_search")
    except Exception as e:
        raise ToolError(str(e), tool_name="web_search")


@tool(name="wikipedia_search", category="cognitive", mcp_enabled=True)
def wikipedia_search(query: str, sentences: int = 3) -> dict:
    """Search Wikipedia and return a summary.

    Args:
        query: Topic to search for
        sentences: Number of sentences in the summary (default: 3)

    Returns:
        Dictionary with title, summary, and URL
    """
    if not HAS_HTTPX:
        raise ToolError(
            "httpx is required for Wikipedia search. Install with: pip install httpx",
            tool_name="wikipedia_search"
        )

    try:
        # Search Wikipedia API
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 1,
        }

        with httpx.Client(timeout=30) as client:
            # First, search for the page
            response = client.get(search_url, params=search_params)
            response.raise_for_status()
            search_data = response.json()

            if not search_data.get("query", {}).get("search"):
                return {
                    "found": False,
                    "query": query,
                    "message": "No Wikipedia article found",
                }

            # Get the page title
            page_title = search_data["query"]["search"][0]["title"]

            # Get the summary
            summary_params = {
                "action": "query",
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "exsentences": sentences,
                "titles": page_title,
                "format": "json",
            }

            response = client.get(search_url, params=summary_params)
            response.raise_for_status()
            summary_data = response.json()

            pages = summary_data.get("query", {}).get("pages", {})
            if not pages:
                return {
                    "found": False,
                    "query": query,
                    "message": "Could not retrieve summary",
                }

            page = list(pages.values())[0]
            page_id = page.get("pageid")

            return {
                "found": True,
                "title": page.get("title", ""),
                "summary": page.get("extract", ""),
                "url": f"https://en.wikipedia.org/?curid={page_id}" if page_id else None,
            }

    except httpx.TimeoutException:
        raise ToolError("Wikipedia request timed out", tool_name="wikipedia_search")
    except Exception as e:
        raise ToolError(str(e), tool_name="wikipedia_search")
