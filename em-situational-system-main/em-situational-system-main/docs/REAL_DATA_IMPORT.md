# 真实外部数据导入说明

当前系统支持把外部真实数据源配置到场景文件中，方式与 CelesTrak TLE 导入类似：场景只保存数据源地址，运行时由后端拉取、缓存、解析，并把数据源元信息写入 API 输出。

## 支持的数据源

在场景 JSON 中增加 `external_sources`：

```json
{
  "constellation": {
    "type": "tle",
    "limit": 40,
    "tle_source": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
  },
  "external_sources": {
    "tolerance_sec": 60,
    "spectrum_observations": {
      "source": "../real/spectrum_observations_demo.csv"
    },
    "link_observations": {
      "source": "https://example.org/link_observations.csv"
    },
    "jammers": {
      "source": "../real/jammers_demo.json",
      "mode": "append"
    }
  }
}
```

- `tle_source`：真实卫星 TLE，可使用 CelesTrak URL 或本地文件。
- `spectrum_observations`：真实频谱观测，支持 CSV/JSON。
- `link_observations`：真实链路状态日志，支持 CSV/JSON。
- `jammers`：真实干扰源/干扰事件，支持 CSV/JSON；`mode` 可为 `append` 或 `replace`。
- `tolerance_sec`：按仿真时间匹配真实观测的最大时间差；设为 `null` 表示始终使用最近观测。

## 频谱观测字段

CSV 表头或 JSON 对象字段支持以下别名：

| 含义 | 字段 |
| --- | --- |
| 时间 | `timestamp`, `time`, `datetime`, `observed_at` |
| 频率 | `freq_hz`, `frequency_hz`, `center_freq_hz`, `frequency` |
| 功率 | `power_dbm`, `psd_dbm`, `rx_power_dbm`, `value_dbm` |

示例：

```csv
timestamp,freq_hz,power_dbm
2026-06-16T12:00:00Z,14000000000,-72.5
2026-06-16T12:00:00Z,26000000000,-81.2
```

导入后，态势快照中的 `spectrum_grid` 会优先使用真实观测点，未观测频点标记为缺失，可继续调用 `/api/v1/situational/complete` 做补全。

## 链路观测字段

`link_observations` 至少需要 `link_id`，其余字段会覆盖仿真计算值：

- `visible`
- `center_freq_hz`
- `bandwidth_hz`
- `range_km`
- `elevation_deg`
- `doppler_hz`
- `propagation_delay_ms`
- `rx_power_dbm`
- `interference_power_dbm`
- `sinr_db`
- `risk_level`
- `confidence`

如果提供 `sinr_db` 但不提供 `risk_level`，系统会按 SINR 阈值自动换算风险等级。

## 缓存与回退

- URL 数据会缓存到 `data/cache/<dataset_type>/`。
- 网络可用时使用 fresh 数据。
- 网络失败但存在缓存时，自动回退到 stale cache。
- `/api/v1/scenario/data-sources` 会返回每个真实数据源的 `source_type`、`cache_status`、`data_version` 和 `cache_path`。

## 示例场景

仓库内置了一个示例：

- `data/scenarios/real_data_demo_v0.json`
- `data/real/spectrum_observations_demo.csv`
- `data/real/jammers_demo.json`

加载方式：

```powershell
POST /api/v1/scenario/load
{"path":"real_data_demo_v0.json"}
```

然后调用：

```powershell
GET /api/v1/situational/current
POST /api/v1/situational/complete
POST /api/v1/situational/predict
GET /api/v1/risk/assessment
```

此时轨道来自 CelesTrak TLE，频谱态势来自外部观测文件，干扰源来自外部 JSON。
