"""Scenario loading and simulation orchestration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.models.schemas import (
    CompletionRequest,
    DataMode,
    DataSourceInfo,
    DownstreamAlert,
    JammerModel,
    PredictionRequest,
    ScenarioConfig,
    ScenarioModeStatus,
    SituationalSnapshot,
)
from app.services.completion import CompletionEngine
from app.services.data_source import DataSourceService
from app.services.jammer import JammerEngine
from app.services.orbit import (
    OrbitEngine,
    generate_walker_constellation,
    load_satellites_from_tle_text,
)
from app.services.prediction import PredictionEngine
from app.services.propagation import PropagationEngine
from app.services.risk import RiskEngine
from app.services.real_data import RealObservationRepository
from app.services.situational import SituationalEngine


class SimulationManager:
    """Central orchestrator for the EMS platform."""

    def __init__(self):
        self.scenario: ScenarioConfig | None = None
        self.satellites = []
        self.orbit: OrbitEngine | None = None
        self.jammer_engine: JammerEngine | None = None
        self.propagation: PropagationEngine | None = None
        self.situational: SituationalEngine | None = None
        self.completion: CompletionEngine | None = None
        self.prediction: PredictionEngine | None = None
        self.risk: RiskEngine | None = None
        self.current_time: datetime | None = None
        self.data_source_service = DataSourceService()
        self.data_sources: list[DataSourceInfo] = []
        self.real_observations = RealObservationRepository()
        self.mode_paths = {
            DataMode.SIMULATION: "demo_leo_v0.json",
            DataMode.ONLINE: "tle_online_v0.json",
        }
        self.current_mode = DataMode.ONLINE
        self.current_scenario_path = ""
        self._history: list[SituationalSnapshot] = []
        self._alerts: list[DownstreamAlert] = []

    def _build_satellites_from_constellation(
        self,
        constellation: dict,
        epoch: datetime,
        scenario_dir: Path,
    ) -> tuple[list, list[DataSourceInfo]]:
        constellation_type = constellation.get("type", "walker")
        if constellation_type == "mixed_local":
            from app.models.schemas import SatelliteModel
            satellites, infos = [], []
            for group in constellation["groups"]:
                source = (scenario_dir / group["source"]).resolve()
                if group["format"] == "tle":
                    batch = load_satellites_from_tle_text(source.read_text(encoding="utf-8-sig"))
                else:
                    records = json.loads(source.read_text(encoding="utf-8-sig"))
                    batch = [SatelliteModel(id=str(r["NORAD_CAT_ID"]), name=r["OBJECT_NAME"], omm=r) for r in records]
                for sat in batch:
                    sat.id = group["id"] + ":" + sat.id
                    sat.constellation_id = group["id"]
                satellites.extend(batch)
                infos.append(DataSourceInfo(source=str(source), source_type=group["format"], detail=f'{group["id"]}: {len(batch)} records'))
            if len({s.id for s in satellites}) != len(satellites):
                raise ValueError("Duplicate satellite IDs")
            return satellites, infos
        if constellation_type == "tle":
            limit = constellation.get("limit")
            if constellation.get("tle_text"):
                tle_text = constellation["tle_text"]
                satellites = load_satellites_from_tle_text(tle_text, limit=limit)
                return satellites, [self.data_source_service.describe_embedded_tle(tle_text)]
            if constellation.get("tle_source"):
                tle_text, source_info = self.data_source_service.resolve_tle(
                    str(constellation["tle_source"]),
                    scenario_dir,
                )
                satellites = load_satellites_from_tle_text(tle_text, limit=limit)
                return satellites, [source_info]
            raise ValueError("TLE constellation requires `tle_text` or `tle_source`")
        if constellation_type != "walker":
            raise ValueError(f"Unsupported constellation type: {constellation_type}")
        satellites = generate_walker_constellation(
            planes=constellation["planes"],
            sats_per_plane=constellation["sats_per_plane"],
            altitude_km=constellation["altitude_km"],
            inclination_deg=constellation["inclination_deg"],
            epoch=epoch,
        )
        return satellites, []


    @staticmethod
    def _source_from_spec(spec) -> str | None:
        if isinstance(spec, str):
            return spec
        if isinstance(spec, dict):
            return spec.get("source") or spec.get("url") or spec.get("path")
        return None

    def _merge_external_jammers(self, data: dict, scenario_dir: Path) -> list[DataSourceInfo]:
        external_sources = data.get("external_sources") or {}
        spec = external_sources.get("jammers")
        source = self._source_from_spec(spec)
        if not source:
            return []
        records, info = self.data_source_service.load_records(source, scenario_dir, "jammers")
        mode = spec.get("mode", "append") if isinstance(spec, dict) else "append"
        jammers = [JammerModel(**record).model_dump(mode="json") for record in records]
        if mode == "replace":
            data["jammers"] = jammers
        else:
            data["jammers"] = list(data.get("jammers", [])) + jammers
        return [info]

    def _load_real_observations(self, scenario_dir: Path) -> tuple[RealObservationRepository, list[DataSourceInfo]]:
        if not self.scenario:
            return RealObservationRepository(), []
        external_sources = self.scenario.external_sources or {}
        tolerance_sec = external_sources.get("tolerance_sec", 300.0)
        infos: list[DataSourceInfo] = []
        spectrum_records = []
        link_records = []

        spectrum_source = self._source_from_spec(external_sources.get("spectrum_observations"))
        if spectrum_source:
            spectrum_records, info = self.data_source_service.load_records(
                spectrum_source,
                scenario_dir,
                "spectrum_observations",
            )
            infos.append(info)

        link_source = self._source_from_spec(external_sources.get("link_observations"))
        if link_source:
            link_records, info = self.data_source_service.load_records(
                link_source,
                scenario_dir,
                "link_observations",
            )
            infos.append(info)

        return RealObservationRepository(
            spectrum_records=spectrum_records,
            link_records=link_records,
            tolerance_sec=float(tolerance_sec) if tolerance_sec is not None else None,
        ), infos

    def load_scenario(self, scenario_path: str | Path, mode: DataMode | None = None) -> ScenarioConfig:
        path = Path(scenario_path)
        if not path.is_absolute():
            path = settings.data_dir / "scenarios" / path
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
        pre_sources = self._merge_external_jammers(data, path.parent)
        if isinstance(data.get("epoch"), str):
            data["epoch"] = datetime.fromisoformat(data["epoch"].replace("Z", "+00:00"))
        self.scenario = ScenarioConfig(**data)

        constellation = self.scenario.constellation
        epoch = self.scenario.epoch
        if epoch.tzinfo is None:
            epoch = epoch.replace(tzinfo=timezone.utc)

        self.satellites, self.data_sources = self._build_satellites_from_constellation(
            constellation,
            epoch,
            path.parent,
        )
        self.data_sources = pre_sources + self.data_sources
        self.real_observations, observation_sources = self._load_real_observations(path.parent)
        self.data_sources.extend(observation_sources)
        self.orbit = OrbitEngine(
            self.satellites,
            self.scenario.ground_stations,
            altitude_km=constellation.get("altitude_km", 550),
            inclination_deg=constellation.get("inclination_deg", 53),
            epoch=epoch,
        )
        self.jammer_engine = JammerEngine(self.scenario.jammers)
        self.propagation = PropagationEngine(self.orbit, self.jammer_engine)
        self.situational = SituationalEngine(self.orbit, self.propagation, self.scenario, self.real_observations)
        self.completion = CompletionEngine()
        self.prediction = PredictionEngine(self.orbit, self.propagation, self.scenario)
        self.risk = RiskEngine(self.scenario)
        self.current_time = epoch
        self.current_scenario_path = path.name
        self.current_mode = mode or self._infer_mode(path.name, constellation)
        self._history.clear()
        self._alerts.clear()
        return self.scenario

    def _infer_mode(self, scenario_name: str, constellation: dict | None = None) -> DataMode:
        if scenario_name == self.mode_paths[DataMode.ONLINE]:
            return DataMode.ONLINE
        constellation = constellation or {}
        if str(constellation.get("tle_source", "")).startswith(("http://", "https://")):
            return DataMode.ONLINE
        return DataMode.SIMULATION

    def set_mode(self, mode: DataMode) -> ScenarioModeStatus:
        self.load_scenario(self.mode_paths[mode], mode=mode)
        return self.get_mode_status()

    def get_mode_status(self) -> ScenarioModeStatus:
        return ScenarioModeStatus(
            mode=self.current_mode,
            scenario_path=self.current_scenario_path,
            scenario_id=self.scenario.scenario_id if self.scenario else "",
            scenario_name=self.scenario.name if self.scenario else "",
            data_sources=self.get_data_sources(),
        )

    def step(self, delta_sec: int | None = None) -> SituationalSnapshot:
        if not self.scenario or not self.situational:
            raise RuntimeError("No scenario loaded")
        delta = delta_sec or self.scenario.time_step_sec
        from datetime import timedelta

        self.current_time = self.current_time + timedelta(seconds=delta)
        snap = self.situational.generate(self.current_time)
        self._history.append(snap)
        if len(self._history) > 500:
            self._history = self._history[-500:]
        alerts = self.risk.evaluate(snap, predictive=False)
        self._alerts.extend(alerts)
        return snap

    def sync_realtime(self, refresh_sources: bool = False) -> None:
        if not self.scenario:
            raise RuntimeError("No scenario loaded")
        if self.current_mode != DataMode.ONLINE:
            return
        if refresh_sources:
            scenario_path = self.current_scenario_path or self.mode_paths[self.current_mode]
            self.load_scenario(scenario_path, mode=self.current_mode)
        self.current_time = datetime.now(timezone.utc)

    def get_snapshot(
        self,
        sparse: bool = False,
        obs_rate: float = 0.25,
        realtime: bool = False,
        refresh_sources: bool = False,
    ) -> SituationalSnapshot:
        if not self.situational or not self.current_time:
            raise RuntimeError("No scenario loaded")
        if realtime:
            self.sync_realtime(refresh_sources=refresh_sources)
        snap = self.situational.generate(self.current_time)
        if realtime:
            self._alerts = self.risk.evaluate(snap, predictive=False)
        if sparse and snap.spectrum_grid:
            snap = self.situational.apply_sparse_observation(snap, obs_rate)
        return snap
    def complete_situational(self, req: CompletionRequest) -> SituationalSnapshot:
        if self.real_observations.has_spectrum():
            snap = self.get_snapshot(sparse=False)
        else:
            snap = self.get_snapshot(sparse=True, obs_rate=req.observation_rate)
        if not snap.spectrum_grid:
            return snap
        completed = self.completion.complete(snap.spectrum_grid, method=req.method)
        snap.spectrum_grid = completed
        return snap

    def predict(self, req: PredictionRequest) -> dict:
        if not self.prediction or not self.current_time:
            raise RuntimeError("No scenario loaded")
        return self.prediction.predict(
            self.current_time,
            req.horizon_sec,
            self._history,
            req.link_ids,
        )

    def get_alerts(self, limit: int = 50) -> list[DownstreamAlert]:
        return self._alerts[-limit:]

    def get_satellite_positions(self, realtime: bool = False) -> list[dict]:
        if not self.orbit or not self.current_time:
            return []
        if realtime:
            self.sync_realtime(refresh_sources=False)
        return [dict(self.orbit.propagate(satellite.id, self.current_time), name=satellite.name, constellation_id=satellite.constellation_id) for satellite in self.satellites]

    def get_data_sources(self) -> list[DataSourceInfo]:
        return [item.model_copy(deep=True) for item in self.data_sources]

    def export_downstream_payload(self) -> dict:
        snap = self.get_snapshot()
        high_risk = [link for link in snap.links if link.risk_level.value in ("severe", "unavailable")]
        return {
            "timestamp": snap.timestamp.isoformat(),
            "link_assessments": [
                {
                    "link_id": link.link_id,
                    "risk_level": link.risk_level.value,
                    "sinr_db": link.sinr_db,
                    "recommended_freq_hz": None,
                    "prediction_confidence": link.confidence,
                }
                for link in high_risk[:20]
            ],
            "alerts": [alert.model_dump(mode="json") for alert in self.get_alerts(10)],
            "data_sources": [item.model_dump(mode="json") for item in self.get_data_sources()],
        }


sim_manager = SimulationManager()
