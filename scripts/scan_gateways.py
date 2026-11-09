"""Offline SGP4 + Skyfield topocentric scanning of the eight candidate sites."""
import csv
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path

import numpy as np
import skyfield
from skyfield.api import EarthSatellite, load, wgs84
from sgp4 import omm
from sgp4.api import Satrec


def main():
    output = Path("results/real_gateway_scan")
    output.mkdir(parents=True, exist_ok=True)
    orbit_path = Path("realdatas/starlink_real_1600_gp.json")
    site_path = Path("realdatas/gateway_main_8.json")
    records = json.loads(orbit_path.read_text(encoding="utf-8-sig"))
    sites = json.loads(site_path.read_text(encoding="utf-8-sig"))["sites"]
    ids = [str(r["NORAD_CAT_ID"]) for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate NORAD IDs")
    start = datetime(2026, 11, 5, tzinfo=timezone.utc)
    step, hours = 60, 72
    dates = [start + timedelta(seconds=i*step) for i in range(hours*3600//step)]
    ts = load.timescale(builtin=True)
    times = ts.from_datetimes(dates)
    observers = [wgs84.latlon(s["lat_deg"], s["lon_deg"], elevation_m=0) for s in sites]
    elevations = np.empty((len(sites), len(records), len(dates)), dtype=np.float32)
    for k, fields in enumerate(records):
        model = Satrec()
        omm.initialize(model, fields)
        satellite = EarthSatellite.from_satrec(model, ts)
        state = satellite.at(times)
        messages = state.message
        if messages is not None and any(m for m in np.atleast_1d(messages)):
            raise RuntimeError(f"SGP4 failure for {ids[k]}: {messages}")
        for j, observer in enumerate(observers):
            alt, _, _ = (satellite - observer).at(times).altaz()
            elevations[j, k, :] = alt.degrees
        if (k+1) % 400 == 0:
            print(f"Propagated {k+1}/{len(records)} satellites", flush=True)
    if not np.isfinite(elevations).all():
        raise RuntimeError("Nonfinite elevation")
    epochs = [datetime.fromisoformat(r["EPOCH"]).replace(tzinfo=timezone.utc) for r in records]
    config = {"start_utc": start.isoformat(), "duration_hours": hours, "step_seconds": step,
              "interval": "left closed, right open", "satellites": len(records), "sites": sites,
              "masks_deg": [10, 20, 25, 30], "altitude_assumption_m": 0,
              "orbit_sha256": sha256(orbit_path.read_bytes()).hexdigest(),
              "sites_sha256": sha256(site_path.read_bytes()).hexdigest(),
              "epoch_min": min(epochs).isoformat(), "epoch_max": max(epochs).isoformat(),
              "max_age_days_at_last_sample": max((dates[-1]-e).total_seconds()/86400 for e in epochs),
              "geometry": "Skyfield SGP4/WGS84 topocentric altaz; no refraction; builtin timescale; no external polar-motion table",
              "skyfield_version": skyfield.__version__, "numpy_version": np.__version__}
    (output/"config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    summaries, pairs, clusters = [], [], []
    with (output/"counts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["utc", "station_id", "mask_deg", "visible_count"])
        for mask in config["masks_deg"]:
            visible = elevations >= mask
            count = visible.sum(axis=1)
            for j, site in enumerate(sites):
                writer.writerows((date.isoformat(), site["station_id"], mask, int(count[j,t])) for t,date in enumerate(dates))
            for period in [24, 72]:
                n = period*3600//step
                v = visible[:, :, :n]
                for j, site in enumerate(sites):
                    c = count[j,:n]
                    summaries.append({"hours": period, "mask_deg": mask, "station_id": site["station_id"],
                                      "name": site["name"], "min": int(c.min()), "mean": float(c.mean()),
                                      "max": int(c.max()), "zero_fraction": float((c==0).mean()),
                                      "at_least_two_fraction": float((c>=2).mean())})
                for a,b in combinations(range(len(sites)),2):
                    common = (v[a] & v[b]).sum(axis=0)
                    pairs.append({"hours": period, "mask_deg": mask, "a": sites[a]["station_id"],
                                  "b": sites[b]["station_id"], "mean_common": float(common.mean()),
                                  "min_common": int(common.min()), "max_common": int(common.max()),
                                  "zero_common_fraction": float((common==0).mean())})
                multiplicity = v.sum(axis=0)
                union = (multiplicity>=1).sum(axis=0)
                shared = (multiplicity>=2).sum(axis=0)
                clusters.append({"hours": period, "mask_deg": mask,
                                 "mean_union_satellites": float(union.mean()),
                                 "mean_shared_satellites": float(shared.mean()),
                                 "shared_satellite_time_fraction": float(shared.sum()/union.sum()) if union.sum() else None,
                                 "all_stations_nonzero_fraction": float((v.sum(axis=1)>0).all(axis=0).mean())})
    result = {"sites": summaries, "pairs": pairs, "cluster": clusters}
    (output/"summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = ["# 真实轨道八站 SGP4 扫描", "", "## 25° 主门限", "",
             "|时长h|站点|最少|平均|最多|零可见占比|", "|---:|---|---:|---:|---:|---:|"]
    for r in summaries:
        if r["mask_deg"] == 25:
            lines.append(f"|{r['hours']}|{r['station_id']} {r['name']}|{r['min']}|{r['mean']:.3f}|{r['max']}|{r['zero_fraction']:.2%}|")
    lines += ["", "## 集群汇总", "", "|时长h|门限°|平均可见星并集|平均多站共享星|共享卫星-时间占比|8站均有星占比|",
              "|---:|---:|---:|---:|---:|---:|"]
    for r in clusters:
        lines.append(f"|{r['hours']}|{r['mask_deg']}|{r['mean_union_satellites']:.2f}|{r['mean_shared_satellites']:.2f}|{r['shared_satellite_time_fraction']:.2%}|{r['all_stations_nonzero_fraction']:.2%}|")
    lines += ["", "几何共享不是已发生的容量竞争。60秒采样可能漏掉短窗口和短缺口，不能证明连续覆盖。",
              "72小时为固定GP快照的传播敏感性实验，不是重新获取轨道的三日实测。站高设为0，无折射、天气、容量、频谱及用户覆盖约束。",
              f"最后采样时刻相对最早轨道历元的间隔：{config['max_age_days_at_last_sample']:.3f}天。"]
    (output/"report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
