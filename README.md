# Q/V 馈电链路研究平台

## 建模原则

采用真实轨道驱动的假设通信场景。真实轨道不代表卫星实际具备 Q/V 载荷；通信参数、网关与业务配置必须单独记录假设。目标是算法评估，而非复现 Starlink 运行系统。

总体架构：星座 → 网关 → 链路容量 → 业务需求 → 调度 → QoS 评估。此处是逻辑模块划分，不要求模块按此顺序单向执行。

## 第一阶段已实现

- 本地 CelesTrak TLE（两行或含名称的三行）与 JSON OMM 快照输入。
- SGP4 传播，统一返回 UTC 时刻、卫星 ID、TEME 位置（km）与速度（km/s）。
- WGS84 地面站／用户区域代表点的方位角、仰角、斜距及最低仰角可见性。
- `OrbitProvider` 接口允许未来接入解析 Walker 星座；尚未实现 Walker 输入适配器。

## 安装与测试

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[test]"
.venv\Scripts\python -m pytest
```

## 使用

```python
from datetime import datetime, timezone
from qv_sim import Sgp4Constellation, GroundSite, observe

orbits = Sgp4Constellation.from_file("data/starlink.json")
site = GroundSite("GS-01", latitude_deg=30, longitude_deg=110,
                  altitude_km=0.1, min_elevation_deg=10)
time = datetime(2026, 11, 5, tzinfo=timezone.utc)  # 应匹配所用快照历元
visible = [result for state in orbits.states_at(time)
           if (result := observe(site, state)).visible]
```

示例坐标仅为假设，不是真实网关。项目尚未下载真实星座数据，`data/starlink.json` 需自行准备。

## 数据与精度边界

- 星座快照应同时记录来源 URL、获取时间、文件哈希、轨道历元和卫星筛选规则。保存原文件，不覆盖历史实验数据。
- OMM 支持 CelesTrak 的地心、TEME、UTC、SGP4 JSON 记录；其精简 JSON 省略的标准字段按该约定解释。
- 时间必须包含时区，输入统一转为 UTC。传播失败直接报出卫星 ID，不静默跳过。
- 当前 TEME 到地固系采用 GMST 旋转，以 UTC 近似 UT1，忽略极移；不适合精密指向与监管级干扰验证。
- 当前可见性仅为几何可见性，不代表容量可用或满足频谱保护条件；未包含地形遮挡、折射与降雨。
- 尚未设置轨道数据过期策略；正式实验应限制传播时刻与轨道历元的间隔并检查敏感性。
- 后续同类 TLE/OMM 星座可只更换输入；若采用其他动力学模型、载荷或覆盖能力，需要相应适配器或独立通信配置，不能保证任意输入文件直接互换。

下一阶段：真实快照及元数据管理、时间序列可见窗口、Walker 适配器、独立网关配置与容量模型。

## Walker 首轮实验（新增）

已实现 `WalkerDelta` 参数化生成器及二体传播，采用固定历元平均赤道惯性系，不将其声称为真实 TEME；24 小时可见性计算中近似作为日期平均赤道系处理，忽略岁差、章动和 J2。统一状态为保持兼容沿用 `position_teme_km` / `velocity_teme_km_s` 字段名，但必须结合 `frame` 理解；后续高精度研究应重构为中性字段并采用严格坐标转换。

```powershell
.venv\Scripts\python scripts/analyze_visibility.py
```

输出位于 `results/first_visibility/`，包括配置、10 秒计数序列、可见窗口、统计 JSON、Markdown 报告及 SVG 曲线。默认 120/12/1、53°、550 km，北京和上海，2026-11-05 UTC 起算 24 小时。脚本再次运行会更新该固定实验目录。

Walker 约定：轨道面 RAAN 为 `offset + 360*p/P`，面内初始纬度幅角为 `phase_offset + 360*s/(T/P) + 360*F*p/T`；地球引力常数 398600.4418 km³/s²，参考赤道半径 6378.137 km。

## 真实轨道八网关扫描

主实验输入为 `realdatas/starlink_real_1600_gp.json` 与 `realdatas/gateway_main_8.json`。前者是轨道子集，不代表完整星座或已核实的Q/V载荷；后者参考第三方公开站址，设备和频率授权未经确认。

```powershell
.venv\Scripts\python -m pip install -e ".[analysis]"
.venv\Scripts\python scripts/scan_gateways.py
```

扫描2026-11-05起72小时，60秒采样，并分别汇总前24小时和全部72小时。Skyfield调用SGP4并计算WGS84地面站的无折射地平坐标，使用内置时间尺度，不下载外部极移表。站高暂设0米。输出 `results/real_gateway_scan/` 内的配置与输入哈希、计数CSV、逐站/逐站对/集群统计JSON及报告。重复运行会更新该目录。

25°为主门限，10°/20°/30°用于敏感性比较。72小时是固定快照的外推检查，必须结合GP历元年龄解释；60秒采样不能证明连续覆盖。当前脚本不提取精细窗口、不计算用户共同覆盖，也不将多站共享卫星直接解释为容量竞争。
