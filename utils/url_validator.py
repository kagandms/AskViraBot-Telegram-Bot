"""
URL Validation & SSRF Protection Utility
Prevents Server-Side Request Forgery by blocking private/internal IPs and dangerous schemes.
"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Allowed URL schemes
SAFE_SCHEMES = {"http", "https"}

# Reserved/private IP ranges that must be blocked
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),  # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),  # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("0.0.0.0/8"),  # "This" network
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


def _is_private_ip(hostname: str) -> bool:
    """Check if a hostname resolves to a private/reserved IP address."""
    try:
        resolved_ips = socket.getaddrinfo(hostname, None)
        for _family, _, _, _, sockaddr in resolved_ips:
            ip_str = sockaddr[0]
            ip = ipaddress.ip_address(ip_str)
            for network in BLOCKED_NETWORKS:
                if ip in network:
                    return True
    except (socket.gaierror, ValueError, OSError):
        # DNS resolution failure — treat as unsafe
        return True
    return False


def is_safe_url(url: str, resolve_dns: bool = True) -> bool:
    """
    Validate that a URL is safe to fetch (not targeting internal services).

    Args:
        url: The URL to validate.
        resolve_dns: If True, also resolve the hostname and check the IP.

    Returns:
        True if the URL is safe to fetch, False otherwise.
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False

    # 1. Scheme check
    if parsed.scheme not in SAFE_SCHEMES:
        logger.warning(f"SSRF blocked: unsafe scheme '{parsed.scheme}' in URL")
        return False

    # 2. Hostname must exist
    hostname = parsed.hostname
    if not hostname:
        logger.warning("SSRF blocked: no hostname in URL")
        return False

    # 3. Block obvious internal hostnames
    blocked_hostnames = {"localhost", "0.0.0.0", "127.0.0.1", "::1", "metadata.google.internal"}
    if hostname.lower() in blocked_hostnames:
        logger.warning(f"SSRF blocked: internal hostname '{hostname}'")
        return False

    # 4. Check if hostname is a raw IP address in a blocked range
    try:
        ip = ipaddress.ip_address(hostname)
        for network in BLOCKED_NETWORKS:
            if ip in network:
                logger.warning(f"SSRF blocked: hostname '{hostname}' is a private IP")
                return False
    except ValueError:
        pass  # Not an IP address, continue to DNS check

    # 5. DNS resolution check (optional but recommended)
    if resolve_dns and _is_private_ip(hostname):
        logger.warning(f"SSRF blocked: hostname '{hostname}' resolves to private IP")
        return False

    return True
