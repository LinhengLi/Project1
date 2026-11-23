# Q/V 馈电链路研究平台

## 组会后研究方向（2026-11-19）

当前拟推进：单一NGSO运营商内部馈电资源在线决策，在GSO保护约束下保障地区性、时段性突发业务QoS，并明确星上算力和状态通信限制。业务方向、QoS及星上可获信息待建模锁定；尚未实现新算法。详细见[主线调整与最小实验方案](研究进展/研究主线调整_单运营商突发业务与星上在线决策_20261119.md)。

下述双系统结果属于已冻结的历史研究，不覆盖或重新解释其结论。

## 当前进度（2026-11-17）

当前研究主线为NGSO–NGSO–GSO异构星座馈电链路干扰评价与共存管理。**V1.5已冻结**；后续实验和说明材料独立保存，不覆盖冻结快照。

- **V1.4.1**：完成NGSO–NGSO干扰及GSO参考窗口EPFD评价，冻结文件位于`baselines/feeder_v1_4_1_20261117/`。
- **V1.5**：最大仰角选星、站内无重频随机子信道分配，两小时、10秒采样间隔、720帧开环干扰计算；冻结文件位于`baselines/feeder_v1_5_20261117/`，工作结果位于`results/feeder_openloop_v1_5/`。
- **独立首帧分频扫描**：实测201个候选，完整干扰计算累计181.17秒，平均0.901秒。失败链路从19条降至最低1条，但没有候选满足全部GSO研究门限。单源下界进一步支持当前固定关联、功率及保护设置下的仅分频不可行性，不能泛化到其他场景。
- **下一步问题**：联合选星与子信道分配，先建立精确缓存、增量更新等强基线，再验证动态干扰评价和决策算法；尚未实现该联合优化求解器。
- **周报材料**：期刊调研、通俗故事、三分钟讲稿、算法图和扫描证据均已归档。

### 入口与资料

| 内容 | 入口 |
|---|---|
| 各版本及巨型星座可视化 | [可视化页面说明](可视化页面/README.md)；双击`可视化页面/启动可视化.cmd`启动本地服务 |
| 可离线打开的课题故事、研究证据和期刊地图 | [独立HTML](可视化页面/课题故事与期刊调研_20261117/index.html) |
| 2026-11-18周报 | [周报说明](周报素材/20261118_V1_5首帧分频扫描/周报说明.md) |
| 首帧扫描原始结果及复现信息 | [实验说明](results/feeder_first_frame_scan_20261117/周报说明.md) |
| 联合优化问题草案 | [问题推导草案](研究进展/选星与子信道联合优化_问题推导草案_20261117.md) |
| 投稿期刊范围与来源 | [期刊调研](周报素材/20261118_V1_5首帧分频扫描/通信期刊投稿范围与课题定位_20261117.md) |

GitHub代码浏览器不会直接运行HTML；请下载或克隆仓库后在本地打开。GSO结果采用特定配置下的瞬时参考上限，不代表真实运营系统的完整长期合规判断。201是实验设置的搜索预算，不是任意优化算法必须评价的次数。

源代码、输入、结果、冻结快照和研究材料一并归档；Python虚拟环境、缓存、运行日志与本机凭据由`.gitignore`排除。早期研究仍使用下述依赖与脚本，后续馈电实验的具体环境和执行方法以各版本说明、冻结清单为准。

## 早期研究与方法记录

以下保留项目早期阶段的实现和模型边界；其中“下一阶段”“尚未”等描述属于当时状态，当前进度以上方摘要及版本说明为准。

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

## 连续窗口 QoS 对照

```powershell
.venv\Scripts\python scripts/experiment_temporal.py
```

