# 星间星地频轨电磁干扰态势感知与预测系统

低轨卫星电磁干扰态势感知与预测原型系统 —— 面向巨型星座的侦察型态势感知平台，提供星座轨道传播、电磁传播建模、多源干扰仿真、稀疏态势补全、动态预测、多维风险评估等能力，并通过三维地球与实时图表进行可视化呈现。

## 功能特性

### 核心仿真

- **星座生成与轨道传播** — 支持 Walker Delta 星座自动生成和基于真实 TLE 的卫星导入；圆形轨道解析传播与 Skyfield SGP4 高精度传播双模式
- **电磁传播建模** — 自由空间路径损耗 (FSPL) 计算，SINR（信号干扰噪声比）链路预算，支持多普勒频移、传播延迟解算
- **多源干扰机建模** — 6 种部署类型（地面固定/移动、空中、舰载、空间非合作、自然源），9 种干扰样式（同频、邻频、宽带拦阻、窄带点频、扫频、脉冲、欺骗、噪声、突发碰撞），支持移动轨迹插值
- **频谱冲突检测** — 同频/邻频/部分重叠自动判定，12–28 GHz 频段 64 区间频谱网格构建

### 态势感知

- **态势快照生成** — 实时合成链路状态、频谱占用网格、干扰源信息与人类可读解释
- **稀疏态势补全** — 4 种算法：Kriging（高斯过程回归）、IDW（反距离加权）、KNN（K 近邻）、MAE（掩码自编码器，PyTorch），支持自动选优与物理一致性校验回退
- **短期动态预测** — 30 s – 10 min 预测窗口，轨道外推 + 历史趋势双模融合，输出 SINR/风险等级/置信度
- **五维风险评估** — 链路维、频率维、区域维、卫星维、业务维综合评估
- **智能告警** — 实时告警、预测性告警、链路降级告警、频谱冲突告警，含可追溯原因与频率推荐

### 实验评测

- **批量实验编排** — 场景 × 观测率 × 预测时域 × 补全方法的笛卡尔积自动评估
- **13 项指标采集** — RMSE、MAE、补全时间、预测置信度等
- **实验回放** — 时间序列可视化，case 级别逐步回放
- **多格式导出** — JSON / CSV，支持结果 artifact 下载

### 可视化

- **CesiumJS 三维地球** — 卫星位置实时渲染、星间/星地链路风险着色、星下点轨迹、点击交互查询
- **ECharts 实时图表** — 态势趋势曲线、频谱瀑布图、SINR 柱状图
- **算法对比面板** — 补全方法 RMSE 对比条形图 + 数据表格

### 下游对接

- 标准化的 `DownstreamAlert` 结构输出，供数据变传管控 / 频谱资管 / 链路重构模块消费
- SSE 实时告警推送流

## 快速启动

### 环境要求

- Python 3.11+
- pip
- （可选）Docker & Docker Compose

### 本地开发启动

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

启动后自动加载默认场景 `tle_online_v0.json` 并执行 5 个初始仿真步。

**访问地址：**

| 页面 | 地址 |
|------|------|
| 前端可视化 | http://127.0.0.1:8000/static/index.html |
| API 文档 (Swagger) | http://127.0.0.1:8000/docs |
| 健康检查 | http://127.0.0.1:8000/health |

## 项目结构

