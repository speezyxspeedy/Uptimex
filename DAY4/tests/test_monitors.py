from unittest.mock import patch
from app.models import Monitor


def test_create_monitor_success(client, db_session):
    # Mock DNS resolution to return a public IP for example.com
    with patch("app.security.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 443))
        ]
        payload = {
            "name": "Example Production Site",
            "url": "https://example.com",
            "interval_seconds": 60,
            "timeout_seconds": 10,
            "method": "GET",
            "expected_status_codes": "200-299"
        }
        response = client.post("/api/monitors", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Example Production Site"
        assert data["url"] == "https://example.com"
        assert data["current_status"] == "PENDING"
        assert data["is_enabled"] is True


def test_create_monitor_rejects_ssrf_destination(client):
    payload = {
        "name": "Local Loopback Attacker",
        "url": "http://127.0.0.1:8080/admin",
        "interval_seconds": 60,
        "timeout_seconds": 10,
        "method": "GET",
        "expected_status_codes": "200"
    }
    response = client.post("/api/monitors", json=payload)
    assert response.status_code == 422
    assert "private or restricted range" in response.json()["detail"]


def test_create_monitor_rejects_unsupported_protocol(client):
    payload = {
        "name": "Local File Exploit",
        "url": "file:///etc/passwd",
        "interval_seconds": 60,
        "timeout_seconds": 10,
        "method": "GET",
        "expected_status_codes": "200"
    }
    response = client.post("/api/monitors", json=payload)
    assert response.status_code == 422
    assert "Only HTTP and HTTPS are permitted" in response.json()["detail"]


def test_update_monitor(client, db_session):
    with patch("app.security.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
        # Create initial monitor
        create_resp = client.post("/api/monitors", json={
            "name": "Original Name",
            "url": "https://example.com",
            "interval_seconds": 60,
            "timeout_seconds": 10,
            "method": "GET",
            "expected_status_codes": "200"
        })
        mon_id = create_resp.json()["id"]

        # Update monitor
        update_resp = client.put(f"/api/monitors/{mon_id}", json={
            "name": "Renamed Site",
            "interval_seconds": 120,
            "method": "HEAD"
        })
        assert update_resp.status_code == 200
        updated_data = update_resp.json()
        assert updated_data["name"] == "Renamed Site"
        assert updated_data["interval_seconds"] == 120
        assert updated_data["method"] == "HEAD"


def test_toggle_monitor_pause_and_resume(client, db_session):
    with patch("app.security.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
        create_resp = client.post("/api/monitors", json={
            "name": "Toggle Site",
            "url": "https://example.com",
            "interval_seconds": 60,
            "timeout_seconds": 10,
            "method": "GET",
            "expected_status_codes": "200"
        })
        mon_id = create_resp.json()["id"]

        # Toggle to pause
        toggle1 = client.post(f"/api/monitors/{mon_id}/toggle")
        assert toggle1.status_code == 200
        assert toggle1.json()["is_enabled"] is False
        assert toggle1.json()["current_status"] == "PAUSED"

        # Toggle to resume
        toggle2 = client.post(f"/api/monitors/{mon_id}/toggle")
        assert toggle2.status_code == 200
        assert toggle2.json()["is_enabled"] is True
        assert toggle2.json()["current_status"] == "PENDING"


def test_delete_monitor(client, db_session):
    with patch("app.security.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
        create_resp = client.post("/api/monitors", json={
            "name": "Site To Delete",
            "url": "https://example.com",
            "interval_seconds": 60,
            "timeout_seconds": 10,
            "method": "GET",
            "expected_status_codes": "200"
        })
        mon_id = create_resp.json()["id"]

        del_resp = client.delete(f"/api/monitors/{mon_id}")
        assert del_resp.status_code == 204

        get_resp = client.get(f"/api/monitors/{mon_id}")
        assert get_resp.status_code == 404
