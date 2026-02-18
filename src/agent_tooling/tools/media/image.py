"""
Image Analysis Tool - Analyze images using Ollama vision models (llava).

Supports both local file paths and image URLs.
"""

import base64
import os
from pathlib import Path
from typing import Optional

from agent_tooling.tools.decorator import tool
from agent_tooling.tools.base import ToolError

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

SAMPLES = {
    "analyze_image": [
        {
            "name": "describe_url",
            "description": "Analyze an image from a URL",
            "input": {"source": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/300px-PNG_transparency_demonstration_1.png"},
            "requires": "ollama",
        },
    ],
}


# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

DEFAULT_VISION_MODEL = "llava"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


def _is_url(source: str) -> bool:
    """Check if a source string is a URL."""
    return source.startswith("http://") or source.startswith("https://")


def _download_image(url: str, timeout: int = 30) -> bytes:
    """Download an image from a URL and return raw bytes."""
    if not HAS_HTTPX:
        raise ToolError(
            "httpx is required to download images. Install with: pip install httpx",
            tool_name="analyze_image",
        )

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AgentTooling/0.1)"},
            )
            response.raise_for_status()
            return response.content
    except httpx.TimeoutException:
        raise ToolError(f"Image download timed out after {timeout}s: {url}", tool_name="analyze_image")
    except httpx.HTTPStatusError as e:
        raise ToolError(
            f"Failed to download image (HTTP {e.response.status_code}): {url}",
            tool_name="analyze_image",
        )
    except Exception as e:
        raise ToolError(f"Failed to download image: {e}", tool_name="analyze_image")


def _read_image_file(path: str) -> bytes:
    """Read an image file from disk and return raw bytes."""
    file_path = Path(path).expanduser().resolve()

    if not file_path.exists():
        raise ToolError(f"Image file not found: {path}", tool_name="analyze_image")

    if not file_path.is_file():
        raise ToolError(f"Not a file: {path}", tool_name="analyze_image")

    if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ToolError(
            f"Unsupported image format '{file_path.suffix}'. "
            f"Supported: {', '.join(sorted(IMAGE_EXTENSIONS))}",
            tool_name="analyze_image",
        )

    try:
        return file_path.read_bytes()
    except Exception as e:
        raise ToolError(f"Failed to read image file: {e}", tool_name="analyze_image")


@tool(name="analyze_image", category="media", mcp_enabled=True)
def analyze_image(
    source: str,
    prompt: str = "Describe this image in detail.",
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> dict:
    """Analyze an image using an Ollama vision model (e.g. llava).

    Accepts a local file path or an image URL. The image is sent to the
    Ollama vision model which returns a text description/analysis.

    Args:
        source: Path to a local image file or an image URL
        prompt: Question or instruction for the vision model (default: describe the image)
        model: Ollama vision model to use (default: env OLLAMA_VISION_MODEL or 'llava')
        base_url: Ollama server URL (default: env OLLAMA_BASE_URL or 'http://localhost:11434')

    Returns:
        Dictionary with the model's description, model name, and source
    """
    if not HAS_HTTPX:
        raise ToolError(
            "httpx is required for analyze_image. Install with: pip install httpx",
            tool_name="analyze_image",
        )

    # Resolve configuration
    model = model or os.environ.get("OLLAMA_VISION_MODEL", DEFAULT_VISION_MODEL)
    base_url = base_url or os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)

    # Load image bytes
    if _is_url(source):
        image_bytes = _download_image(source)
    else:
        image_bytes = _read_image_file(source)

    # Encode to base64
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # Call Ollama chat API with image
    api_url = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }
        ],
        "stream": False,
    }

    try:
        with httpx.Client(timeout=120) as client:
            response = client.post(api_url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError:
        raise ToolError(
            f"Cannot connect to Ollama at {base_url}. Is Ollama running?",
            tool_name="analyze_image",
        )
    except httpx.TimeoutException:
        raise ToolError(
            "Ollama request timed out. The image may be too large or the model too slow.",
            tool_name="analyze_image",
        )
    except httpx.HTTPStatusError as e:
        raise ToolError(
            f"Ollama API error (HTTP {e.response.status_code}): {e.response.text[:300]}",
            tool_name="analyze_image",
        )
    except Exception as e:
        raise ToolError(f"Ollama API request failed: {e}", tool_name="analyze_image")

    description = data.get("message", {}).get("content", "")
    if not description:
        raise ToolError("Ollama returned an empty response", tool_name="analyze_image")

    return {
        "description": description,
        "model": model,
        "source": source,
        "prompt": prompt,
    }
