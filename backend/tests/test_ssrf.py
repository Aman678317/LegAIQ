"""SSRF guard tests — outbound fetch protection."""
import pytest
from fastapi import HTTPException

from app.security.ssrf import validate_external_url

ALLOWED = [
    "https://indiankanoon.org/doc/12345/",
    "https://api.openai.com/v1/chat/completions",
    "http://example.com/document.pdf",
    "https://main.sci.gov.in/judgments",
]

BLOCKED = [
    # scheme
    "file:///etc/passwd",
    "ftp://example.com/file",
    "gopher://example.com",
    # loopback / private ranges
    "http://localhost/api",
    "http://127.0.0.1:8080/admin",
    "http://10.0.0.5/internal",
    "http://192.168.1.1/router",
    "http://172.16.0.1/console",
    # link-local / metadata endpoints
    "http://169.254.169.254/latest/meta-data/",
    "http://metadata.google.internal/computeMetadata/v1/",
    # reserved / multicast
    "http://0.0.0.0/",
    "http://224.0.0.1/stream",
    # malformed
    "",
    "not a url",
    "https://",  # no host
]


@pytest.mark.parametrize("url", ALLOWED)
def test_allows_public_urls(url):
    assert validate_external_url(url) == url


@pytest.mark.parametrize("url", BLOCKED)
def test_blocks_dangerous_urls(url):
    with pytest.raises(HTTPException) as exc:
        validate_external_url(url)
    assert exc.value.status_code == 400


def test_blocks_dns_rebinding_to_private(monkeypatch):
    """A public hostname that resolves to a private IP must be blocked."""
    from app.security import ssrf

    monkeypatch.setattr(
        ssrf, "_resolve_all",
        lambda host: ["192.168.0.10"] if host == "evil.example.com" else [],
    )
    with pytest.raises(HTTPException) as exc:
        ssrf.validate_external_url("https://evil.example.com/doc")
    assert "blocked address" in exc.value.detail.lower()
