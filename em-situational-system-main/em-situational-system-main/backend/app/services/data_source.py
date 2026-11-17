"""Data source resolution with cache/fallback metadata for reproducible experiments."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.models.schemas import DataSourceInfo


class DataSourceService:
    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or settings.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def resolve_tle(self, source: str, scenario_dir: Path) -> tuple[str, DataSourceInfo]:
        if source.startswith(("http://", "https://")):
            return self._resolve_remote_tle(source)

        path = Path(source)
        if not path.is_absolute():
            path = scenario_dir / path
        text = path.read_text(encoding="utf-8-sig")
        stat = path.stat()
        fetched_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        return text, DataSourceInfo(
            source=str(path),
            source_type="local_file",
            fetched_at=fetched_at,
            cache_status="local",
            data_version=self._hash_text(text),
            detail="Loaded from local TLE file",
            cache_path=str(path),
        )

    def describe_embedded_tle(self, tle_text: str) -> DataSourceInfo:
        return DataSourceInfo(
            source="embedded_tle",
            source_type="embedded",
            fetched_at=datetime.now(timezone.utc),
            cache_status="embedded",
            data_version=self._hash_text(tle_text),
            detail="Loaded from scenario-embedded TLE text",
        )

    def _resolve_remote_tle(self, source: str) -> tuple[str, DataSourceInfo]:
        tle_cache_dir = self.cache_dir / "tle"
        tle_cache_dir.mkdir(parents=True, exist_ok=True)
        cache_key = hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]
        tle_path = tle_cache_dir / f"{cache_key}.tle"
        meta_path = tle_cache_dir / f"{cache_key}.json"
        fetched_at = datetime.now(timezone.utc)
        try:
            response = httpx.get(source, timeout=15.0, follow_redirects=True)
            response.raise_for_status()
            text = response.text
            info = DataSourceInfo(
                source=source,
                source_type="online_tle",
                fetched_at=fetched_at,
                cache_status="fresh",
                data_version=self._hash_text(text),
                detail="Fetched from online source",
                cache_path=str(tle_path),
            )
            tle_path.write_text(text, encoding="utf-8")
            meta_path.write_text(json.dumps(info.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
            return text, info
        except Exception as exc:
            if tle_path.exists():
                text = tle_path.read_text(encoding="utf-8-sig")
                if meta_path.exists():
                    cached_info = DataSourceInfo(**json.loads(meta_path.read_text(encoding="utf-8-sig")))
                else:
                    cached_info = DataSourceInfo(
                        source=source,
                        source_type="online_tle",
                        fetched_at=None,
                        cache_status="stale_fallback",
                        data_version=self._hash_text(text),
                        detail="Loaded from cached TLE snapshot",
                        cache_path=str(tle_path),
                    )
                cached_info.cache_status = "stale_fallback"
                cached_info.detail = f"Remote fetch failed, using cache: {exc}"
                return text, cached_info
            raise

    def resolve_text_dataset(
        self,
        source: str,
        scenario_dir: Path,
        dataset_type: str,
    ) -> tuple[str, DataSourceInfo]:
        """Resolve an external dataset from URL or local file with cache metadata."""
        if source.startswith(("http://", "https://")):
            return self._resolve_remote_dataset(source, dataset_type)

        path = Path(source)
        if not path.is_absolute():
            path = scenario_dir / path
        text = path.read_text(encoding="utf-8-sig")
        stat = path.stat()
        fetched_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        return text, DataSourceInfo(
            source=str(path),
            source_type=f"local_{dataset_type}",
            fetched_at=fetched_at,
            cache_status="local",
            data_version=self._hash_text(text),
            detail=f"Loaded {dataset_type} from local file",
            cache_path=str(path),
        )

    def load_records(
        self,
        source: str,
        scenario_dir: Path,
        dataset_type: str,
    ) -> tuple[list[dict[str, Any]], DataSourceInfo]:
        """Load JSON/CSV records from external source."""
        text, info = self.resolve_text_dataset(source, scenario_dir, dataset_type)
        records = self.parse_records(text, source)
        info.detail = f"{info.detail}; parsed {len(records)} records"
        return records, info

    @staticmethod
    def parse_records(text: str, source_hint: str = "") -> list[dict[str, Any]]:
        source_lower = source_hint.lower()
        stripped = text.strip()
        if not stripped:
            return []
        first_line = stripped.splitlines()[0]
        if source_lower.endswith(".csv") or ("," in first_line and not stripped.startswith(("{", "["))):
            return [dict(row) for row in csv.DictReader(stripped.splitlines())]

        payload = json.loads(stripped)
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("items", "records", "observations", "links", "jammers"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
            return [payload]
        raise ValueError("External dataset must be JSON object/list or CSV table")

    def _resolve_remote_dataset(self, source: str, dataset_type: str) -> tuple[str, DataSourceInfo]:
        dataset_cache_dir = self.cache_dir / dataset_type
        dataset_cache_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(source.split("?", 1)[0]).suffix or ".txt"
        cache_key = hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]
        data_path = dataset_cache_dir / f"{cache_key}{suffix}"
        meta_path = dataset_cache_dir / f"{cache_key}.json"
        fetched_at = datetime.now(timezone.utc)
        try:
            response = httpx.get(source, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            text = response.text
            info = DataSourceInfo(
                source=source,
                source_type=f"online_{dataset_type}",
                fetched_at=fetched_at,
                cache_status="fresh",
                data_version=self._hash_text(text),
                detail=f"Fetched {dataset_type} from online source",
                cache_path=str(data_path),
            )
            data_path.write_text(text, encoding="utf-8")
            meta_path.write_text(json.dumps(info.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
            return text, info
        except Exception as exc:
            if data_path.exists():
                text = data_path.read_text(encoding="utf-8-sig")
                if meta_path.exists():
                    cached_info = DataSourceInfo(**json.loads(meta_path.read_text(encoding="utf-8-sig")))
                else:
                    cached_info = DataSourceInfo(
                        source=source,
                        source_type=f"online_{dataset_type}",
                        fetched_at=None,
                        cache_status="stale_fallback",
                        data_version=self._hash_text(text),
                        detail=f"Loaded cached {dataset_type} snapshot",
                        cache_path=str(data_path),
                    )
                cached_info.cache_status = "stale_fallback"
                cached_info.detail = f"Remote fetch failed, using cached {dataset_type}: {exc}"
                return text, cached_info
            raise

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
