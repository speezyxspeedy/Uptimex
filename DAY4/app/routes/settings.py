from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Monitor, Incident, AppSetting, utc_now
from app.schemas import AppSettingsSchema, AppSettingsUpdate
from app.scheduler import is_scheduler_running
from app.config import settings as app_cfg

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_setting(db: Session, key: str, default_val: str) -> str:
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    return setting.value if setting else default_val


def _set_setting(db: Session, key: str, val: str):
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if setting:
        setting.value = val
    else:
        setting = AppSetting(key=key, value=val)
        db.add(setting)
    db.commit()


@router.get("", response_model=AppSettingsSchema)
def get_application_settings(db: Session = Depends(get_db)):
    default_interval = int(_get_setting(db, "default_interval_seconds", str(app_cfg.DEFAULT_CHECK_INTERVAL_SECONDS)))
    default_timeout = int(_get_setting(db, "default_timeout_seconds", str(app_cfg.DEFAULT_TIMEOUT_SECONDS)))
    retention_days = int(_get_setting(db, "data_retention_days", str(app_cfg.DATA_RETENTION_DAYS)))
    theme = _get_setting(db, "theme", "dark")

    total_monitors = db.query(Monitor).count()
    active_incidents = db.query(Incident).filter(Incident.status == "ACTIVE").count()

    return AppSettingsSchema(
        default_interval_seconds=default_interval,
        default_timeout_seconds=default_timeout,
        data_retention_days=retention_days,
        theme=theme,
        scheduler_running=is_scheduler_running(),
        total_monitors_count=total_monitors,
        active_incidents_count=active_incidents,
        server_time_utc=utc_now()
    )


@router.put("", response_model=AppSettingsSchema)
def update_application_settings(payload: AppSettingsUpdate, db: Session = Depends(get_db)):
    if payload.default_interval_seconds is not None:
        _set_setting(db, "default_interval_seconds", str(payload.default_interval_seconds))
    if payload.default_timeout_seconds is not None:
        _set_setting(db, "default_timeout_seconds", str(payload.default_timeout_seconds))
    if payload.data_retention_days is not None:
        _set_setting(db, "data_retention_days", str(payload.data_retention_days))
    if payload.theme is not None:
        _set_setting(db, "theme", payload.theme)

    return get_application_settings(db=db)
