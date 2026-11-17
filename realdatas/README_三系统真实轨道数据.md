# Starlink Gen1 / OneWeb / GSO 实际轨道数据（SGP4 输入）

核对时间：2026-11-14。

## 文件说明与当前完成状态

| 文件 | 已随包存储的完整 OMM 轨道记录 | 额外的真实 NORAD 目录 | 用途 |
| --- | ---: | --- | --- |
| `Starlink_Gen1_constellation.json` | 0 | 5 条此前确认的候选编号 | 保留 218 条公开来源 Gateway，待将全量 GP 与 Gen1 身份索引交叉匹配 |
| `OneWeb_constellation.json` | 8 | 651 个 NORAD 编号 | 保留 4 条 FCC 经纬度 Gateway，准备完整导入 |
| `GSO_constellation.json` | 5 | 已收录 GEO 目录 568 个真实 NORAD 编号；仅 5 条完整 OMM | GEO 轨道候选；仅 SES-17 标记为初始保护系统示例 |

**重要：这里的 651 和 568 是已经存入目录的真实 NORAD 编号数量，并不是已经写入本地的完整轨道元素数量。**

## 全量导入：运行以下命令

1. 将 ZIP 中所有文件解压到同一个文件夹。
2. Windows PowerShell 在该文件夹执行（Python 3.9+，仅标准库）：

```powershell
python .\download_three_constellations.py --output-dir .
```

如学校网络无法直接访问 CelesTrak，请从以下链接浏览器下载并放入同一文件夹：

- Starlink GP/OMM：`https://celestrak.org/NORAD/elements/gp.php?GROUP=STARLINK&FORMAT=JSON`
- OneWeb GP/OMM：`https://celestrak.org/NORAD/elements/gp.php?GROUP=ONEWEB&FORMAT=JSON`
- GEO GP/OMM：`https://celestrak.org/NORAD/elements/gp.php?GROUP=GEO&FORMAT=JSON`
- Starlink Gen1 身份名单：`https://www.planet4589.org/space/con/star/starindex.html` （网页另存为 HTML）

也可以用公开镜像：https://github.com/satvisorcom/satvisor-data （`celestrak/json/` 下对应三个 JSON）。

将上述文件分别重命名为 `starlink.json`、`oneweb.json`、`geo.json`、`starindex.html`，运行：

```powershell
python .\download_three_constellations.py --no-network --starlink-omm starlink.json --oneweb-omm oneweb.json --geo-omm geo.json --starlink-index starindex.html --output-dir .
```

成功以后，脚本会原子写入三份完整的 `*_constellation.json`，并显示每套**真正导入的卫星数量**与最新的 `EPOCH`。输出会保存经纬度 Gateway 和天线数量 4/8/16 的实验设定。

## 仿真限制与科研注意

1. **Starlink Gen1 不是 STARLINK 全目录**。严格识别方式是 Jonathan McDowell 的 V1.0/V1.5 型号目录与当前 GP 的 NORAD 编号/卫星名称交叉匹配，并排除 43° Gen2 Group 5 壳层中的 V1.5 卫星。Gen1 授权轨道、Gen1 硬件代际与实际运营状态须分开。
2. **OneWeb 的 GP 记录不代表卫星都在运营轨道**，需按实际历元、轨道高度、卫星活动状态二次筛选。
3. **GEO 不是可直接拿来保护的 GSO-FSS 列表**。必须从 GEO 卫星中核实工作频段、地面站、天线增益和许可/ITU 保护条件。SES-17 是初步示例，不意味着所有 GEO 卫星都用 17.8–18.6 GHz。
4. GP/OMM 是轨道数据，不包括馈电链路真实活动、网关站发射/接收分配、实时天线指向、转发器功率及用户业务。下行馈电的 `Sat -> Gateway` 工作链路仍需仿真定义。
5. 新星可能拥有六位 NORAD 编号，不能将整个 Starlink 目录强行转为旧式五位 TLE。使用 OMM JSON/SGP4。
6. 采用 SGP4 时应在对应 `EPOCH` 附近传播，避免用一份 GP 做长达几个月的预测。
7. GSO 保护评估中，GSO 地球站位置与保护判据应另行建模；不能把 Starlink/OneWeb 的下行 LF Rate 和 GSO EPFD 规则混成一个 I/N 约束。

## 建议的实验任务

先验证 OneWeb 与 Starlink Gen1 的 `EPOCH` 分布及 `NORAD_CAT_ID` 唯一性，再做 SGP4 全球可见性；之后用真实 Gateway 位置建立卫星-站候选关系，最后引入 GSO 受保护地球站与适用干扰限制。
