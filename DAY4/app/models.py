from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Monitor(Base):
    __tablename__ = "monitors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    url = Column(String(2048), nullable=False)
    interval_seconds = Column(Integer, default=60, nullable=False)
    timeout_seconds = Column(Integer, default=10, nullable=False)
    method = Column(String(10), default="GET", nullable=False)
    expected_status_codes = Column(String(100), default="200-299", nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    current_status = Column(String(20), default="PENDING", nullable=False)  # PENDING, UP, DOWN, PAUSED
    
    last_check_at = Column(DateTime(timezone=True), nullable=True)
    last_response_time_ms = Column(Float, nullable=True)
    last_status_code = Column(Integer, nullable=True)
    last_error = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    check_results = relationship(
        "CheckResult",
        back_populates="monitor",
        cascade="all, delete-orphan",
        order_by="desc(CheckResult.checked_at)"
    )
    incidents = relationship(
        "Incident",
        back_populates="monitor",
        cascade="all, delete-orphan",
        order_by="desc(Incident.started_at)"
    )


class CheckResult(Base):
    __tablename__ = "check_results"

    id = Column(Integer, primary_key=True, index=True)
    monitor_id = Column(Integer, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False, index=True)
    checked_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=False)
    is_success = Column(Boolean, nullable=False, index=True)
    error_category = Column(String(50), nullable=True)
    error_message = Column(String(255), nullable=True)

    monitor = relationship("Monitor", back_populates="check_results")

    __table_args__ = (
        Index("ix_check_results_monitor_checked_at", "monitor_id", "checked_at"),
    )


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    monitor_id = Column(Integer, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)
    cause = Column(String(255), nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False, index=True)  # ACTIVE, RESOLVED

    monitor = relationship("Monitor", back_populates="incidents")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(50), primary_key=True)
    value = Column(String(255), nullable=False)