```text
em-situational-system/
├── backend/                        # FastAPI 后端
│   ├── app/
│   │   ├── main.py                 # 应用入口，启动初始化
│   │   ├── config.py               # 配置管理 (pydantic-settings)
│   │   ├── db.py                   # 数据库与 Redis 状态存储
│   │   ├── api/
│   │   │   └── routes.py           # REST API 路由 (26 个端点)
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic 数据模型 (35+ 个)
│   │   └── services/               # 核心服务层
│   │       ├── scenario_manager.py # 仿真总控 (SimulationManager)
│   │       ├── orbit.py            # 轨道传播引擎
│   │       ├── propagation.py      # 电磁传播与 SINR 计算
│   │       ├── spectrum.py         # 频谱资源建模
│   │       ├── jammer.py           # 多源干扰机建模
│   │       ├── situational.py      # 态势快照生成
│   │       ├── completion.py       # 稀疏补全 (Kriging/IDW/KNN/MAE)
│   │       ├── prediction.py       # 短期预测
│   │       ├── risk.py             # 五维风险评估与告警
│   │       ├── knowledge.py        # 知识库 (规则/公式)
│   │       ├── data_source.py      # 数据源解析与缓存
│   │       ├── real_data.py        # 真实观测数据适配
│   │       ├── experiments.py      # 实验编排引擎
│   │       └── physics.py          # 物理一致性校验
│   ├── scripts/
│   │   ├── run_demo.py             # 端到端演示脚本
│   │   └── acceptance_tests.py     # 验收测试 (14 项)
│   ├── tests/                      # 单元测试
│   ├── Dockerfile                  # 多阶段构建
│   └── requirements.txt
├── frontend/
│   ├── static/
│   │   └── index.html              # SPA 前端 (CesiumJS + ECharts)
│   ├── Dockerfile                  # Nginx 静态服务
│   └── nginx.conf                  # 反向代理配置
├── data/
│   ├── scenarios/                  # 场景配置文件
│   │   ├── demo_leo_v0.json        # 50 星 Walker 星座演示场景
│   │   ├── tle_online_v0.json      # 在线 TLE 实时模式
│   │   ├── tle_demo_v0.json        # 离线 TLE 演示 (ISS/NOAA/FY-3C)
│   │   └── real_data_demo_v0.json  # 真实数据导入演示
│   ├── real/                       # 真实观测数据
│   ├── knowledge/                  # 知识库规则
│   ├── experiments/                # 实验输出目录
│   └── cache/                      # TLE/数据源缓存
├── schemas/                        # JSON Schema 定义
├── docs/                           # 文档
│   ├── API_v0.1.md                 # API 参考
│   ├── STARTUP.md                  # 启动说明
│   ├── DOCKER_DEPLOY.md            # Docker 部署指南
│   ├── DOCKER_OFFLINE.md           # 离线部署手册
│   ├── DOCKER_PRODUCTION_CHECKLIST.md  # 生产检查清单
│   ├── REAL_DATA_IMPORT.md         # 真实数据导入指南
│   └── ACCEPTANCE_REPORT.md        # 验收测试报告
├── scripts/
│   └── init.sql                    # PostgreSQL 初始化脚本
├── tools/                          # 辅助工具脚本
├── .github/workflows/              # CI/CD (Docker 构建 + 测试)
├── docker-compose.yml              # 四服务编排
├── docker.sh / docker.bat          # Docker 管理脚本
└── README.md
```

## 核心模块说明

### SimulationManager（仿真总控）

`backend/app/services/scenario_manager.py` — 全局单例，持有所有引擎引用并编排仿真生命周期：

- `load_scenario(path)` — 解析 JSON 场景，初始化轨道/传播/频谱/干扰/态势/补全/预测/风险全部引擎
- `step(delta_sec)` — 推进仿真时间，生成态势快照，触发告警评估
- `get_snapshot()` — 构建当前态势快照，支持稀疏观测、真实数据刷新
- `complete_situational(req)` — 应用稀疏感知后运行补全算法
- `predict(req)` — 对未来链路状态进行外推预测

### 数据模型

核心 Pydantic v2 模型（`backend/app/models/schemas.py`）：

| 模型 | 用途 |
|------|------|
| `SatelliteModel` | 卫星定义（ID、名称、TLE 双行轨道根数） |
| `GroundStationModel` | 地面站（经纬度、天线增益、最小仰角） |
| `LinkConfigModel` | 链路配置（ISL/SGL、频率、带宽、发射功率、调制方式） |
| `JammerModel` | 干扰机（6 种部署类型、9 种干扰样式、功率、轨迹） |
| `LinkState` | 链路实时状态（可见性、SINR、多普勒、延迟、风险等级） |
| `SpectrumGrid` | 频谱网格（频点、功率、观测掩码、补全标记） |
| `SituationalSnapshot` | 态势快照（时间戳、链路列表、频谱网格、干扰源） |
| `AlertTrace` | 告警追溯（干扰机 ID、原因、触发的规则） |
| `ExperimentConfig` / `ExperimentRun` | 实验配置与运行记录 |

### 干扰样式与 SINR 风险映射

**9 种干扰样式**：`co_channel`（同频）、`adjacent_channel`（邻频）、`barrage`（宽带拦阻）、`narrowband_spot`（窄带点频）、`sweep`（扫频）、`pulse`（脉冲）、`deceptive`（欺骗）、`noise`（噪声）、`burst_collision`（突发碰撞）

**SINR → 风险等级映射**：

| SINR 范围 | 风险等级 |
|-----------|----------|
| `>= 15 dB` | normal（正常） |
| `[10, 15) dB` | mild（轻度） |
| `[5, 10) dB` | moderate（中度） |
| `[0, 5) dB` | severe（严重） |
| `< 0 dB` | unavailable（不可用） |

## API 参考

基地址：`/api/v1`

