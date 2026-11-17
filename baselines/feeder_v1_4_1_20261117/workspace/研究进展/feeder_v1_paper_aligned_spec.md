# Feeder v1 — 对齐 Liu et al. (2025) 的参数与实现约定

本文件配合 `feeder_v1_paper_aligned_parameters.json` 使用。所有“论文值”来自 arXiv:2505.12429 第 II、III、IV、VI 节及 Table I；原文的卫星数/站点数并非本项目数据规模。项目新增的 OneWeb/GSO、17.8–18.6 GHz 和具体网关位置属于扩展场景。

## 1. 冻结场景与论文的共同物理基线

| 项目 | 推荐值 | 依据/说明 |
|---|---|---|
| 传输方向 | NGSO 卫星 → NGSO Gateway | 论文第 II 节，下行 feeder link |
| 工作卫星 | Starlink Gen1+Gen2 / OneWeb | 用户的双系统外推；公开轨道数据不证明正在运营或实际载荷参数 |
| 参考 GSO | 12 颗候选 GSO，各绑定一个地表参考接收点 | 用户场景假设；12 候选的具体频谱业务尚需进一步证实 |
| NGSO 网关 | Starlink 6 个 + OneWeb 6 个 | 用户当前小规模场景；尚非 115 站复现 |
| 每网关工作天线 | 8（敏感性：4、8、16、25） | 论文设 C = N_at；25 为论文一个重点实验点 |
| 选星方式 | 各网关轮流选择当前最高仰角且未被占用的可见卫星 | 论文第 II 节；默认每卫星仅接一条活动 feeder，属于归一化假设 |
| 最低仰角 | 40° | 论文 Table I |
| 星上每载波发射功率 | 12 dBW（约15.85 W）| 论文 Table I；注意不是 12 dBm 或 12 W |
| 星上峰值发射天线增益 | 35 dBi | 论文 Table I |
| 网关峰值接收天线增益 | 45.76 dBi | 论文 Table I |
| 接收天线噪声温度 | 398 K | 论文 Table I |
| NGSO 发射方向图 | ITU-R S.1528-0（论文采用的历史版本）| 只设置 35 dBi 常数不足以得到可靠干扰结果 |
| NGSO Gateway 接收方向图 | ITU-R S.1428-1 | 需正确实现所有角度分段，区分线性倍数和 dBi |
| 传播模型 | SGP4 + 基于真实站址的动态地心坐标/仰角/斜距 | 对真实 TLE/OMM 进行传播；基础损耗只算 FSPL，额外大气/降雨损耗作为扩展 |
| 干扰比门限 | I/N > −12.2 dB 时计入 LF | 论文定义；不等于本频段 GSO EPFD 法规定值 |
| 构图初筛门限 | −13 dB | 论文 VI 节；还需逐接收链路自适应阈值 |
| 步长及窗长 | 10 s / 2 h，共 720 槽 | 论文设置和冻结场景一致 |
| 量化功率 | 所有干扰先按 **瓦** 累加，最后取 10log10 | 禁止直接相加 dBW/dBm 或 dB |

## 2. 三套频率模式，优先保留冻结场景

| 模式 | 中心频率 | 总带宽 | 8 个子信道 | 用途 |
|---|---:|---:|---:|---|
| `frozen_main_800mhz` | 18.2 GHz | 800 MHz（17.8–18.6） | 100 MHz | **主实验、UI 保持不变** |
| `paper_bandwidth_adapted_500mhz` | 18.2 GHz | 500 MHz（17.95–18.45） | 62.5 MHz | 研究频段内对齐论文的带宽和 C=N_at |
| `paper_physics_reference_20ghz` | 20 GHz | 500 MHz | 62.5 MHz | 单独物理参数控制组；不声称是合法共用 17.8–18.6 场景 |

对照模式不要混为一谈。原论文是 20 GHz、500 MHz；800 MHz 的冻结设置是合理的研究扩展，但**不能写成论文原始参数**。三种模式都保持单位载波发射功率 12 dBW 作第一组公平对照；如果未来研究固定功率谱密度，应增设单独实验。

