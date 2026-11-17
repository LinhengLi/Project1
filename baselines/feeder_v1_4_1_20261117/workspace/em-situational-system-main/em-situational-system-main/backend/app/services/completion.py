"""Sparse situational completion: Kriging/IDW/KNN baselines + Masked Autoencoder."""

from __future__ import annotations

import numpy as np
from scipy.interpolate import griddata
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel

from app.models.schemas import SpectrumGrid
from app.services.physics import PhysicsValidator

try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:
    class SimpleMAE(nn.Module):
        def __init__(self, size: int):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(size, 128),
                nn.ReLU(),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, size),
            )

        def forward(self, x):
            return self.net(x)


class CompletionEngine:
    """Complete sparse spectrum maps using baselines or neural model."""

    def __init__(self):
        self.physics = PhysicsValidator()
        self._mae_model = None

    def complete(self, grid: SpectrumGrid, method: str = "auto") -> SpectrumGrid:
        if method == "auto":
            method = "kriging"
        observed = np.array(grid.observed_mask)
        power = np.array(grid.power_dbm, dtype=float)
        freqs = np.array(grid.freq_bins_hz, dtype=float)

        valid = observed & (power > -500)
        if valid.sum() < 3:
            return grid

        if method == "idw":
            completed_power = self._idw(freqs, power, valid)
            used = "idw"
        elif method == "knn":
            completed_power = self._knn(freqs, power, valid, k=5)
            used = "knn"
        elif method == "mae":
            completed_power = self._mae_complete(freqs, power, valid)
            used = "mae"
        else:
            completed_power = self._kriging(freqs, power, valid)
            used = "kriging"

        _, violations = self.physics.validate_spectrum_completion(
            freqs.tolist(), completed_power.tolist()
        )
        if violations and method not in ("kriging", "idw"):
            completed_power = self._kriging(freqs, power, valid)
            used = "kriging_fallback"

        rmse = self._rmse(power[valid], completed_power[valid])
        return SpectrumGrid(
            freq_bins_hz=freqs.tolist(),
            power_dbm=completed_power.tolist(),
            observed_mask=observed.tolist(),
            completed=True,
            completion_method=f"{used}(rmse_obs={rmse:.2f})",
        )

    def build_sparse_grid(self, grid: SpectrumGrid, observation_rate: float, seed: int = 0) -> SpectrumGrid:
        full = np.array(grid.power_dbm, dtype=float)
        n = len(full)
        rng = np.random.default_rng(seed)
        existing_observed = np.array(grid.observed_mask, dtype=bool) & (full > -500)
        if existing_observed.any():
            candidate_idx = np.where(existing_observed)[0]
            keep_count = max(1, int(round(len(candidate_idx) * observation_rate)))
            keep_idx = rng.choice(candidate_idx, size=min(keep_count, len(candidate_idx)), replace=False)
            mask = np.zeros(n, dtype=bool)
            mask[keep_idx] = True
        else:
            mask = rng.random(n) < observation_rate
            if not mask.any():
                mask[0] = True
        return SpectrumGrid(
            freq_bins_hz=grid.freq_bins_hz,
            power_dbm=[float(p) if mask[i] else -999.0 for i, p in enumerate(full)],
            observed_mask=mask.tolist(),
        )

    def benchmark_methods(
        self,
        grid: SpectrumGrid,
        observation_rate: float = 0.25,
        methods: tuple[str, ...] = ("kriging", "idw", "knn", "mae"),
        seed: int = 0,
    ) -> dict[str, dict]:
        full = np.array(grid.power_dbm, dtype=float)
        sparse = self.build_sparse_grid(grid, observation_rate=observation_rate, seed=seed)
        mask = np.array(sparse.observed_mask)
        valid_full = full > -500
        unobserved = valid_full & ~mask
        results: dict[str, dict] = {}
        for method in methods:
            try:
                comp = self.complete(sparse.model_copy(deep=True), method=method)
                pred = np.array(comp.power_dbm, dtype=float)
                rmse = float(np.sqrt(np.mean((pred[unobserved] - full[unobserved]) ** 2))) if unobserved.any() else 0.0
                results[method] = {
                    "rmse": rmse,
                    "coverage_rate": float(mask.mean()),
                    "observation_missing_rate": float(1.0 - mask.mean()),
                    "completed": True,
                    "completion_method": comp.completion_method,
                }
            except Exception as exc:
                results[method] = {
                    "rmse": -1.0,
                    "coverage_rate": float(mask.mean()),
                    "observation_missing_rate": float(1.0 - mask.mean()),
                    "completed": False,
                    "error": str(exc),
                }
        base = results.get("kriging", {}).get("rmse", 1) or 1
        for value in results.values():
            rmse = value.get("rmse", base)
            if rmse >= 0 and base > 0:
                value["improvement_vs_kriging_pct"] = (base - rmse) / base * 100
        return results

    def _kriging(self, freqs, power, valid) -> np.ndarray:
        x_obs = freqs[valid].reshape(-1, 1)
        y_obs = power[valid]
        x_std = x_obs.std() + 1e-6
        x_norm = (x_obs - x_obs.mean()) / x_std
        kernel = RBF(length_scale=1.0) + WhiteKernel(noise_level=1.0)
        gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, alpha=1e-6)
        try:
            gp.fit(x_norm, y_obs)
            x_all = (freqs.reshape(-1, 1) - x_obs.mean()) / x_std
            pred, _ = gp.predict(x_all, return_std=True)
        except Exception:
            pred = griddata(x_obs.flatten(), y_obs, freqs, method="linear", fill_value=-120)
            pred = np.nan_to_num(pred, nan=-120)
        return np.clip(pred, -150, 30)

    def _idw(self, freqs, power, valid, power_exp: float = 2) -> np.ndarray:
        result = power.copy()
        obs_f, obs_p = freqs[valid], power[valid]
        for i in range(len(freqs)):
            if valid[i]:
                continue
            d = np.abs(obs_f - freqs[i]) + 1e-6
            w = 1 / (d**power_exp)
            result[i] = np.sum(w * obs_p) / np.sum(w)
        return result

    def _knn(self, freqs, power, valid, k: int = 5) -> np.ndarray:
        result = power.copy()
        obs_f, obs_p = freqs[valid], power[valid]
        for i in range(len(freqs)):
            if valid[i]:
                continue
            d = np.abs(obs_f - freqs[i])
            idx = np.argsort(d)[: min(k, len(obs_f))]
            result[i] = np.mean(obs_p[idx])
        return result

    def _mae_complete(self, freqs, power, valid) -> np.ndarray:
        if not TORCH_AVAILABLE:
            return self._kriging(freqs, power, valid)
        n = len(freqs)
        normalized = np.clip((power - (-120)) / 150, 0, 1).astype(np.float32)
        mask = valid.astype(np.float32)
        x = torch.from_numpy(normalized.reshape(1, -1))
        m = torch.from_numpy(mask.reshape(1, -1))
        if self._mae_model is None:
            self._mae_model = SimpleMAE(n)
            self._train_mae(self._mae_model, n)
        self._mae_model.eval()
        with torch.no_grad():
            out = self._mae_model(x * m).numpy()[0]
        reconstructed = out * 150 + (-120)
        result = power.copy()
        result[~valid] = reconstructed[~valid]
        return np.clip(result, -150, 30)

    def _train_mae(self, model, n: int, steps: int = 80):
        opt = torch.optim.Adam(model.parameters(), lr=1e-3)
        loss_fn = nn.MSELoss()
        model.train()
        for _ in range(steps):
            batch = torch.randn(8, n) * 0.3 + 0.5
            batch = batch.clamp(0, 1)
            mask = (torch.rand(8, n) > 0.25).float()
            out = model(batch * mask)
            loss = loss_fn(out * (1 - mask), batch * (1 - mask))
            opt.zero_grad()
            loss.backward()
            opt.step()

    @staticmethod
    def _rmse(a, b) -> float:
        return float(np.sqrt(np.mean((a - b) ** 2)))

    def compare_methods(self, grid: SpectrumGrid) -> dict:
        return self.benchmark_methods(grid, observation_rate=0.25)
