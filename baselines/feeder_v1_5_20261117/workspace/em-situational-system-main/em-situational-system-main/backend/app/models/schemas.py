"""Pydantic models for API and internal data exchange."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LinkType(str, Enum):
    ISL = "isl"
    SGL = "sgl"


class JammerSourceType(str, Enum):
    GROUND_FIXED = "ground_fixed"
    GROUND_MOBILE = "ground_mobile"
    AIRBORNE = "airborne"
    SHIPBORNE = "shipborne"
    SPACE_NONCOOP = "space_noncoop"
    NATURAL = "natural"


class JammingStyle(str, Enum):
    CO_CHANNEL = "co_channel"
    ADJACENT_CHANNEL = "adjacent_channel"
    BARRAGE = "barrage"
    NARROWBAND_SPOT = "narrowband_spot"
    SWEEP = "sweep"
    PULSE = "pulse"
    DECEPTIVE = "deceptive"
    NOISE = "noise"
    BURST_COLLISION = "burst_collision"


class RiskLevel(str, Enum):
    NORMAL = "normal"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNAVAILABLE = "unavailable"


class ExperimentStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SatelliteModel(BaseModel):
    id: str
    name: str
    tle_line1: str = ""
    tle_line2: str = ""
    omm: dict[str, Any] | None = None
    constellation_id: str = ""
    orbit_plane: int = 0


class GroundStationModel(BaseModel):
    constellation_id: str = ""
    research_metadata: dict[str, Any] = Field(default_factory=dict)
    id: str
    name: str
    latitude: float
    longitude: float
    altitude_m: float = 0
    antenna_gain_dbi: float = 30
    visible_elevation_deg: float = 10


class LinkConfigModel(BaseModel):
    id: str
    link_type: LinkType
    source_id: str
    target_id: str
    center_freq_hz: float
    bandwidth_hz: float
    tx_power_dbm: float
    modulation: str = "QPSK"
    data_rate_bps: float = 1e9


class JammerModel(BaseModel):
    id: str
    name: str = ""
    source_type: JammerSourceType
    jamming_style: JammingStyle
    latitude: float = 0
    longitude: float = 0
    altitude_m: float = 0
    tx_power_dbm: float = 30
    center_freq_hz: float = 14e9
    bandwidth_hz: float = 50e6
    antenna_gain_dbi: float = 10
    trajectory: list[dict[str, Any]] = Field(default_factory=list)


class ScenarioConfig(BaseModel):
    orbit_only: bool = False
    scenario_id: str
    name: str
    epoch: datetime
    time_step_sec: int = 5
    simulation_duration_sec: int = 5400
    constellation: dict[str, Any]
    ground_stations: list[GroundStationModel]
    default_links: dict[str, float]
    jammers: list[JammerModel]
    sparse_observation_rate: float = 0.25
    external_sources: dict[str, Any] = Field(default_factory=dict)


class Position3D(BaseModel):
    entity_id: str
    latitude: float
    longitude: float
    altitude_m: float
    velocity_m_s: float = 0


class LinkState(BaseModel):
    link_id: str
    link_type: LinkType
    source_id: str
    target_id: str
    visible: bool
    center_freq_hz: float = 0
    bandwidth_hz: float = 0
    range_km: float = 0
    elevation_deg: float = 0
    doppler_hz: float = 0
    propagation_delay_ms: float = 0
    rx_power_dbm: float = -999
    interference_power_dbm: float = -999
    sinr_db: float = -999
    risk_level: RiskLevel = RiskLevel.NORMAL
    confidence: float = 1.0


class SpectrumGrid(BaseModel):
    freq_bins_hz: list[float]
    power_dbm: list[float]
    observed_mask: list[bool]
    completed: bool = False
    completion_method: str = "none"


class SituationalSnapshot(BaseModel):
    timestamp: datetime
    scenario_id: str
    links: list[LinkState]
    spectrum_grid: SpectrumGrid | None = None
    jammers: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str = ""


class AlertTrace(BaseModel):
    jammer_ids: list[str] = Field(default_factory=list)
    reason: str = ""
    rules_applied: list[str] = Field(default_factory=list)


class DownstreamAlert(BaseModel):
    alert_id: str
    alert_type: str
    timestamp: datetime
    risk_level: RiskLevel
    affected_links: list[str] = Field(default_factory=list)
    affected_freq_hz: list[float] = Field(default_factory=list)
    recommended_freq_hz: float | None = None
    prediction_confidence: float = 0.0
    trace: AlertTrace = Field(default_factory=AlertTrace)


class PredictionRequest(BaseModel):
    horizon_sec: int = Field(300, ge=30, le=600)
    link_ids: list[str] | None = None


class CompletionRequest(BaseModel):
    observation_rate: float = Field(0.25, ge=0.05, le=1.0)
    method: str = Field("auto", pattern="^(auto|kriging|idw|knn|mae)$")


class ImportScenarioRequest(BaseModel):
    path: str = "tle_online_v0.json"


class DataSourceInfo(BaseModel):
    source: str
    source_type: str
    fetched_at: datetime | None = None
    cache_status: str = "not_applicable"
    data_version: str = ""
    detail: str = ""
    cache_path: str | None = None


class DataMode(str, Enum):
    SIMULATION = "simulation"
    ONLINE = "online"


class ScenarioModeRequest(BaseModel):
    mode: DataMode


class ScenarioModeStatus(BaseModel):
    mode: DataMode
    scenario_path: str
    scenario_id: str = ""
    scenario_name: str = ""
    data_sources: list[DataSourceInfo] = Field(default_factory=list)



class ExperimentConfig(BaseModel):
    name: str = "research_validation"
    scenario_paths: list[str] = Field(default_factory=lambda: ["tle_online_v0.json"], min_length=1)
    observation_rates: list[float] = Field(default_factory=lambda: [0.25], min_length=1)
    prediction_horizons_sec: list[int] = Field(default_factory=lambda: [300], min_length=1)
    completion_methods: list[str] = Field(
        default_factory=lambda: ["kriging", "idw", "knn", "mae"],
        min_length=1,
    )
    prediction_method: str = "orbit_extrapolation+lstm_trend"
    simulation_steps: int = Field(12, ge=1, le=240)
    step_delta_sec: int | None = Field(None, ge=1, le=600)
    export_formats: list[str] = Field(default_factory=lambda: ["json", "csv"])
    notes: str = ""


class ExperimentMetricSummary(BaseModel):
    visible_link_count: int = 0
    average_sinr_db: float = 0.0
    low_sinr_link_ratio: float = 0.0
    completion_error_rmse: float = 0.0
    coverage_rate: float = 0.0
    observation_missing_rate: float = 0.0
    future_high_risk_identification_accuracy: float = 0.0
    prediction_confidence_mean: float = 0.0
    prediction_confidence_min: float = 0.0
    prediction_confidence_max: float = 0.0
    alert_count: int = 0
    severe_alert_ratio: float = 0.0
    alert_lead_time_sec: float = 0.0
    spectrum_occupancy_ratio: float = 0.0


class ExperimentComparisonEntry(BaseModel):
    completion_method: str
    prediction_method: str
    metrics: ExperimentMetricSummary
    notes: list[str] = Field(default_factory=list)


class ExperimentTimeSeriesPoint(BaseModel):
    timestamp: datetime
    visible_link_count: int = 0
    average_sinr_db: float = 0.0
    high_risk_link_count: int = 0
    alert_count: int = 0
    severe_alert_count: int = 0


class ExperimentCaseResult(BaseModel):
    case_id: str
    scenario_path: str
    scenario_id: str
    observation_rate: float
    prediction_horizon_sec: int
    simulation_steps: int
    step_delta_sec: int
    data_sources: list[DataSourceInfo] = Field(default_factory=list)
    time_series: list[ExperimentTimeSeriesPoint] = Field(default_factory=list)
    comparison: list[ExperimentComparisonEntry] = Field(default_factory=list)
    summary: ExperimentMetricSummary = Field(default_factory=ExperimentMetricSummary)
    conclusion: str = ""
    artifacts: dict[str, str] = Field(default_factory=dict)


class ExperimentAggregateSummary(BaseModel):
    total_cases: int = 0
    scenarios: list[str] = Field(default_factory=list)
    best_completion_method: str = ""
    average_metrics: ExperimentMetricSummary = Field(default_factory=ExperimentMetricSummary)
    comparison_table: list[dict[str, Any]] = Field(default_factory=list)
    generated_summary: str = ""


class ExperimentExportPayload(BaseModel):
    experiment_id: str
    format: str
    generated_at: datetime
    file_path: str
    download_path: str
    record_count: int = 0


class ExperimentRun(BaseModel):
    experiment_id: str
    status: ExperimentStatus = ExperimentStatus.CREATED
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    config: ExperimentConfig
    total_cases: int = 0
    completed_cases: int = 0
    cases: list[ExperimentCaseResult] = Field(default_factory=list)
    summary: ExperimentAggregateSummary = Field(default_factory=ExperimentAggregateSummary)
    exports: list[ExperimentExportPayload] = Field(default_factory=list)
    result_dir: str = ""
    errors: list[str] = Field(default_factory=list)
