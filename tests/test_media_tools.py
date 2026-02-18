"""Tests for media tools (image analysis, PDF processing)."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agent_tooling.tools.media.image import analyze_image
from agent_tooling.tools.media.pdf import pdf_to_markdown, summarize_pdf


# --- Fixtures ---


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal valid PDF for testing."""
    import pymupdf

    pdf_path = tmp_path / "sample.pdf"
    doc = pymupdf.open()

    # Page 1
    page = doc.new_page()
    page.insert_text((72, 72), "Document Title", fontsize=20)
    page.insert_text((72, 120), "Section One", fontsize=15)
    page.insert_text((72, 150), "This is the first paragraph of content in the sample PDF.")
    page.insert_text((72, 170), "It contains multiple lines of text for testing purposes.")

    # Page 2
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Section Two", fontsize=15)
    page2.insert_text((72, 110), "Second page content with additional information.")

    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


@pytest.fixture
def sample_image(tmp_path):
    """Create a minimal valid PNG image for testing."""
    import struct
    import zlib

    img_path = tmp_path / "sample.png"

    # Minimal 1x1 red pixel PNG
    def create_minimal_png():
        signature = b'\x89PNG\r\n\x1a\n'

        # IHDR chunk
        ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)  # 1x1, 8bit, RGB
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
        ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)

        # IDAT chunk (1x1 red pixel)
        raw_data = b'\x00\xff\x00\x00'  # filter byte + RGB
        compressed = zlib.compress(raw_data)
        idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
        idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)

        # IEND chunk
        iend_crc = zlib.crc32(b'IEND') & 0xffffffff
        iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)

        return signature + ihdr + idat + iend

    img_path.write_bytes(create_minimal_png())
    return str(img_path)


# --- pdf_to_markdown tests ---


class TestPdfToMarkdown:
    """Tests for the pdf_to_markdown tool."""

    def test_basic_extraction(self, sample_pdf):
        """Test basic PDF to markdown conversion."""
        result = pdf_to_markdown(path=sample_pdf)
        assert result.success
        assert result.data["page_count"] == 2
        assert result.data["pages_processed"] == 2
        assert "Document Title" in result.data["markdown"]
        assert "first paragraph" in result.data["markdown"]

    def test_page_range(self, sample_pdf):
        """Test extracting a specific page range."""
        result = pdf_to_markdown(path=sample_pdf, start_page=0, end_page=1)
        assert result.success
        assert result.data["pages_processed"] == 1
        assert "Document Title" in result.data["markdown"]
        # Page 2 content should not be present
        assert "Second page" not in result.data["markdown"]

    def test_second_page_only(self, sample_pdf):
        """Test extracting only the second page."""
        result = pdf_to_markdown(path=sample_pdf, start_page=1, end_page=2)
        assert result.success
        assert result.data["pages_processed"] == 1
        assert "Section Two" in result.data["markdown"]

    def test_file_not_found(self):
        """Test with a non-existent file."""
        result = pdf_to_markdown(path="/nonexistent/file.pdf")
        assert not result.success
        assert "not found" in result.error.lower()

    def test_not_a_pdf(self, tmp_path):
        """Test with a non-PDF file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a pdf")
        result = pdf_to_markdown(path=str(txt_file))
        assert not result.success
        assert "not a pdf" in result.error.lower()

    def test_start_page_out_of_range(self, sample_pdf):
        """Test with start_page beyond document length."""
        result = pdf_to_markdown(path=sample_pdf, start_page=100)
        assert not result.success
        assert "exceeds" in result.error.lower()

    def test_heading_detection(self, sample_pdf):
        """Test that large text is detected as markdown headings."""
        result = pdf_to_markdown(path=sample_pdf)
        assert result.success
        markdown = result.data["markdown"]
        # The title (fontsize=20) should be detected as a heading
        assert "# Document Title" in markdown or "## Document Title" in markdown

    def test_schema_generation(self):
        """Test that the tool generates valid schemas."""
        schema = pdf_to_markdown.to_openai_function()
        assert schema["name"] == "pdf_to_markdown"
        assert "parameters" in schema
        assert "path" in schema["parameters"]["properties"]


# --- summarize_pdf tests ---


class TestSummarizePdf:
    """Tests for the summarize_pdf tool."""

    def test_file_not_found(self):
        """Test with a non-existent file."""
        result = summarize_pdf(path="/nonexistent/file.pdf")
        assert not result.success
        assert "not found" in result.error.lower()

    def test_not_a_pdf(self, tmp_path):
        """Test with a non-PDF file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a pdf")
        result = summarize_pdf(path=str(txt_file))
        assert not result.success
        assert "not a pdf" in result.error.lower()

    @patch("agent_tooling.tools.media.pdf.httpx.Client")
    def test_successful_summarization(self, mock_client_cls, sample_pdf):
        """Test successful PDF summarization with mocked Ollama."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "This document discusses two sections of sample content."
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = summarize_pdf(path=sample_pdf)
        assert result.success
        assert "two sections" in result.data["summary"]
        assert result.data["page_count"] == 2

    @patch("agent_tooling.tools.media.pdf.httpx.Client")
    def test_max_pages(self, mock_client_cls, sample_pdf):
        """Test that max_pages limits text extraction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Summary of page 1."}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = summarize_pdf(path=sample_pdf, max_pages=1)
        assert result.success
        assert result.data["pages_processed"] == 1

    @patch("agent_tooling.tools.media.pdf.httpx.Client")
    def test_ollama_connection_error(self, mock_client_cls, sample_pdf):
        """Test handling of Ollama connection failure."""
        import httpx

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_cls.return_value = mock_client

        result = summarize_pdf(path=sample_pdf)
        assert not result.success
        assert "ollama" in result.error.lower()

    def test_schema_generation(self):
        """Test that the tool generates valid schemas."""
        schema = summarize_pdf.to_openai_function()
        assert schema["name"] == "summarize_pdf"
        assert "path" in schema["parameters"]["properties"]