需要已有 `results/real_gateway_refinement/candidate_links.csv.gz` 和 optimization 依赖。脚本先按链路数据选择两段不重叠的连续 120 秒窗口（低候选下降恢复与相对稳定对照），不对稀疏数据插值。每 5 秒重新分配业务速率，比较 5/30 秒关联重选、四种策略与每类 0.6/0.9 Gbit/s 需求，保障固定为 0.5/0.3 Gbit/s。使用原有 loss10 链路容量，不施加额外收紧或频谱保护。沿用假设的每星 1.5 Gbit/s 共享容量。

输出 `results/temporal_qos/`：`config.json` 固定窗口、源哈希和口径，`summary.csv` / `report.md` 为 30/60 秒完整滑动窗口结果表，`traces.csv` 为逐站时序，`under_rate_runs.csv` 为连续欠速及链路失效诊断，`timeline.png` / `.svg` 展示瓶颈站候选数、两类速率、保障线及切换时刻。达标率是每站窗口平均高优先级服务速率达标的比例，不是逐时刻达标率；无排队或积压模型，不能解释为时延或端到端 QoS。联合策略是当前状态的逐快照优化，不使用未来信息，也没有切换惩罚；多解导致的关联切换属于这一版本策略的实际输出。

## 30 秒业务保障前瞻选星

```powershell
.venv\Scripts\python scripts/experiment_lookahead.py
```

复用 `results/temporal_qos/config.json` 的窗口并验证候选源文件哈希，不重新选窗。`src/qv_sim/holding.py` 一次求解六个 5 秒步的关联与速率，按“逐站高优交付缺口、普通交付缺口、总交付”进行词典序优化，30 秒目标固定为 15/9 Gbit。对照组包括现有瞬时吞吐/加权 QoS，以及使用相同未来信息的周期吞吐/周期 QoS。未来信息来自保存数据，是理想信息实验，不是预测精度验证。

模型定义见 `results/HOLDING_QOS_MODEL.md`；结果见 `results/holding_qos/report.md`，同目录保留 `summary.csv`、逐站 `periods.csv`、逐步 `traces.csv` 与固定关联/自由重选下界 `diagnostics.csv`。本轮不包含物理频谱保护约束；当前→未来 QoS 同时改变信息和目标，不能解释为纯信息收益。周期内速率可能集中分配，对齐达标不代表瞬时服务平滑。

## 馈电上行发射限值配对实验

```powershell
.venv\Scripts\python scripts/experiment_spectrum.py
```

复用保持周期实验的冻结窗口和候选链路。限值开关两组均重新计算 50.0 GHz、250 MHz 容量，再比较前瞻吞吐优先和前瞻 QoS 优先。五档合成泄漏抑制度覆盖端口限值生效前后。条款、单位与物理假设见 [频谱保护资料](research_sources/spectrum_protection.md)，QoS 资料见 [网络侧 QoS 资料](research_sources/network_qos.md)。[实验报告](results/spectrum_protection/report.md) 同目录保存配置、逐边容量、业务结果和配对差值。实验对应单地球站发射端口限值场景。

### 按 ITU 参考大气和发射谱重算

```powershell
.venv\Scripts\python scripts/experiment_spectrum.py --refined
```

该模式使用 P.676-13 逐谱线计算气体衰减，采用 P.835-7 参考大气和 P.453-14 折射率。可用 `--residual-loss-db` 单独设置其他损耗余量，默认 0 dB。除原抑制度扫描外，还积分 SM.1541-7 FSS 掩模以评估通用包络情景。若有设备谱，传入 `--port-spectrum path/to/spectrum.csv`，CSV 提供按频率升序的 `frequency_hz` 和 `psd_w_per_hz`，覆盖带内与保护带的积分范围。实验取带内与保护带的功率比，将谱形归一到同一标称发射功率。

输出见 [重算报告](results/spectrum_refined/report.md) 和同目录的逐边容量与业务结果。气体衰减使用参考大气，掩模使用平坦带内谱和单信道指配假设。参数依据见 [ITU 与 3GPP 文献摘记](research_sources/itu_3gpp_model_refinement.md)。
