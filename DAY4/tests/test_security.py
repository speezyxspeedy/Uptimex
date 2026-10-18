import ipaddress
import pytest
from app.security import (
    validate_url_syntax,
    is_ip_blocked,
    SecurityValidationError,
    validate_target_url
)


def test_validate_url_syntax_allowed():
    scheme, host, port = validate_url_syntax("https://example.com/api/test")
    assert scheme == "https"
    assert host == "example.com"
    assert port == 443

    scheme, host, port = validate_url_syntax("http://api.service.org:8080/health")
    assert scheme == "http"
    assert host == "api.service.org"
    assert port == 8080


def test_validate_url_syntax_rejects_unsupported_schemes():
    with pytest.raises(SecurityValidationError, match="Unsupported protocol"):
        validate_url_syntax("file:///etc/passwd")

    with pytest.raises(SecurityValidationError, match="Unsupported protocol"):
        validate_url_syntax("ftp://ftp.example.com/file.txt")

    with pytest.raises(SecurityValidationError, match="Unsupported protocol"):
        validate_url_syntax("gopher://gopher.floodgap.com")


def test_validate_url_syntax_rejects_credentials():
    with pytest.raises(SecurityValidationError, match="embedded authentication credentials"):
        validate_url_syntax("https://admin:password123@example.com")


def test_validate_url_syntax_rejects_blocked_hostnames():
    with pytest.raises(SecurityValidationError, match="Host 'localhost' is not permitted"):
        validate_url_syntax("http://localhost:8000")

    with pytest.raises(SecurityValidationError, match="Host '169.254.169.254' is not permitted"):
        validate_url_syntax("http://169.254.169.254/latest/meta-data")

    with pytest.raises(SecurityValidationError, match="metadata.google.internal"):
        validate_url_syntax("http://metadata.google.internal/computeMetadata/v1/")


def test_is_ip_blocked_ranges():
    # Loopback
    assert is_ip_blocked(ipaddress.ip_address("127.0.0.1")) is True
    assert is_ip_blocked(ipaddress.ip_address("127.1.2.3")) is True
    assert is_ip_blocked(ipaddress.ip_address("::1")) is True

    # Private RFC 1918
    assert is_ip_blocked(ipaddress.ip_address("10.0.0.1")) is True
    assert is_ip_blocked(ipaddress.ip_address("192.168.1.1")) is True
    assert is_ip_blocked(ipaddress.ip_address("172.16.5.10")) is True
    assert is_ip_blocked(ipaddress.ip_address("172.31.255.255")) is True

    # Link-local & cloud metadata
    assert is_ip_blocked(ipaddress.ip_address("169.254.169.254")) is True
    assert is_ip_blocked(ipaddress.ip_address("fe80::1")) is True

    # Carrier-grade NAT
    assert is_ip_blocked(ipaddress.ip_address("100.64.0.1")) is True

    # Documentation / Test nets
    assert is_ip_blocked(ipaddress.ip_address("192.0.2.1")) is True
    assert is_ip_blocked(ipaddress.ip_address("198.51.100.1")) is True
    assert is_ip_blocked(ipaddress.ip_address("203.0.113.1")) is True

    # Public safe IPs
    assert is_ip_blocked(ipaddress.ip_address("8.8.8.8")) is False
    assert is_ip_blocked(ipaddress.ip_address("1.1.1.1")) is False
    assert is_ip_blocked(ipaddress.ip_address("93.184.216.34")) is False


def test_validate_target_url_rejects_private_ip():
    with pytest.raises(SecurityValidationError, match="Destination IP address '127.0.0.1' is in a private or restricted range"):
        validate_target_url("http://127.0.0.1:8000/health")

    with pytest.raises(SecurityValidationError, match="Destination IP address '10.0.0.5' is in a private or restricted range"):
        validate_target_url("http://10.0.0.5/api")