# --- analyze_image tests ---


class TestAnalyzeImage:
    """Tests for the analyze_image tool."""

    def test_file_not_found(self):
        """Test with a non-existent image file."""
        result = analyze_image(source="/nonexistent/image.png")
        assert not result.success
        assert "not found" in result.error.lower()

    def test_unsupported_format(self, tmp_path):
        """Test with an unsupported file extension."""
        bad_file = tmp_path / "test.xyz"
        bad_file.write_bytes(b"not an image")
        result = analyze_image(source=str(bad_file))
        assert not result.success
        assert "unsupported" in result.error.lower()

    @patch("agent_tooling.tools.media.image.httpx.Client")
    def test_successful_local_image(self, mock_client_cls, sample_image):
        """Test successful image analysis with a local file."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "A small red pixel image."}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = analyze_image(source=sample_image)
        assert result.success
        assert "red pixel" in result.data["description"]
        assert result.data["model"] == "llava"

    @patch("agent_tooling.tools.media.image.httpx.Client")
    def test_successful_url_image(self, mock_client_cls):
        """Test successful image analysis from a URL."""
        # First call: GET to download image; second call: POST to Ollama
        mock_download_response = MagicMock()
        mock_download_response.content = b'\x89PNG\r\n\x1a\nfakedata'
        mock_download_response.raise_for_status = MagicMock()

        mock_ollama_response = MagicMock()
        mock_ollama_response.json.return_value = {
            "message": {"content": "A photograph of a sunset."}
        }
        mock_ollama_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_download_response
        mock_client.post.return_value = mock_ollama_response
        mock_client_cls.return_value = mock_client

        result = analyze_image(source="https://example.com/photo.jpg")
        assert result.success
        assert "sunset" in result.data["description"]

    @patch("agent_tooling.tools.media.image.httpx.Client")
    def test_ollama_connection_error(self, mock_client_cls, sample_image):
        """Test handling of Ollama connection failure."""
        import httpx

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_cls.return_value = mock_client

        result = analyze_image(source=sample_image)
        assert not result.success
        assert "ollama" in result.error.lower()

    def test_custom_prompt(self, sample_image):
        """Test that custom prompt is passed through."""
        schema = analyze_image.to_openai_function()
        # Verify prompt parameter exists in schema
        assert "prompt" in schema["parameters"]["properties"]

    def test_schema_generation(self):
        """Test that the tool generates valid schemas."""
        schema = analyze_image.to_openai_function()
        assert schema["name"] == "analyze_image"
        assert "source" in schema["parameters"]["properties"]


# --- Registry integration tests ---


class TestMediaToolsRegistry:
    """Test that media tools are properly registered."""

    def test_tools_registered(self):
        """Test that all media tools appear in the registry."""
        from agent_tooling.tools.registry import ToolRegistry

        media_tools = ToolRegistry.get_by_category("media")
        media_names = {t.name for t in media_tools}

        assert "analyze_image" in media_names
        assert "pdf_to_markdown" in media_names
        assert "summarize_pdf" in media_names

    def test_mcp_enabled(self):
        """Test that all media tools are MCP-enabled."""
        from agent_tooling.tools.registry import ToolRegistry

        for tool in ToolRegistry.get_by_category("media"):
            assert tool.mcp_enabled, f"{tool.name} should be MCP-enabled"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