热噪声功率 `N = k_B × 398 × B`：

- 100 MHz 子信道：`N ≈ 5.495 × 10^-13 W = −122.600 dBW`。
- 62.5 MHz 子信道：`N ≈ 3.434 × 10^-13 W = −124.642 dBW`。

## 3. 活动链路与物理干扰计算

**每个时隙先形成活动链路，而非把 10,611+651 颗卫星全部设为发射。**

1. SGP4 计算卫星位置；在地面网关处计算仰角，筛选 `elevation ≥ 40°`。
2. 按网关轮询最高仰角原则，每站选取不超过 8 颗可见卫星，不复用已占用卫星。
3. 每条活动链路的发射天线指向其服务网关；接收天线指向其服务卫星。
4. 每个干扰对重新计算两个离轴角：星上发射端的“服务网关方向 vs 受扰网关方向”与受扰网关接收端的“服务卫星方向 vs 干扰卫星方向”。
5. 使用论文 Eq.(1) 计算单路干扰，用 Eq.(2) 对相同子信道的干扰源进行**线性功率求和**，然后用 Eq.(3) 求 I/N。
6. 区分 `同网关站内`、`同运营商跨网关站`、`Starlink–OneWeb 跨系统` 干扰。图染色使用共同的 8 色池，不能分别给两运营商独立且互不干扰的颜色表。

在每站满载 8 个波束且共用 8 频点时，即使每个站内互不重频，也可能在邻近的 Starlink–OneWeb 两站间产生不可避免的跨系统重频；**算法的改善目标是减少失败而不保证零冲突。**

两个关键公式（W 为瓦，天线增益为线性倍数）：

`I[j→i] = P_j × G_t,j(theta_tx) × G_r,i(theta_rx) × (lambda / (4π d_ji))²`

`LF_Rate(t) = count{active feeder i : sum_j I[j→i]/(k_B T_n B) > 10^(−12.2/10)} / count(active feeder)`

### 对图算法的参数锁定

| 算法 | 论文 VI 节参数 |
|---|---|
| Generalized Global (GG) | `N_GG = 100` 次独立试探 |
| Clique-Based Tabu Search (CTS) | `N_init = 2000`, `N_candidate = 500`, `N_iter = 250`, `N_neighbor = 10` |
| 图构建 | 初筛 `I/N = −13 dB`，然后为每条受扰链路计算适配门限（论文 Eq.(6)(7)）；不能把固定 −13 dB 当成所有最终图边的唯一判据 |
| TCFA-GG / TCFA-CTS | 同一卫星连续两槽仍服务同一网关时优先继承颜色；交换频率时计 FSR |
| 基线 | Random / Global / GG / CTS，再增加 TCFA-GG / TCFA-CTS |

算法时间应在**同一电脑同一语言同一图规模**上比较；论文中 GG 约 6 ms、CTS 约 20 ms 的数值不能直接移植到本系统。对于大规模仿真，优先先运行单时隙、10 分钟，再扩展 720 槽和站数。

## 4. GSO独立EPFD模块（限值候选待逐项核验）

研究频段 17.8–18.6 GHz 适用 ITU《无线电规则》2024版 **Article 22 Table 22-1B** 的非 GSO 系统对 GSO FSS 地球站下行 `EPFD↓` 限制（视具体业务/法规条件）。下述表号及示例限值尚未逐项完成官方原表核验，不应直接作为可执行法规判据。应另设 GSO 接收机模块：

