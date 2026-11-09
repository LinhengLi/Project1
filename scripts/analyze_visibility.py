"""Run reproducible Beijing/Shanghai point visibility analysis."""
import csv
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from statistics import mean

from qv_sim import GroundSite, observe
from qv_sim.walker import WalkerDelta


def main():
    output = Path("results/first_visibility")
    output.mkdir(parents=True, exist_ok=True)
    epoch = datetime(2026, 11, 5, tzinfo=timezone.utc)
    constellation = WalkerDelta(epoch)
    step, duration = 10, 86400
    sites = [GroundSite("Beijing", 39.90, 116.40), GroundSite("Shanghai", 31.23, 121.47)]
    masks = [10, 20, 30]
    config = {"walker": {**asdict(constellation), "epoch": epoch.isoformat()},
              "sites": [asdict(s) for s in sites], "masks_deg": masks,
              "step_seconds": step, "duration_seconds": duration,
              "time_interval": "[epoch, epoch + duration)",
              "model": "two-body; fixed mean equator of epoch approximated as equator of date; UTC~UT1; no J2/polar motion"}
    (output / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    counts = {(s.site_id, m): [] for s in sites for m in masks}
    active, windows = {}, []

    def close(key, end, right_censored=False):
        start = active.pop(key)
        site, mask, satellite = key
        windows.append([site, mask, satellite, (epoch + timedelta(seconds=start)).isoformat(),
                        (epoch + timedelta(seconds=end)).isoformat(), end-start,
                        start == 0, right_censored])

    with (output / "counts.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["time_utc", "site", "mask_deg", "visible_count"])
        for second in range(0, duration, step):
            time = epoch + timedelta(seconds=second)
            states = constellation.states_at(time)
            for site in sites:
                elevations = {state.satellite_id: observe(site, state).elevation_deg for state in states}
                for mask in masks:
                    visible = {sat for sat, elev in elevations.items() if elev >= mask}
                    counts[site.site_id, mask].append(len(visible))
                    writer.writerow([time.isoformat(), site.site_id, mask, len(visible)])
                    for sat in visible:
                        active.setdefault((site.site_id, mask, sat), second)
                    for key in list(active):
                        if key[:2] == (site.site_id, mask) and key[2] not in visible:
                            close(key, second)
    for key in list(active):
        close(key, duration, True)
    with (output / "windows.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["site", "mask_deg", "satellite", "start_utc", "end_utc", "duration_s", "left_censored", "right_censored"])
        writer.writerows(windows)
    summary = []
    for (site, mask), values in counts.items():
        complete = [w[5] for w in windows if w[0] == site and w[1] == mask and not w[6] and not w[7]]
        summary.append({"site": site, "mask_deg": mask, "min": min(values), "mean": mean(values),
                        "max": max(values), "zero_fraction": values.count(0)/len(values),
                        "at_least_two_fraction": sum(v >= 2 for v in values)/len(values),
                        "histogram": dict(sorted(Counter(values).items())),
                        "complete_windows": len(complete),
                        "mean_complete_window_s": mean(complete) if complete else None})
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    # Dependency-free SVG; all samples are retained, not downsampled.
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="650" viewBox="0 0 1100 650">',
           '<rect width="1100" height="650" fill="white"/>']
    colors = {10: "#1565c0", 20: "#e65100", 30: "#388e3c"}
    for panel, site in enumerate(sites):
        top = 45 + panel * 315
        svg.append(f'<text x="70" y="{top-15}" font-family="sans-serif">{site.site_id}: visible satellites (UTC, 2026-11-05)</text>')
        for count in range(7):
            y = top + 210 - count*35
            svg.append(f'<path d="M70 {y} H1030" stroke="#dddddd"/><text x="45" y="{y+5}">{count}</text>')
        for hour in range(0, 25, 3):
            x = 70 + hour*40
            svg.append(f'<text x="{x}" y="{top+235}">{hour:02d}</text>')
        for mask in masks:
            points = " ".join(f"{70+i*step/3600*40:.2f},{top+210-v*35}" for i, v in enumerate(counts[site.site_id, mask]))
            svg.append(f'<polyline points="{points}" fill="none" stroke="{colors[mask]}" stroke-width="1"/>')
            svg.append(f'<text x="{700 + masks.index(mask)*110}" y="{top-15}" fill="{colors[mask]}">{mask} deg</text>')
    svg.append('</svg>')
    (output / "visible_counts.svg").write_text("\n".join(svg), encoding="utf-8")
    lines = ["# 首轮几何可见性分析", "", "120/12/1，53°，550 km；24 h，10 s 采样。", "",
             "|观测点|最低仰角|最少|平均|最多|零可见占比|至少两星占比|完整窗口平均秒数|",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in summary:
        lines.append(f"|{row['site']}|{row['mask_deg']}°|{row['min']}|{row['mean']:.3f}|{row['max']}|{row['zero_fraction']:.2%}|{row['at_least_two_fraction']:.2%}|{row['mean_complete_window_s']:.1f}|")
    lines += ["", "时间区间为左闭右开；窗口由采样估计，边界分辨率为10秒。跨实验边界的窗口标记截断，不参与完整窗口均值。",
              "", "仅为单点几何覆盖，不包含容量、干扰、天气、用户—GS共同可见性。单一历元与相位的24小时结果不代表长期性能。"]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
