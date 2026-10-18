import ipaddress
import socket
from urllib.parse import urlparse, urljoin
from typing import List, Tuple, Optional


# Forbidden IP networks for SSRF protection
BLOCKED_NETWORKS = [
    # IPv4 Private & Local
    ipaddress.ip_network("0.0.0.0/8"),          # Current network (only valid as source address)
    ipaddress.ip_network("10.0.0.0/8"),         # Private-Use (RFC 1918)
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space / CGNAT (RFC 6598)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback (RFC 1122)
    ipaddress.ip_network("169.254.0.0/16"),     # Link Local / Cloud Metadata (RFC 3927)
    ipaddress.ip_network("172.16.0.0/12"),      # Private-Use (RFC 1918)
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # Documentation (TEST-NET-1)
    ipaddress.ip_network("192.88.99.0/24"),     # 6to4 Relay Anycast
    ipaddress.ip_network("192.168.0.0/16"),     # Private-Use (RFC 1918)
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),    # Documentation (TEST-NET-2)
    ipaddress.ip_network("203.0.113.0/24"),     # Documentation (TEST-NET-3)
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved for Future Use
    ipaddress.ip_network("255.255.255.255/32"), # Limited Broadcast

    # IPv6 Private, Local & Reserved
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("64:ff9b:1::/48"),     # Local-Use IPv4/IPv6 Translation
    ipaddress.ip_network("100::/64"),           # Discard-Only Address Block
    ipaddress.ip_network("2001:db8::/32"),      # Documentation
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local Unicast
    ipaddress.ip_network("ff00::/8"),           # Multicast
]

# Explicitly blocked hostnames (e.g., metadata endpoints, internal services)
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
    "169.254.169.254",
    "100.100.100.200",
}


class SecurityValidationError(ValueError):
    """Raised when a URL or resolved destination fails security validation."""
    pass


def is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address belongs to any blocked or private subnet."""
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True
    for network in BLOCKED_NETWORKS:
        if ip in network:
            return True
    return False


def validate_url_syntax(url_str: str) -> Tuple[str, str, int]:
    """
    Validates URL syntax, scheme, and userinfo.
    Returns (scheme, hostname, port).
    """
    if not url_str or not isinstance(url_str, str):
        raise SecurityValidationError("URL must be a non-empty string.")

    url_str = url_str.strip()
    if len(url_str) > 2048:
        raise SecurityValidationError("URL exceeds maximum length of 2048 characters.")

    try:
        parsed = urlparse(url_str)
    except Exception as exc:
        raise SecurityValidationError(f"Invalid URL structure: {exc}")

    # Enforce only http or https
    if parsed.scheme.lower() not in ("http", "https"):
        raise SecurityValidationError(
            f"Unsupported protocol '{parsed.scheme}'. Only HTTP and HTTPS are permitted."
        )

    # Reject userinfo / credentials in URL
    if parsed.username or parsed.password:
        raise SecurityValidationError("URLs with embedded authentication credentials are not permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SecurityValidationError("URL must contain a valid hostname.")

    hostname = hostname.lower().strip()
    if hostname in BLOCKED_HOSTNAMES:
        raise SecurityValidationError(f"Host '{hostname}' is not permitted.")

    # Determine port
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme.lower() == "https" else 80
    elif not (1 <= port <= 65535):
        raise SecurityValidationError(f"Port {port} is out of valid range (1-65535).")

    return parsed.scheme.lower(), hostname, port


def resolve_and_validate_destination(hostname: str, port: int) -> List[str]:
    """
    Resolves hostname via DNS and verifies that all resolved IP addresses are safe public IPs.
    Returns list of safe resolved IP strings.
    """
    # Check if the hostname is directly an IP literal
    try:
        ip_obj = ipaddress.ip_address(hostname)
        is_ip_literal = True
    except ValueError:
        is_ip_literal = False

    if is_ip_literal:
        if is_ip_blocked(ip_obj):
            raise SecurityValidationError(f"Destination IP address '{hostname}' is in a private or restricted range.")
        return [str(ip_obj)]

    try:
        # Perform DNS resolution
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SecurityValidationError(f"Could not resolve hostname '{hostname}': DNS lookup failed.")
    except Exception as exc:
        raise SecurityValidationError(f"DNS resolution error for '{hostname}': {exc}")

    resolved_ips: List[str] = []
    for family, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise SecurityValidationError(f"Invalid IP address format returned by DNS: {ip_str}")

        if is_ip_blocked(ip_obj):
            raise SecurityValidationError(
                f"Hostname '{hostname}' resolved to a restricted IP address ({ip_str})."
            )
        if ip_str not in resolved_ips:
            resolved_ips.append(ip_str)

    if not resolved_ips:
        raise SecurityValidationError(f"No valid IP addresses resolved for '{hostname}'.")

    return resolved_ips


def validate_target_url(url_str: str) -> str:
    """
    Complete security validation of a target URL including syntax, credentials, and DNS resolution.
    Returns the normalized URL string if valid, otherwise raises SecurityValidationError.
    """
    scheme, hostname, port = validate_url_syntax(url_str)
    resolve_and_validate_destination(hostname, port)
    return url_str.strip()


def validate_redirect_target(current_url: str, location_header: str) -> str:
    """
    Computes absolute URL for a redirect header and performs full security validation.
    """
    new_url = urljoin(current_url, location_header)
    return validate_target_url(new_url)
