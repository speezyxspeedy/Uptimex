from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.security import validate_target_url, SecurityValidationError


def parse_status_code_spec(spec: str) -> set[int]:
    """
    Parses status code specification like '200-299' or '200,201,204' or '200-204,301,302'.
    Returns set of allowed integer status codes.
    """
    codes = set()
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    if not parts:
        raise ValueError("Expected status codes cannot be empty.")
    
    for part in parts:
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) != 2:
                raise ValueError(f"Invalid range format in '{part}'")
            try:
                start = int(bounds[0].strip())
                end = int(bounds[1].strip())
            except ValueError:
                raise ValueError(f"Non-integer status code in range '{part}'")
            if start > end or start < 100 or end > 599:
                raise ValueError(f"Invalid HTTP status range '{part}'")
            codes.update(range(start, end + 1))
        else:
            try:
                code = int(part)
            except ValueError:
                raise ValueError(f"Non-integer status code '{part}'")
            if not (100 <= code <= 599):
                raise ValueError(f"Status code {code} is outside HTTP range 100-599")
            codes.add(code)
    return codes


class MonitorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Monitor friendly name")
    url: str = Field(..., max_length=2048, description="Target HTTP or HTTPS URL")
    interval_seconds: int = Field(60, ge=10, le=86400, description="Check frequency in seconds (10s to 24h)")
    timeout_seconds: int = Field(10, ge=1, le=60, description="Request timeout in seconds (1s to 60s)")
    method: str = Field("GET", description="HTTP check method: GET or HEAD")
    expected_status_codes: str = Field("200-299", description="Comma-separated codes or ranges e.g. '200-299' or '200,204'")

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper not in ("GET", "HEAD"):
            raise ValueError("HTTP method must be either 'GET' or 'HEAD'.")
        return v_upper

    @field_validator("expected_status_codes")
    @classmethod
    def validate_status_codes(cls, v: str) -> str:
        try:
            parse_status_code_spec(v)
        except Exception as exc:
            raise ValueError(f"Invalid expected status codes specification: {exc}")
        return v.strip()

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        try:
            validated = validate_target_url(v)
        except SecurityValidationError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise ValueError(f"URL validation error: {e}")
        return validated


class MonitorCreate(MonitorBase):
    pass


class MonitorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, max_length=2048)
    interval_seconds: Optional[int] = Field(None, ge=10, le=86400)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=60)
    method: Optional[str] = None
    expected_status_codes: Optional[str] = None
    is_enabled: Optional[bool] = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_upper = v.strip().upper()
            if v_upper not in ("GET", "HEAD"):
                raise ValueError("HTTP method must be either 'GET' or 'HEAD'.")
            return v_upper
        return v

    @field_validator("expected_status_codes")
    @classmethod
    def validate_status_codes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                parse_status_code_spec(v)
            except Exception as exc:
                raise ValueError(f"Invalid expected status codes specification: {exc}")
            return v.strip()
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                return validate_target_url(v)
            except SecurityValidationError as e:
                raise ValueError(str(e))
            except Exception as e:
                raise ValueError(f"URL validation error: {e}")
        return v


class MonitorResponse(BaseModel):
    id: int
    name: str
    url: str
    interval_seconds: int
    timeout_seconds: int
    method: str
    expected_status_codes: str
    is_enabled: bool
    current_status: str
    last_check_at: Optional[datetime] = None
    last_response_time_ms: Optional[float] = None
    last_status_code: Optional[int] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CheckResultResponse(BaseModel):
    id: int
    monitor_id: int
    checked_at: datetime
    status_code: Optional[int]
    response_time_ms: float
    is_success: bool
    error_category: Optional[str]
    error_message: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class IncidentResponse(BaseModel):
    id: int
    monitor_id: int
    monitor_name: Optional[str] = None
    monitor_url: Optional[str] = None
    started_at: datetime
    resolved_at: Optional[datetime]
    duration_seconds: Optional[int]
    cause: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class DashboardSummary(BaseModel):
    total_monitors: int
    up_count: int
    down_count: int
    paused_count: int
    pending_count: int
    overall_avg_response_time: Optional[float]
    overall_uptime_24h: Optional[float]
    active_incidents_count: int


class TimeseriesPoint(BaseModel):
    timestamp: datetime
    response_time_ms: float
    is_success: bool
    status_code: Optional[int]


class AnalyticsResponse(BaseModel):
    monitor_id: int
    monitor_name: str
    time_window_hours: int
    uptime_percentage: Optional[float]
    uptime_display: str
    avg_response_time_ms: Optional[float]
    min_response_time_ms: Optional[float]
    max_response_time_ms: Optional[float]
    total_checks: int
    success_checks: int
    failed_checks: int
    latest_status_code: Optional[int]
    timeseries: List[TimeseriesPoint]


class AppSettingsSchema(BaseModel):
    default_interval_seconds: int
    default_timeout_seconds: int
    data_retention_days: int
    theme: str
    scheduler_running: bool
    total_monitors_count: int
    active_incidents_count: int
    server_time_utc: datetime


class AppSettingsUpdate(BaseModel):
    default_interval_seconds: Optional[int] = Field(None, ge=10, le=86400)
    default_timeout_seconds: Optional[int] = Field(None, ge=1, le=60)
    data_retention_days: Optional[int] = Field(None, ge=1, le=365)
    theme: Optional[str] = Field(None, pattern="^(dark|light)$")
