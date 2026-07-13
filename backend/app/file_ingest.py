"""Bounded manuscript ingestion shared by MCP tools and the browser cockpit."""
from __future__ import annotations

import base64
import binascii
import io
import urllib.parse
import urllib.request
import zipfile
from xml.etree import ElementTree

from .epistemic_review.schemas import FileRef

DOWNLOAD_LIMIT = 10_000_000
DOCUMENT_LIMIT = 5_000_000


def download_file(ref: FileRef) -> bytes:
    parsed = urllib.parse.urlparse(str(ref.download_url))
    if parsed.scheme != "https":
        raise ValueError("file download_url must use HTTPS")
    req = urllib.request.Request(
        str(ref.download_url), headers={"User-Agent": "DESi-Workbench/0.4"}
    )
    with urllib.request.urlopen(req, timeout=20) as response:  # noqa: S310
        if urllib.parse.urlparse(response.geturl()).scheme != "https":
            raise ValueError("file download redirected to a non-HTTPS URL")
        data = response.read(DOWNLOAD_LIMIT + 1)
    if len(data) > DOWNLOAD_LIMIT:
        raise ValueError("file exceeds the 10 MB transport limit")
    return data


def _docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ValueError("invalid DOCX file") from exc
    root = ElementTree.fromstring(xml)
    chunks: list[str] = []
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    for paragraph in root.iter(ns + "p"):
        text = "".join(node.text or "" for node in paragraph.iter(ns + "t"))
        if text.strip():
            chunks.append(text.strip())
    return "\n\n".join(chunks)


def _pdf_text(data: bytes) -> str:
    try:
        import fitz  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ValueError("PDF support requires the 'files' extra (PyMuPDF)") from exc
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # PyMuPDF exposes several parser exception types
        raise ValueError("invalid or unreadable PDF file") from exc
    try:
        return "\n\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def bytes_to_text(data: bytes, *, file_name: str = "", mime_type: str = "") -> str:
    if len(data) > DOWNLOAD_LIMIT:
        raise ValueError("file exceeds the 10 MB transport limit")
    name = file_name.lower()
    mime = mime_type.lower()
    if name.endswith(".docx") or "wordprocessingml" in mime:
        text = _docx_text(data)
    elif name.endswith(".pdf") or mime == "application/pdf":
        text = _pdf_text(data)
    elif name.endswith((".txt", ".md", ".markdown")) or mime.startswith("text/") or not mime:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("text files must be UTF-8") from exc
    else:
        raise ValueError(f"unsupported file type: {mime_type or file_name}")
    ensure_document_limit(text)
    return text


def base64_file_to_text(
    encoded: str, *, file_name: str = "", mime_type: str = ""
) -> str:
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid base64 file payload") from exc
    return bytes_to_text(data, file_name=file_name, mime_type=mime_type)


def file_ref_to_text(ref: FileRef) -> str:
    return bytes_to_text(
        download_file(ref),
        file_name=ref.file_name or "",
        mime_type=ref.mime_type or "",
    )


def ensure_document_limit(text: str) -> None:
    if len(text.encode("utf-8")) > DOCUMENT_LIMIT:
        raise ValueError("document exceeds the 5 MB limit")