### 场景管理
| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/scenario/load` | 加载场景 JSON |
| GET | `/scenario/current` | 当前场景配置 |
| GET | `/scenario/data-sources` | 数据源元数据 |
| GET | `/scenario/mode` | 当前模式（仿真/在线） |
| POST | `/scenario/mode` | 切换模式 |

### 仿真与态势
| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/simulation/step` | 仿真步进（可选 `delta_sec` 参数） |
| GET | `/situational/current` | 当前态势（支持 `sparse`、`realtime`、`refresh_sources`） |
| POST | `/situational/complete` | 稀疏态势补全 |
| POST | `/situational/predict` | 动态预测（30–600s） |
| GET | `/constellation/positions` | 卫星实时位置 |

### 告警与风险评估
| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/alerts` | 告警列表 |
| GET | `/risk/assessment` | 五维风险评估 |
| GET | `/stream/alerts` | SSE 实时告警流 |

### 下游与评测
| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/downstream/payload` | 下游模块结构化载荷 |
| GET | `/completion/compare` | 补全方法基准对比 |

### 实验管理
| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/experiments` | 创建实验 |
| GET | `/experiments` | 列出所有实验 |
| DELETE | `/experiments` | 清除所有实验 |
| GET | `/experiments/{id}` | 获取实验详情 |
| DELETE | `/experiments/{id}` | 删除实验 |
| POST | `/experiments/{id}/run` | 运行实验 |
| GET | `/experiments/{id}/progress` | 实验进度 |
| POST | `/experiments/{id}/export` | 导出实验结果 |
| GET | `/experiments/{id}/cases/{case_id}/replay` | 回放实验 case |
| GET | `/experiments/{id}/artifacts/{name}` | 下载结果文件 |

完整 API 文档见 `docs/API_v0.1.md` 或启动后访问 `/docs` 查看 Swagger UI。

## 场景配置

场景使用 JSON 文件定义，位于 `data/scenarios/`：

```jsonc
{
  "scenario_id": "demo_leo_v0",
  "name": "低轨星座演示场景",
  "epoch": "2026-06-15T12:00:00Z",
  "time_step_sec": 5,
  "simulation_duration_sec": 5400,
  "constellation": {
    "type": "walker",           // walker | tle_text | tle_source
    "planes": 5,
    "sats_per_plane": 10,
    "altitude_km": 550,
    "inclination_deg": 53
  },
  "ground_stations": [ /* ... */ ],
  "default_links": {
    "isl_center_freq_hz": 2.8e10,   // ISL 28 GHz
    "sgl_center_freq_hz": 1.4e10,   // SGL 14 GHz
    "bandwidth_hz": 5e8,
    "tx_power_dbm": 30
  },
  "jammers": [ /* ... */ ],
  "external_sources": { /* TLE URL / 真实数据路径 */ }
}
```

### 可用场景

| 场景文件 | 说明 |
|----------|------|
| `demo_leo_v0.json` | 50 星 Walker 星座 (550km)，3 地面站（北京/上海/西安），5 类干扰源 |
| `tle_online_v0.json` | 从 Celestrak 在线拉取 TLE，最多 40 颗真实卫星，1 个干扰源 |
| `tle_demo_v0.json` | 离线模式，内嵌 ISS / NOAA 15 / FY-3C 三颗真实卫星 TLE |
| `real_data_demo_v0.json` | 导入外部 CSV/JSON 真实观测数据演示，含 60s 时间对齐容差 |

## 前端可视化

单页面应用 (`frontend/static/index.html`)，基于 CesiumJS + ECharts，无构建工具依赖。

### 功能布局

- **三维地球 (CesiumJS)** — 卫星实体实时渲染、ISL/SGL 链路按风险等级着色（绿→黄→橙→红）、星下点轨迹线、卫星/链路点击交互查询
- **操作工具栏** — 模式切换（仿真/在线）、手动步进、预测触发、补全触发、自动刷新（12s 间隔）
- **实验面板** — 场景选择、观测率、预测时域、步数/间隔、补全方法勾选、创建/运行、历史列表
- **实时图表 (ECharts)** — 态势趋势曲线、实时频谱瀑布图、实时 SINR 柱状图
- **分析面板** — 当前链路与告警、实验摘要统计、算法对比条形图+表格、实验回放（时间滑块+时间序列+case 列表）

## 实验系统

实验引擎 (`backend/app/services/experiments.py`) 支持在场景 × 观测率 × 预测时域 × 补全方法构成的笛卡尔积空间上进行批量自动化评估。

### 工作流程

1. **创建实验** — 指定场景路径、观测率列表、预测时域列表、步数/间隔、补全方法、导出格式
2. **运行实验** — 对每个 case：加载场景 → 执行 N 步仿真 → 运行所有补全方法 → 运行预测 → 采集指标
3. **查看结果** — 实验摘要、case 级别指标、对比 CSV、时间序列 CSV
4. **回放分析** — 前端选择 case，时间滑块逐步回放态势变化

### 采集指标（13 项）

RMSE、MAE、补全时间、预测置信度、链路可用率、频谱占用率等。

## 验收测试

```bash
cd backend
python -m scripts.acceptance_tests
python -m pytest tests/ -v
```

**14/14 全部通过：**

- 星座/链路动态更新
- 频谱冲突判定
- 干扰样式覆盖（≥4 种，实际覆盖 5 种）
- 态势生成
- 稀疏补全 25%/50%
- 动态预测 30s / 1min / 5min / 10min
- 五维风险评估
- 下游接口载荷
- 态势更新延迟 < 5s（实测 ~0.01s）
- 补全方法对照实验（IDW 相对 Kriging 提升 ~22%）

## 部署

### 本地开发

SQLite + 单进程 uvicorn，适合开发调试。数据目录默认 `./data`，数据库文件 `ems.db`。

### Docker 生产部署

```
┌──────────┐    ┌──────────┐    ┌────────────┐    ┌──────────┐
│  Nginx   │───▶│  FastAPI  │───▶│ PostgreSQL │    │  Redis   │
│  (web)   │    │  (api)   │    │    16      │    │    7     │
│  :80     │    │  :8000   │    │  :5432     │    │  :6379   │
└──────────┘    └──────────┘    └────────────┘    └──────────┘
```

- **api** — FastAPI + uvicorn (4 workers)，挂载 `./data` 和 `./backend` 卷
- **web** — Nginx 反向代理，静态文件 7 天缓存，gzip，100MB 请求体
- **postgres** — PostgreSQL 16 Alpine，持久化卷，自动初始化扩展
- **redis** — Redis 7 Alpine，AOF 持久化，实验进度跟踪

详细部署说明见 `docs/DOCKER_DEPLOY.md`，离线部署见 `docs/DOCKER_OFFLINE.md`，生产检查清单见 `docs/DOCKER_PRODUCTION_CHECKLIST.md`。

### CI/CD

GitHub Actions 工作流 (`.github/workflows/docker-build.yml`)：
- **构建** — Docker Buildx 多平台构建，推送至 ghcr.io，支持分支/tag/SHA 标签
- **测试** — PostgreSQL + Redis 服务容器，pytest + pytest-cov，Codecov 覆盖率上报

## 配置项

通过环境变量或 `.env` 文件配置（`backend/app/config.py`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./ems.db` | 数据库连接串（SQLite / PostgreSQL） |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串 |
| `DATA_DIR` | `../data` | 场景/知识库/实验数据目录 |
| `STATIC_DIR` | `../frontend/static` | 前端静态文件目录 |
| `ENABLE_DB_BOOTSTRAP` | `true` | 启动时自动建表 |

