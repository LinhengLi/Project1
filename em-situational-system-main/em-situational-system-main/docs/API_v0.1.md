# 模块接口说明 v0.1

## 系统定位

侦察型态势感知平台，输出结构化数据给下游「数据变传管控 / 频谱资管 / 链路重构」模块。

## REST API 基址

`/api/v1`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/scenario/load` | 加载演示场景 |
| GET | `/scenario/current` | 当前场景配置 |
| POST | `/simulation/step` | 仿真步进 |
| GET | `/situational/current` | 当前态势（支持 sparse 参数） |
| POST | `/situational/complete` | 稀疏态势补全 |
| POST | `/situational/predict` | 动态预测 |
| GET | `/alerts` | 告警列表 |
| GET | `/risk/assessment` | 5 维风险评估 |
| GET | `/constellation/positions` | 卫星位置 |
| GET | `/downstream/payload` | 下游模块对接载荷 |
| GET | `/completion/compare` | 补全方法对照实验 |
| GET | `/stream/alerts` | SSE 实时告警流 |

## 下游 API 字段（DownstreamAlert）

```json
{
  "alert_id": "a1b2c3d4",
  "alert_type": "realtime",
  "timestamp": "2026-06-15T12:00:00Z",
  "risk_level": "severe",
  "affected_links": ["sgl_sat_00_00_gs_beijing"],
  "affected_freq_hz": [14000000000],
  "recommended_freq_hz": 14200000000,
  "prediction_confidence": 0.85,
  "trace": {
    "jammer_ids": ["jam_ground_fixed"],
    "reason": "链路 SINR=3.2dB...",
    "rules_applied": ["sinr_risk_classification"]
  }
}
```

## 模块插件接口（预留）

各功能模块遵循统一输入/输出：

- 输入：JSON，含 `timestamp`, `scenario_id`, 模块专属参数
- 输出：JSON，含 `status`, `confidence`, `result`, `trace`
- 错误码：400 参数错误，500 内部错误

## 数据格式

支持 JSON / CSV 导出；大文件 IQ 摘要使用 HDF5/Parquet（后续扩展）。
