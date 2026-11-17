"""Database and cache helpers for containerized deployments."""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from datetime import datetime

import redis
from sqlalchemy import DateTime, Integer, String, Text, create_engine, delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import settings


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base declarative model."""


class ExperimentRunRecord(Base):
    """Persistent experiment metadata snapshot."""

    __tablename__ = "experiment_runs"

    experiment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    completed_cases: Mapped[int] = mapped_column(Integer, default=0)
    config_json: Mapped[str] = mapped_column(Text)
    summary_json: Mapped[str] = mapped_column(Text)
    exports_json: Mapped[str] = mapped_column(Text)
    errors_json: Mapped[str] = mapped_column(Text)
    result_dir: Mapped[str] = mapped_column(Text)


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_database() -> None:
    """Create tables when the service boots."""

    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope():
    """Provide a transactional SQLAlchemy session."""

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_experiment_record(payload: dict) -> None:
    """Persist the latest experiment snapshot."""

    _retryable_write(lambda session: _upsert_record(session, payload))


def load_experiment_records() -> list[dict]:
    """Load experiment metadata from the database."""

    try:
        with Session(engine, future=True) as session:
            records = session.scalars(
                select(ExperimentRunRecord).order_by(ExperimentRunRecord.created_at.desc())
            ).all()
    except OperationalError:
        init_database()
        return []
    return [_record_to_payload(record) for record in records]


def delete_experiment_record(experiment_id: str) -> None:
    """Delete one experiment metadata record from the database."""

    _retryable_write(
        lambda session: session.execute(
            delete(ExperimentRunRecord).where(ExperimentRunRecord.experiment_id == experiment_id)
        )
    )


def clear_experiment_records() -> None:
    """Delete all experiment metadata records from the database."""

    _retryable_write(lambda session: session.execute(delete(ExperimentRunRecord)))


class RedisStateStore:
    """Tiny Redis helper for experiment progress tracking."""

    def __init__(self, url: str):
        self.url = url
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis | None:
        if self._client is not None:
            return self._client
        try:
            client = redis.Redis.from_url(self.url, decode_responses=True)
            client.ping()
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Redis unavailable: %s", exc)
            return None
        self._client = client
        return self._client

    def set_progress(self, experiment_id: str, payload: dict) -> None:
        client = self.client
        if client is None:
            return
        client.set(f"experiment:{experiment_id}:progress", json.dumps(payload, ensure_ascii=False))

    def get_progress(self, experiment_id: str) -> dict | None:
        client = self.client
        if client is None:
            return None
        raw = client.get(f"experiment:{experiment_id}:progress")
        return json.loads(raw) if raw else None

    def delete_progress(self, experiment_id: str) -> None:
        client = self.client
        if client is None:
            return
        client.delete(f"experiment:{experiment_id}:progress")

    def clear_progress(self) -> None:
        client = self.client
        if client is None:
            return
        keys = client.keys("experiment:*:progress")
        if keys:
            client.delete(*keys)


def _retryable_write(callback) -> None:
    try:
        with session_scope() as session:
            callback(session)
    except OperationalError:
        init_database()
        with session_scope() as session:
            callback(session)


def _upsert_record(session: Session, payload: dict) -> None:
    record = session.get(ExperimentRunRecord, payload["experiment_id"])
    if record is None:
        record = ExperimentRunRecord(experiment_id=payload["experiment_id"])
        session.add(record)
    record.status = payload["status"]
    record.created_at = _parse_dt(payload["created_at"])
    record.started_at = _parse_dt(payload.get("started_at"))
    record.finished_at = _parse_dt(payload.get("finished_at"))
    record.total_cases = int(payload.get("total_cases", 0))
    record.completed_cases = int(payload.get("completed_cases", 0))
    record.config_json = json.dumps(payload.get("config", {}), ensure_ascii=False)
    record.summary_json = json.dumps(payload.get("summary", {}), ensure_ascii=False)
    record.exports_json = json.dumps(payload.get("exports", []), ensure_ascii=False)
    record.errors_json = json.dumps(payload.get("errors", []), ensure_ascii=False)
    record.result_dir = payload.get("result_dir", "")


def _record_to_payload(record: ExperimentRunRecord) -> dict:
    return {
        "experiment_id": record.experiment_id,
        "status": record.status,
        "created_at": _to_iso(record.created_at),
        "started_at": _to_iso(record.started_at),
        "finished_at": _to_iso(record.finished_at),
        "total_cases": record.total_cases,
        "completed_cases": record.completed_cases,
        "config": json.loads(record.config_json or "{}"),
        "summary": json.loads(record.summary_json or "{}"),
        "exports": json.loads(record.exports_json or "[]"),
        "errors": json.loads(record.errors_json or "[]"),
        "result_dir": record.result_dir,
    }


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