## 文档索引

| 文档 | 内容 |
|------|------|
| `docs/API_v0.1.md` | API 参考、下游接口格式、插件接口规范 |
| `docs/STARTUP.md` | 本地/Docker/离线三种启动方式 |
| `docs/DOCKER_DEPLOY.md` | Docker 部署完整指南 |
| `docs/DOCKER_OFFLINE.md` | 内网/离线环境部署手册 |
| `docs/DOCKER_PRODUCTION_CHECKLIST.md` | 生产环境安全/性能/监控清单 |
| `docs/REAL_DATA_IMPORT.md` | 真实观测数据导入格式与字段映射 |
| `docs/ACCEPTANCE_REPORT.md` | 验收测试结果报告 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.11+) |
| 数据模型 | Pydantic v2, SQLAlchemy |
| 轨道计算 | Skyfield (SGP4) |
| 数值计算 | NumPy, SciPy, scikit-learn |
| 深度学习 | PyTorch (MAE 补全模型) |
| 数据库 | SQLite (开发) / PostgreSQL 16 (生产) |
| 缓存/状态 | Redis 7 |
| 三维可视化 | CesiumJS 1.115 |
| 图表 | ECharts 5.5.0 |
| 容器化 | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| 前端服务 | Nginx 1.27 Alpine |

## 已知限制（Phase 2 规划）

- 千星规模压力测试尚未验证
- GenSpectraLM / 3D Swin Transformer 完整复现待 Phase 2
- 半实物 SDR 验证待硬件到位后接入
- 大文件 IQ 摘要计划扩展 HDF5 / Parquet 格式支持