- GSO 参考接收天线始终指向其关联的 GSO 卫星；该方向决定每颗 NGSO 干扰卫星进入 GSO 参考天线的离轴角。
- 用 ITU-R S.1428-1 参考天线方向图计算 `G_rx(theta)/G_rx,max`。
- 将卫星每个已占用子信道的功率按平坦谱模型折算到 **40 kHz** 或 **1 MHz**；绝不能将 100 MHz 总功率直接同 40 kHz EPFD 门限比较。
- 分别汇报 Starlink 单系统、OneWeb 单系统及两系统合计 EPFD，正式监管合规分析需要核对对应的单系统和多系统条件。
- 参考地面接收天线口径可先用 **1 m**，再用 **2 m、5 m** 做敏感性分析。Article 22 的门限不仅是一个 dB 数，而是“EPFD 阈值—满足时间百分比”的曲线；例如 1 m/40 kHz 参考曲线包含 `−175.4 dB(W/m²)` 对应 90% 时间与 `−164 dB(W/m²)` 对应 100% 时间两档。
- 2 小时窗口只能做瞬时 EPFD 风险筛查；**不能声称完成符合 ITU-R S.1503 的长期 EPFD 正式合规审查**。

## 5. 上线之前必须核验的输入真实性

1. OneWeb冻结基线现有6个FCC坐标来源站：原4站加Clewiston（DOC-355200A1）和Santa Paula（DOC-358650A1，后续授权DOC-376504A1）；全量场景为6个FCC+7个区域仿真位置。FCC许可或申请均不等于当前运营证明。
2. 12 个 GSO 候选卫星来自 GEO 轨道组，不代表每颗已确认在 17.8–18.6 GHz 从事 FSS；在前端加 `band_licensed_verified` 标志。
3. Starlink 社区站址可能是区域级近似坐标，需保留 source + accuracy 字段。
4. 将卫星 EPOCH、仿真统一 UTC 起点与 TLE/OMM 源文件 SHA256 保存到运行元数据；不能把 10611 目录数量当成每槽在发射数。
5. 论文纯算法基线对比可以沿用 12 dBW 等归一化参数；它们**不是 Starlink/OneWeb 真实设备披露的逐星逐站功率和增益**。

## 6. 实现顺序

(1) 真轨道 + 网关可见性 → (2) 活动链路选星 → (3) 完整天线方向图/双离轴角 → (4) 干扰矩阵、I/N 与 LF → (5) 图构建与 Random/Global → (6) GG/CTS → (7) TCFA 与 FSR → (8) GSO EPFD 筛查和长期统计 → (9) 站址规模扩展与 AI 加速。

### 参考

- Liu et al., *Time-Continuous Frequency Allocation for Feeder Links of Mega Constellations with Multi-Antenna Gateway Stations*, arXiv:2505.12429, 2025. https://arxiv.org/abs/2505.12429
- ITU-R S.1528（2025论文使用 2001 版本；2026 年存在更新版）. https://www.itu.int/rec/R-REC-S.1528/en
- ITU-R S.1428-1，FSS 地球站参考天线方向图。
- ITU《Radio Regulations》2024，Article 22 Table 22-1B. https://search.itu.int/history/HistoryDigitalCollectionDocLibrary/1.49.48.en.101.pdf
- FCC SpaceX 17.8–18.6 GHz 地球站许可示例. https://docs.fcc.gov/public/attachments/DA-24-222A1.pdf
- FCC OneWeb 17.8–18.6 GHz 地球站许可示例. https://docs.fcc.gov/public/attachments/DOC-400804A1.pdf


## 7. 本轮状态更新（2026-11-15）

- 原feeder_v1快照及哈希保持不变，本材料作为v1.1派生实现规范。主频率仍为800MHz模式。
- 网关按ID升序固定轮询，每轮每站取最高仰角未占用的同系统卫星；相同仰角按卫星ID升序。Global参考试探次数也记录为100，GG扰动、CTS禁忌长度等尚需补核。
- 本文列出的EPFD限值数组尚未逐行核对官方原表，不作为可执行法规门限；表号、口径、参考带宽、百分比语义均须核实。
- 1m/2m/5m是后续EPFD参考天线配置；原GSO场景3.5m不静默改写。
- 720个区间与含起点721个快照分开；无保留关联时FSR为NA。
- 当前开始几何和选星阶段，不启用方向图、聚合干扰、着色或EPFD限值。
