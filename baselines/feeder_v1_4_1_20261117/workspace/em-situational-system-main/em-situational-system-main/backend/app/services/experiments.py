"""Experiment orchestration, evaluation, replay, and export services."""

from __future__ import annotations

import csv
import json
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from itertools import product
from pathlib import Path

from app.config import settings
from app.db import (
    RedisStateStore,
    clear_experiment_records,
    delete_experiment_record,
    load_experiment_records,
    upsert_experiment_record,
)
from app.models.schemas import (
    ExperimentAggregateSummary,
    ExperimentCaseResult,
    ExperimentComparisonEntry,
    ExperimentConfig,
    ExperimentExportPayload,
    ExperimentMetricSummary,
    ExperimentRun,
    ExperimentStatus,
    ExperimentTimeSeriesPoint,
    PredictionRequest,
    RiskLevel,
    SituationalSnapshot,
)
from app.services.scenario_manager import SimulationManager


HIGH_RISK_LEVELS = {RiskLevel.MODERATE.value, RiskLevel.SEVERE.value, RiskLevel.UNAVAILABLE.value}


class ExperimentService:
    def __init__(self, storage_dir: Path | None = None, enable_persistence: bool = True):
        self.storage_dir = storage_dir or settings.data_dir / "experiments"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._runs: dict[str, ExperimentRun] = {}
        self._progress_store = RedisStateStore(settings.redis_url)
        self.enable_persistence = enable_persistence
        self._load_existing_runs()

    def create_experiment(self, config: ExperimentConfig) -> ExperimentRun:
        experiment_id = datetime.now(timezone.utc).strftime("exp_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
        result_dir = self.storage_dir / experiment_id
        result_dir.mkdir(parents=True, exist_ok=True)
        run = ExperimentRun(
            experiment_id=experiment_id,
            created_at=datetime.now(timezone.utc),
            config=config,
            result_dir=str(result_dir),
        )
        self._runs[experiment_id] = run
        self._persist_run(run)
        self._set_progress(run, current_case=None)
        return run

    def list_experiments(self) -> list[ExperimentRun]:
        return sorted(self._runs.values(), key=lambda run: run.created_at, reverse=True)

    def get_experiment(self, experiment_id: str) -> ExperimentRun:
        if experiment_id not in self._runs:
            raise KeyError(experiment_id)
        return self._runs[experiment_id]

    def run_experiment(self, experiment_id: str) -> ExperimentRun:
        run = self.get_experiment(experiment_id)
        run.status = ExperimentStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        run.finished_at = None
        run.cases = []
        run.summary = ExperimentAggregateSummary()
        run.exports = []
        run.errors = []

        case_specs = list(product(
            run.config.scenario_paths,
            run.config.observation_rates,
            run.config.prediction_horizons_sec,
        ))
        run.total_cases = len(case_specs)
        run.completed_cases = 0
        self._persist_run(run)
        self._set_progress(run, current_case=None)

        try:
            for index, (scenario_path, observation_rate, horizon_sec) in enumerate(case_specs, start=1):
                case_id = f"case_{index:03d}"
                self._set_progress(run, current_case=case_id)
                try:
                    case = self._execute_case(
                        run=run,
                        case_id=case_id,
                        scenario_path=scenario_path,
                        observation_rate=observation_rate,
                        horizon_sec=horizon_sec,
                    )
                    run.cases.append(case)
                except Exception as exc:
                    run.errors.append(f"{case_id}: {exc}")
                run.completed_cases = index
                self._persist_run(run)

            try:
                run.summary = self._aggregate_summary(run.cases)
            except Exception as exc:
                run.errors.append(f"summary: {exc}")
                run.summary = ExperimentAggregateSummary(generated_summary="Experiment completed but summary aggregation failed.")

            run.status = ExperimentStatus.COMPLETED if not run.errors else ExperimentStatus.FAILED
            for export_format in run.config.export_formats:
                try:
                    run.exports.append(self._generate_export(run, export_format))
                except Exception as exc:
                    run.errors.append(f"export:{export_format}: {exc}")
                    run.status = ExperimentStatus.FAILED
        finally:
            run.finished_at = datetime.now(timezone.utc)
            self._persist_run(run)
            self._set_progress(run, current_case=None)
        return run

    def replay_case(self, experiment_id: str, case_id: str) -> dict:
        run = self.get_experiment(experiment_id)
        case = next((item for item in run.cases if item.case_id == case_id), None)
        if case is None:
            raise KeyError(case_id)
        return {
            "experiment_id": experiment_id,
            "case_id": case_id,
            "scenario_id": case.scenario_id,
            "observation_rate": case.observation_rate,
            "prediction_horizon_sec": case.prediction_horizon_sec,
            "time_series": [point.model_dump(mode="json") for point in case.time_series],
            "comparison": [entry.model_dump(mode="json") for entry in case.comparison],
            "conclusion": case.conclusion,
        }

    def export_experiment(self, experiment_id: str, export_format: str) -> ExperimentExportPayload:
        run = self.get_experiment(experiment_id)
        payload = self._generate_export(run, export_format)
        run.exports = [item for item in run.exports if item.format != export_format] + [payload]
        self._persist_run(run)
        return payload

    def get_progress(self, experiment_id: str) -> dict:
        run = self.get_experiment(experiment_id)
        progress = self._progress_store.get_progress(experiment_id) or {}
        return {
            "experiment_id": experiment_id,
            "status": run.status.value,
            "completed_cases": run.completed_cases,
            "total_cases": run.total_cases,
            **progress,
        }

    def delete_experiment(self, experiment_id: str) -> dict:
        run = self.get_experiment(experiment_id)
        result_dir = Path(run.result_dir)
        if result_dir.exists():
            shutil.rmtree(result_dir)
        if self.enable_persistence:
            delete_experiment_record(experiment_id)
            self._progress_store.delete_progress(experiment_id)
        del self._runs[experiment_id]
        return {"deleted": True, "experiment_id": experiment_id}

    def clear_experiments(self) -> dict:
        for experiment_id in list(self._runs.keys()):
            result_dir = Path(self._runs[experiment_id].result_dir)
            if result_dir.exists():
                shutil.rmtree(result_dir)
            if self.enable_persistence:
                self._progress_store.delete_progress(experiment_id)
        self._runs.clear()
        if self.enable_persistence:
            clear_experiment_records()
            self._progress_store.clear_progress()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        return {"deleted": True, "count": 0}

    def artifact_path(self, experiment_id: str, artifact_name: str) -> Path:
        run = self.get_experiment(experiment_id)
        path = Path(run.result_dir) / artifact_name
        if not path.exists():
            raise FileNotFoundError(artifact_name)
        return path

    def _execute_case(
        self,
        run: ExperimentRun,
        case_id: str,
        scenario_path: str,
        observation_rate: float,
        horizon_sec: int,
    ) -> ExperimentCaseResult:
        manager = SimulationManager()
        scenario = manager.load_scenario(scenario_path)
        step_delta_sec = run.config.step_delta_sec or scenario.time_step_sec

        time_series: list[ExperimentTimeSeriesPoint] = []
        for _ in range(run.config.simulation_steps):
            snap = manager.step(step_delta_sec)
            alerts = manager.get_alerts(1000)
            time_series.append(self._time_series_point(snap, alerts))

        final_snapshot = manager.get_snapshot()
        if final_snapshot.spectrum_grid is None or manager.completion is None or manager.situational is None:
            raise RuntimeError("Experiment case requires spectrum grid and completion engine")

        benchmark = manager.completion.benchmark_methods(
            final_snapshot.spectrum_grid,
            observation_rate=observation_rate,
            methods=tuple(run.config.completion_methods),
            seed=0,
        )
        prediction = manager.predict(PredictionRequest(horizon_sec=horizon_sec))
        future_snapshot = manager.situational.generate(manager.current_time + timedelta(seconds=horizon_sec))

        base_metrics = self._link_metrics(final_snapshot)
        prediction_metrics = self._prediction_metrics(prediction, future_snapshot)
        risk_metrics = self._risk_metrics(manager.get_alerts(1000))

        comparison: list[ExperimentComparisonEntry] = []
        for method in run.config.completion_methods:
            method_result = benchmark.get(method, {})
            metrics = ExperimentMetricSummary(
                **base_metrics,
                completion_error_rmse=round(float(method_result.get("rmse", -1.0)), 4),
                coverage_rate=round(float(method_result.get("coverage_rate", 0.0)), 4),
                observation_missing_rate=round(float(method_result.get("observation_missing_rate", 0.0)), 4),
                **prediction_metrics,
                **risk_metrics,
            )
            notes: list[str] = []
            if method_result.get("error"):
                notes.append(method_result["error"])
            comparison.append(ExperimentComparisonEntry(
                completion_method=method,
                prediction_method=run.config.prediction_method,
                metrics=metrics,
                notes=notes,
            ))

        summary = self._best_metrics(comparison)
        conclusion = self._case_conclusion(case_id, scenario.scenario_id, horizon_sec, comparison)
        case = ExperimentCaseResult(
            case_id=case_id,
            scenario_path=scenario_path,
            scenario_id=scenario.scenario_id,
            observation_rate=observation_rate,
            prediction_horizon_sec=horizon_sec,
            simulation_steps=run.config.simulation_steps,
            step_delta_sec=step_delta_sec,
            data_sources=manager.get_data_sources(),
            time_series=time_series,
            comparison=comparison,
            summary=summary,
            conclusion=conclusion,
        )
        artifacts = self._write_case_artifacts(run, case)
        case.artifacts.update(artifacts)
        return case

    def _write_case_artifacts(self, run: ExperimentRun, case: ExperimentCaseResult) -> dict[str, str]:
        result_dir = Path(run.result_dir)
        case_json = result_dir / f"{case.case_id}.json"
        case_json.write_text(json.dumps(case.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")

        timeseries_csv = result_dir / f"{case.case_id}_timeseries.csv"
        with timeseries_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "timestamp",
                "visible_link_count",
                "average_sinr_db",
                "high_risk_link_count",
                "alert_count",
                "severe_alert_count",
            ])
            writer.writeheader()
            for point in case.time_series:
                writer.writerow(point.model_dump(mode="json"))

        return {
            "case_json": str(case_json),
            "timeseries_csv": str(timeseries_csv),
        }

    def _aggregate_summary(self, cases: list[ExperimentCaseResult]) -> ExperimentAggregateSummary:
        if not cases:
            return ExperimentAggregateSummary(generated_summary="No successful experiment cases.")

        comparison_rows: list[dict] = []
        metric_field_names = list(ExperimentMetricSummary.model_fields.keys())
        metric_accumulator = {name: [] for name in metric_field_names}
        method_scores: dict[str, list[float]] = {}

        for case in cases:
            for entry in case.comparison:
                metrics_dict = entry.metrics.model_dump()
                for name, value in metrics_dict.items():
                    metric_accumulator[name].append(value)
                method_scores.setdefault(entry.completion_method, []).append(entry.metrics.completion_error_rmse)
                comparison_rows.append({
                    "case_id": case.case_id,
                    "scenario_id": case.scenario_id,
                    "scenario_path": case.scenario_path,
                    "observation_rate": case.observation_rate,
                    "prediction_horizon_sec": case.prediction_horizon_sec,
                    "completion_method": entry.completion_method,
                    "prediction_method": entry.prediction_method,
                    **metrics_dict,
                })

        integer_metric_names = {"visible_link_count", "alert_count"}
        average_metrics = ExperimentMetricSummary(**{
            name: int(round(sum(values) / len(values))) if values and name in integer_metric_names else round(sum(values) / len(values), 4) if values else 0.0
            for name, values in metric_accumulator.items()
        })
        best_completion_method = ""
        if method_scores:
            best_completion_method = min(
                method_scores.items(),
                key=lambda item: sum(item[1]) / len(item[1]) if item[1] else float("inf"),
            )[0]

        generated_summary = (
            f"Ran {len(cases)} experiment cases across {len({case.scenario_id for case in cases})} scenarios. "
            f"Best completion method: {best_completion_method or 'n/a'}. "
            f"Average visible links: {average_metrics.visible_link_count:.1f}, "
            f"average SINR: {average_metrics.average_sinr_db:.2f} dB, "
            f"future high-risk identification accuracy: {average_metrics.future_high_risk_identification_accuracy:.2%}."
        )

        return ExperimentAggregateSummary(
            total_cases=len(cases),
            scenarios=sorted({case.scenario_id for case in cases}),
            best_completion_method=best_completion_method,
            average_metrics=average_metrics,
            comparison_table=comparison_rows,
            generated_summary=generated_summary,
        )

    def _generate_export(self, run: ExperimentRun, export_format: str) -> ExperimentExportPayload:
        result_dir = Path(run.result_dir)
        result_dir.mkdir(parents=True, exist_ok=True)
        generated_at = datetime.now(timezone.utc)

        if export_format == "csv":
            file_name = "comparison.csv"
            file_path = result_dir / file_name
            rows = run.summary.comparison_table
            fieldnames = list(rows[0].keys()) if rows else [
                "case_id",
                "scenario_id",
                "scenario_path",
                "observation_rate",
                "prediction_horizon_sec",
                "completion_method",
                "prediction_method",
            ]
            with file_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            record_count = len(rows)
        else:
            file_name = "experiment.json"
            file_path = result_dir / file_name
            file_path.write_text(json.dumps(run.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
            record_count = len(run.cases)
            export_format = "json"

        return ExperimentExportPayload(
            experiment_id=run.experiment_id,
            format=export_format,
            generated_at=generated_at,
            file_path=str(file_path),
            download_path=f"/api/v1/experiments/{run.experiment_id}/artifacts/{file_name}",
            record_count=record_count,
        )

    @staticmethod
    def _time_series_point(snap: SituationalSnapshot, alerts) -> ExperimentTimeSeriesPoint:
        visible_links = [link for link in snap.links if link.visible]
        high_risk_links = [link for link in visible_links if link.risk_level.value in HIGH_RISK_LEVELS]
        severe_alert_count = sum(1 for alert in alerts if alert.risk_level in (RiskLevel.SEVERE, RiskLevel.UNAVAILABLE))
        avg_sinr = sum(link.sinr_db for link in visible_links) / len(visible_links) if visible_links else 0.0
        return ExperimentTimeSeriesPoint(
            timestamp=snap.timestamp,
            visible_link_count=len(visible_links),
            average_sinr_db=round(avg_sinr, 4),
            high_risk_link_count=len(high_risk_links),
            alert_count=len(alerts),
            severe_alert_count=severe_alert_count,
        )

    @staticmethod
    def _link_metrics(snap: SituationalSnapshot) -> dict[str, float | int]:
        visible_links = [link for link in snap.links if link.visible]
        avg_sinr = sum(link.sinr_db for link in visible_links) / len(visible_links) if visible_links else 0.0
        low_sinr_ratio = sum(1 for link in visible_links if link.sinr_db < 10) / len(visible_links) if visible_links else 0.0
        occupancy_ratio = 0.0
        if snap.spectrum_grid and snap.spectrum_grid.power_dbm:
            occupancy_ratio = sum(1 for power in snap.spectrum_grid.power_dbm if power > -110) / len(snap.spectrum_grid.power_dbm)
        return {
            "visible_link_count": len(visible_links),
            "average_sinr_db": round(avg_sinr, 4),
            "low_sinr_link_ratio": round(low_sinr_ratio, 4),
            "spectrum_occupancy_ratio": round(occupancy_ratio, 4),
        }

    @staticmethod
    def _prediction_metrics(prediction: dict, future_snapshot: SituationalSnapshot) -> dict[str, float]:
        prediction_map = {
            entry["link_id"]: entry
            for entry in prediction.get("link_predictions", [])
        }
        future_links = {
            link.link_id: link
            for link in future_snapshot.links
            if link.visible
        }
        common_ids = sorted(set(prediction_map) & set(future_links))
        if not common_ids:
            return {
                "future_high_risk_identification_accuracy": 0.0,
                "prediction_confidence_mean": 0.0,
                "prediction_confidence_min": 0.0,
                "prediction_confidence_max": 0.0,
                "alert_lead_time_sec": 0.0,
            }

        correct = 0
        matched_high_risk = False
        confidences = []
        for link_id in common_ids:
            predicted = prediction_map[link_id]
            actual = future_links[link_id]
            predicted_high_risk = predicted.get("predicted_risk_level") in HIGH_RISK_LEVELS
            actual_high_risk = actual.risk_level.value in HIGH_RISK_LEVELS
            correct += int(predicted_high_risk == actual_high_risk)
            matched_high_risk = matched_high_risk or (predicted_high_risk and actual_high_risk)
            confidences.append(float(predicted.get("prediction_confidence", 0.0)))

        return {
            "future_high_risk_identification_accuracy": round(correct / len(common_ids), 4),
            "prediction_confidence_mean": round(sum(confidences) / len(confidences), 4),
            "prediction_confidence_min": round(min(confidences), 4),
            "prediction_confidence_max": round(max(confidences), 4),
            "alert_lead_time_sec": float(prediction.get("horizon_sec", 0) if matched_high_risk else 0.0),
        }

    @staticmethod
    def _risk_metrics(alerts) -> dict[str, float | int]:
        if not alerts:
            return {
                "alert_count": 0,
                "severe_alert_ratio": 0.0,
            }
        severe_count = sum(1 for alert in alerts if alert.risk_level in (RiskLevel.SEVERE, RiskLevel.UNAVAILABLE))
        return {
            "alert_count": len(alerts),
            "severe_alert_ratio": round(severe_count / len(alerts), 4),
        }

    @staticmethod
    def _best_metrics(comparison: list[ExperimentComparisonEntry]) -> ExperimentMetricSummary:
        scored = [entry for entry in comparison if entry.metrics.completion_error_rmse >= 0]
        if not scored:
            return comparison[0].metrics if comparison else ExperimentMetricSummary()
        return min(scored, key=lambda entry: entry.metrics.completion_error_rmse).metrics

    @staticmethod
    def _case_conclusion(
        case_id: str,
        scenario_id: str,
        horizon_sec: int,
        comparison: list[ExperimentComparisonEntry],
    ) -> str:
        if not comparison:
            return f"{case_id} produced no comparison rows."
        best = ExperimentService._best_metrics(comparison)
        best_method = min(
            comparison,
            key=lambda entry: entry.metrics.completion_error_rmse if entry.metrics.completion_error_rmse >= 0 else float("inf"),
        ).completion_method
        return (
            f"{scenario_id} @ {horizon_sec}s horizon: best completion method {best_method}, "
            f"RMSE {best.completion_error_rmse:.3f}, "
            f"high-risk accuracy {best.future_high_risk_identification_accuracy:.2%}, "
            f"alerts {best.alert_count}."
        )

    def _persist_run(self, run: ExperimentRun) -> None:
        result_dir = Path(run.result_dir)
        result_dir.mkdir(parents=True, exist_ok=True)
        run_file = result_dir / "run.json"
        run_file.write_text(json.dumps(run.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
        if self.enable_persistence:
            upsert_experiment_record(run.model_dump(mode="json"))

    def _load_existing_runs(self) -> None:
        if self.enable_persistence:
            for payload in load_experiment_records():
                try:
                    run = ExperimentRun(**payload)
                except Exception:
                    continue
                self._runs[run.experiment_id] = run
        for run_file in self.storage_dir.glob("*/run.json"):
            try:
                run = ExperimentRun(**json.loads(run_file.read_text(encoding="utf-8")))
            except Exception:
                continue
            self._runs[run.experiment_id] = run
        for experiment_id, run in list(self._runs.items()):
            healed = self._heal_stale_run(run)
            self._runs[experiment_id] = healed
            if self.enable_persistence:
                upsert_experiment_record(healed.model_dump(mode="json"))

    def _heal_stale_run(self, run: ExperimentRun) -> ExperimentRun:
        if not run.cases:
            run.cases = self._load_cases_from_artifacts(run)
        if run.status != ExperimentStatus.RUNNING:
            if not run.summary.total_cases and run.cases:
                run.summary = self._aggregate_summary(run.cases)
                self._persist_run(run)
            return run
        if run.total_cases and run.completed_cases >= run.total_cases:
            if not run.summary.total_cases and run.cases:
                run.summary = self._aggregate_summary(run.cases)
            if not run.finished_at:
                run.finished_at = datetime.now(timezone.utc)
            if not run.exports:
                for export_format in run.config.export_formats:
                    try:
                        run.exports.append(self._generate_export(run, export_format))
                    except Exception as exc:
                        run.errors.append(f"heal_export:{export_format}: {exc}")
            run.status = ExperimentStatus.COMPLETED if not run.errors else ExperimentStatus.FAILED
            self._persist_run(run)
            self._set_progress(run, current_case=None)
        return run

    def _load_cases_from_artifacts(self, run: ExperimentRun) -> list[ExperimentCaseResult]:
        result_dir = Path(run.result_dir)
        cases: list[ExperimentCaseResult] = []
        for case_file in sorted(result_dir.glob("case_*.json")):
            if case_file.name.endswith("_timeseries.csv"):
                continue
            try:
                cases.append(ExperimentCaseResult(**json.loads(case_file.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return cases
    def _set_progress(self, run: ExperimentRun, current_case: str | None) -> None:
        if not self.enable_persistence:
            return
        self._progress_store.set_progress(
            run.experiment_id,
            {
                "current_case": current_case,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )


experiment_service = ExperimentService()



