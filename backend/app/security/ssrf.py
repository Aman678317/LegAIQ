"""SSRF protection for outbound web research requests.

Only http/https; blocks localhost, loopback, private, and reserved addresses.
"""
import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException

ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = {
    "metadata.google.internal",
    "169.254.169.254",
}


def _resolve_all(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
        return list({info[4][0] for info in infos})
    except socket.gaierror:
        return []


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_external_url(url: str) -> str:
    """Validate a URL for outbound fetching; raises HTTPException if unsafe."""
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise HTTPException(status_code=400, detail=f"Scheme '{parsed.scheme}' not allowed")

    host = parsed.hostname or ""
    if not host:
        raise HTTPException(status_code=400, detail="URL has no host")

    if host.lower() in BLOCKED_HOSTS:
        raise HTTPException(status_code=400, detail="Blocked host")

    # Literal IP check
    try:
        ipaddress.ip_address(host)
        if _is_blocked_ip(host):
            raise HTTPException(status_code=400, detail="Private or reserved address not allowed")
        return url
    except ValueError:
        pass

    # DNS resolution check (blocks hostnames resolving to private ranges)
    for resolved in _resolve_all(host):
        if _is_blocked_ip(resolved):
            raise HTTPException(
                status_code=400,
                detail=f"Host resolves to blocked address ({resolved})",
            )

    return url
