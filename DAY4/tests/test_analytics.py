from datetime import timedelta
from unittest.mock import patch
from app.models import Monitor, CheckResult, utc_now


def test_analytics_with_known_checks(client, db_session):
    with patch("app.security.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]

        # Create monitor
        mon = Monitor(
            name="Analytics Site",
            url="https://example.com",
            interval_seconds=60,
            timeout_seconds=5,
            method="GET",
            expected_status_codes="200",
            is_enabled=True,
            current_status="UP"
        )
        db_session.add(mon)
        db_session.commit()
        db_session.refresh(mon)

        now = utc_now()
        # Add 3 successful checks (100ms, 120ms, 140ms) and 1 failed check (500ms)
        checks = [
            CheckResult(monitor_id=mon.id, checked_at=now - timedelta(minutes=15), status_code=200, response_time_ms=100.0, is_success=True),
            CheckResult(monitor_id=mon.id, checked_at=now - timedelta(minutes=10), status_code=200, response_time_ms=120.0, is_success=True),
            CheckResult(monitor_id=mon.id, checked_at=now - timedelta(minutes=5), status_code=500, response_time_ms=500.0, is_success=False),
            CheckResult(monitor_id=mon.id, checked_at=now - timedelta(minutes=1), status_code=200, response_time_ms=140.0, is_success=True),
        ]
        db_session.add_all(checks)
        db_session.commit()

        # Query analytics endpoint for 24 hours
        resp = client.get(f"/api/monitors/{mon.id}/analytics?hours=24")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_checks"] == 4
        assert data["success_checks"] == 3
        assert data["failed_checks"] == 1
        # 3 out of 4 = 75.0%
        assert data["uptime_percentage"] == 75.0
        assert data["uptime_display"] == "75.00%"
        assert data["min_response_time_ms"] == 100.0
        assert data["max_response_time_ms"] == 500.0
        # Avg = (100 + 120 + 500 + 140) / 4 = 215.0
        assert data["avg_response_time_ms"] == 215.0
        assert len(data["timeseries"]) == 4


def test_analytics_with_no_history_reports_insufficient_data(client, db_session):
    with patch("app.security.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]

        mon = Monitor(
            name="Empty Site",
            url="https://example.com",
            interval_seconds=60,
            timeout_seconds=5,
            method="GET",
            expected_status_codes="200",
            is_enabled=True,
            current_status="PENDING"
        )
        db_session.add(mon)
        db_session.commit()
        db_session.refresh(mon)

        resp = client.get(f"/api/monitors/{mon.id}/analytics?hours=24")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_checks"] == 0
        assert data["uptime_percentage"] is None
        assert data["uptime_display"] == "Insufficient data"
        assert data["avg_response_time_ms"] is None


def test_csv_export(client, db_session):
    with patch("app.security.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]

        mon = Monitor(
            name="CSV Site",
            url="https://example.com",
            interval_seconds=60,
            timeout_seconds=5,
            method="GET",
            expected_status_codes="200",
            is_enabled=True,
            current_status="UP"
        )
        db_session.add(mon)
        db_session.commit()
        db_session.refresh(mon)

        c1 = CheckResult(monitor_id=mon.id, checked_at=utc_now(), status_code=200, response_time_ms=95.5, is_success=True)
        db_session.add(c1)
        db_session.commit()

        resp = client.get(f"/api/monitors/{mon.id}/history/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment; filename=" in resp.headers["content-disposition"]
        content = resp.text
        assert "Check ID,Monitor ID,Monitor Name" in content
        assert "CSV Site" in content
        assert "95.5" in content


def test_dashboard_summary(client, db_session):
    with patch("app.security.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]

        m1 = Monitor(name="M1", url="https://example.com/1", interval_seconds=60, timeout_seconds=5, method="GET", expected_status_codes="200", is_enabled=True, current_status="UP", last_response_time_ms=100.0)
        m2 = Monitor(name="M2", url="https://example.com/2", interval_seconds=60, timeout_seconds=5, method="GET", expected_status_codes="200", is_enabled=True, current_status="DOWN", last_response_time_ms=200.0)
        m3 = Monitor(name="M3", url="https://example.com/3", interval_seconds=60, timeout_seconds=5, method="GET", expected_status_codes="200", is_enabled=False, current_status="PAUSED")

        db_session.add_all([m1, m2, m3])
        db_session.commit()

        resp = client.get("/api/summary")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_monitors"] == 3
        assert data["up_count"] == 1
        assert data["down_count"] == 1
        assert data["paused_count"] == 1
        assert data["overall_avg_response_time"] == 150.0  # (100 + 200) / 2
