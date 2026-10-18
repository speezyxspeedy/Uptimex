import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from app.monitor_service import execute_http_check, perform_monitor_check
from app.models import Monitor, Incident, CheckResult, utc_now


@pytest.mark.asyncio
async def test_execute_http_check_success():
    with patch("app.security.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.is_redirect = False
        mock_response.headers = {}

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            success, status_code, elapsed_ms, err_cat, err_msg = await execute_http_check(
                url="https://example.com",
                method="GET",
                timeout_seconds=5,
                expected_status_codes="200-299"
            )

            assert success is True
            assert status_code == 200
            assert elapsed_ms >= 0
            assert err_cat is None
            assert err_msg is None


@pytest.mark.asyncio
async def test_execute_http_check_status_mismatch():
    with patch("app.security.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 503
        mock_response.is_redirect = False
        mock_response.headers = {}

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            success, status_code, elapsed_ms, err_cat, err_msg = await execute_http_check(
                url="https://example.com",
                method="GET",
                timeout_seconds=5,
                expected_status_codes="200"
            )

            assert success is False
            assert status_code == 503
            assert err_cat == "HTTP_STATUS_MISMATCH"
            assert "Returned status 503" in err_msg


@pytest.mark.asyncio
async def test_execute_http_check_timeout():
    with patch("app.security.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.ConnectTimeout("Connection timed out")

            success, status_code, elapsed_ms, err_cat, err_msg = await execute_http_check(
                url="https://example.com",
                method="GET",
                timeout_seconds=5,
                expected_status_codes="200"
            )

            assert success is False
            assert status_code is None
            assert err_cat == "CONNECTION_TIMEOUT"


@pytest.mark.asyncio
async def test_incident_state_transitions(db_session):
    from tests.conftest import TestingSessionLocal

    with patch("app.security.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]

        # Create a monitor
        monitor = Monitor(
            name="Transition Test Monitor",
            url="https://example.com",
            interval_seconds=60,
            timeout_seconds=5,
            method="GET",
            expected_status_codes="200",
            is_enabled=True,
            current_status="PENDING"
        )
        db_session.add(monitor)
        db_session.commit()
        mon_id = monitor.id

        # Patch SessionLocal in monitor_service to produce fresh test sessions
        with patch("app.monitor_service.SessionLocal", side_effect=TestingSessionLocal):
            # Step 1: Simulate check failure -> monitor transitions to DOWN, opens Incident
            with patch("app.monitor_service.execute_http_check", new_callable=AsyncMock) as mock_check:
                mock_check.return_value = (False, 500, 150.0, "HTTP_STATUS_MISMATCH", "Server Error 500")

                res1 = await perform_monitor_check(mon_id)
                assert res1 is not None
                assert res1.is_success is False

                db_session.expire_all()
                mon = db_session.query(Monitor).filter(Monitor.id == mon_id).first()
                assert mon.current_status == "DOWN"

                # Check incident was opened
                incidents = db_session.query(Incident).filter(Incident.monitor_id == mon_id).all()
                assert len(incidents) == 1
                assert incidents[0].status == "ACTIVE"
                assert "Server Error 500" in incidents[0].cause

            # Step 2: Second failed check during same outage -> stays DOWN, does NOT duplicate incident
            with patch("app.monitor_service.execute_http_check", new_callable=AsyncMock) as mock_check:
                mock_check.return_value = (False, 500, 160.0, "HTTP_STATUS_MISMATCH", "Server Error 500")

                res2 = await perform_monitor_check(mon_id)
                assert res2 is not None

                db_session.expire_all()
                incidents = db_session.query(Incident).filter(Incident.monitor_id == mon_id).all()
                assert len(incidents) == 1  # No duplicate incident created

            # Step 3: Successful check -> monitor transitions to UP, incident is RESOLVED with duration
            with patch("app.monitor_service.execute_http_check", new_callable=AsyncMock) as mock_check:
                mock_check.return_value = (True, 200, 85.0, None, None)

                res3 = await perform_monitor_check(mon_id)
                assert res3 is not None
                assert res3.is_success is True

                db_session.expire_all()
                mon = db_session.query(Monitor).filter(Monitor.id == mon_id).first()
                assert mon.current_status == "UP"

                incidents = db_session.query(Incident).filter(Incident.monitor_id == mon_id).all()
                assert len(incidents) == 1
                assert incidents[0].status == "RESOLVED"
                assert incidents[0].resolved_at is not None
                assert incidents[0].duration_seconds is not None
