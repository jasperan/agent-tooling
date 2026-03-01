"""
PDF Tools - Convert PDFs to markdown and summarize PDF content.

Uses pymupdf (fitz) for text extraction and Ollama for LLM-based summarization.
"""

import os
from pathlib import Path
from typing import Optional

from agent_tooling.tools.decorator import tool
from agent_tooling.tools.base import ToolError

try:
    import pymupdf
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

SAMPLES = {
    "pdf_to_markdown": [
        {
            "name": "convert_sample",
            "description": "Convert a sample PDF to markdown (auto-generated)",
            "input": {"path": "__auto_pdf__"},
        },
    ],
    "summarize_pdf": [
        {
            "name": "summarize_sample",
            "description": "Summarize a sample PDF with Ollama",
            "input": {"path": "__auto_pdf__", "max_pages": 1},
            "requires": "ollama",
        },
    ],
}

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

DEFAULT_OLLAMA_MODEL = "qwen3-coder"
# Canonical Ollama base URL — also defined in agents/ollama.py and media/image.py
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


def _validate_pdf_path(path: str, tool_name: str) -> Path:
    """Validate and resolve a PDF file path."""
    file_path = Path(path).expanduser().resolve()

    if not file_path.exists():
        raise ToolError(f"PDF file not found: {path}", tool_name=tool_name)

    if not file_path.is_file():
        raise ToolError(f"Not a file: {path}", tool_name=tool_name)

    if file_path.suffix.lower() != ".pdf":
        raise ToolError(f"Not a PDF file: {path}", tool_name=tool_name)

    return file_path


def _extract_text_as_markdown(file_path: Path, start_page: int = 0, end_page: Optional[int] = None) -> tuple:
    """Extract text from a PDF and convert to markdown.

    Returns:
        Tuple of (markdown_text, total_page_count, pages_processed)
    """
    if not HAS_PYMUPDF:
        raise ToolError(
            "pymupdf is required for PDF processing. Install with: pip install pymupdf",
            tool_name="pdf_to_markdown",
        )

    try:
        doc = pymupdf.open(str(file_path))
    except Exception as e:
        raise ToolError(f"Failed to open PDF: {e}", tool_name="pdf_to_markdown")

    total_pages = len(doc)

    # Resolve page range
    start = max(0, start_page)
    end = min(total_pages, end_page) if end_page is not None else total_pages

    if start >= total_pages:
        doc.close()
        raise ToolError(
            f"start_page ({start_page}) exceeds total pages ({total_pages})",
            tool_name="pdf_to_markdown",
        )

    markdown_parts = []

    for page_num in range(start, end):
        page = doc[page_num]

        # Extract text blocks with position info for structural awareness
        blocks = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE)["blocks"]

        page_lines = []
        for block in blocks:
            if block["type"] != 0:  # Skip image blocks
                continue

            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue

                text = "".join(span["text"] for span in spans).strip()
                if not text:
                    continue

                # Detect headings by font size relative to page average
                max_font_size = max(span["size"] for span in spans)
                is_bold = any(
                    "bold" in span.get("font", "").lower() for span in spans
                )

                if max_font_size >= 18:
                    page_lines.append(f"# {text}")
                elif max_font_size >= 15 or (max_font_size >= 13 and is_bold):
                    page_lines.append(f"## {text}")
                elif is_bold and max_font_size >= 11:
                    page_lines.append(f"### {text}")
                else:
                    page_lines.append(text)

        if page_lines:
            markdown_parts.append(f"<!-- Page {page_num + 1} -->\n\n" + "\n\n".join(page_lines))

    doc.close()

    markdown_text = "\n\n---\n\n".join(markdown_parts)
    pages_processed = end - start

    return markdown_text, total_pages, pages_processed


@tool(name="pdf_to_markdown", category="media", mcp_enabled=True)
def pdf_to_markdown(
    path: str,
    start_page: int = 0,
    end_page: Optional[int] = None,
) -> dict:
    """Convert a PDF file to markdown text.

    Extracts text from a PDF with structural awareness, detecting headings
    based on font size and weight. Returns markdown-formatted text.

    Args:
        path: Path to the PDF file
        start_page: First page to extract (0-indexed, default: 0)
        end_page: Last page to extract (exclusive, default: all pages)

    Returns:
        Dictionary with markdown text, page count, and pages processed
    """
    file_path = _validate_pdf_path(path, "pdf_to_markdown")
    markdown_text, total_pages, pages_processed = _extract_text_as_markdown(
        file_path, start_page, end_page
    )

    return {
        "markdown": markdown_text,
        "page_count": total_pages,
        "pages_processed": pages_processed,
        "source": str(file_path),
    }


@tool(name="summarize_pdf", category="media", mcp_enabled=True)
def summarize_pdf(
    path: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    max_pages: Optional[int] = None,
    prompt: Optional[str] = None,
) -> dict:
    """Summarize a PDF file using an Ollama LLM.

    Extracts text from the PDF and sends it to the configured Ollama model
    for an intelligent summary.

    Args:
        path: Path to the PDF file
        model: Ollama model to use (default: env OLLAMA_MODEL or 'qwen3-coder')
        base_url: Ollama server URL (default: env OLLAMA_BASE_URL or 'http://localhost:11434')
        max_pages: Maximum number of pages to include (default: all pages)
        prompt: Custom summarization prompt (default: standard summarization instruction)

    Returns:
        Dictionary with the summary, model used, page count, and source
    """
    if not HAS_HTTPX:
        raise ToolError(
            "httpx is required for summarize_pdf. Install with: pip install httpx",
            tool_name="summarize_pdf",
        )

    file_path = _validate_pdf_path(path, "summarize_pdf")

    # Extract text
    markdown_text, total_pages, pages_processed = _extract_text_as_markdown(
        file_path, start_page=0, end_page=max_pages
    )

    if not markdown_text.strip():
        raise ToolError("PDF contains no extractable text", tool_name="summarize_pdf")

    # Resolve configuration
    model = model or os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    base_url = base_url or os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)

    # Build summarization prompt
    if prompt is None:
        prompt = (
            "Summarize the following document concisely. "
            "Capture the key points, main arguments, and important details. "
            "Use bullet points for clarity where appropriate."
        )

    full_prompt = f"{prompt}\n\n---\n\n{markdown_text}"

    # Call Ollama generate API
    api_url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
    }

    try:
        with httpx.Client(timeout=180) as client:
            response = client.post(api_url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError:
        raise ToolError(
            f"Cannot connect to Ollama at {base_url}. Is Ollama running?",
            tool_name="summarize_pdf",
        )
    except httpx.TimeoutException:
        raise ToolError(
            "Ollama request timed out. Try reducing max_pages to send less text.",
            tool_name="summarize_pdf",
        )
    except httpx.HTTPStatusError as e:
        raise ToolError(
            f"Ollama API error (HTTP {e.response.status_code}): {e.response.text[:300]}",
            tool_name="summarize_pdf",
        )
    except Exception as e:
        raise ToolError(f"Ollama API request failed: {e}", tool_name="summarize_pdf")

    summary = data.get("response", "")
    if not summary:
        raise ToolError("Ollama returned an empty summary", tool_name="summarize_pdf")

    return {
        "summary": summary,
        "model": model,
        "page_count": total_pages,
        "pages_processed": pages_processed,
        "source": str(file_path),
    }
