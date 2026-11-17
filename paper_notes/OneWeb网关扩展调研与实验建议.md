# OneWeb网关扩展调研与实验建议

检索日期：2026-11-15。当前系统4站是已整理子集，不是OneWeb全球网关总量。本轮为调研，未将坐标未核实的候选加入运行场景。

## 全球规模依据

Eutelsat 2024–25年度业绩材料（2025-08-05）报告截至2025年6月39个SNP已到位、5个部署中，目标44个。这是带日期的官方快照，不能写成截至2026-11的实时运营数量。

https://www.eutelsat.com/files/PDF/investors/FY_2024-25_Presentation_vDEF.pdf

OneWeb官方海事资料说明SNP为Ka频段网关，设计每站7–30副全动天线。它是系统设计说明，不是逐站当前设备清单。

https://assets.oneweb.net/s3fs-public/assets/documents/1133-OW-Maritime-Brochure-12pp-A4L-ENG-03A-lite.pdf?VersionId=gqusnZySrjo.DaiaPooDdqDK7KMfUU0d

## 优先扩展名单：8个新增候选

|候选|区域|一手证据及时间|尚缺内容|
|---|---|---|---|
|Clewiston|美国佛罗里达|SSC 2019年公告已安装8副OneWeb天线；FCC公告含17.8–18.6GHz申请|提取FCC精确站址、最新状态；不要把申请13副与公告8副当同一时刻数量|
|Darwin Tivendale|澳大利亚北部|Telstra 2022-03-31计划安装并于7月上线|精确坐标、后续建成状态、当地频段许可|
|Charlton Toowoomba|澳大利亚东部|Telstra同一公告列为2022年计划站|同上|
|Wangara Perth|澳大利亚西部|Telstra同一公告列为2022年计划站|同上|
|Scanzano|意大利西西里|Telespazio 2023-03-01公告OneWeb网关已部署；英/意文写15副，葡文写14副|精确坐标、当地频段、天线数量冲突溯源|
|Maricá|巴西里约州|Telespazio 2023-03-01公告网关揭幕|精确坐标、ANATEL许可、频段和设备参数|
|Sirindhorn / Ubon Ratchathani|泰国|NT 2024-11-11公告OneWeb SNP即将启用|精确站址、实际启用时间、NBTC频段许可|
|SvalSat|挪威斯瓦尔巴|ESA托管2024项目材料明确OneWeb gateway facility|具体OneWeb天线区坐标、Ka接收许可，不能把全部SvalSat天线都算OneWeb|

以上8点加现有4点构成12站的第一阶段扩展目标，不表示现在已有12套精确站址与许可数据。新增候选均不应仅用城市中心坐标冒充天线位置。

### 直接证据链接

- SSC Clewiston：https://sscspace.com/news/ssc-increases-capacity-at-florida-ground-station-eight-new-antennas-to-support-onewebs-global-satellite-network/
- SSC设施坐标（约两位小数，不是天线级精度）：https://sscspace.com/services/satellite-ground-stations/our-stations/ ，Clewiston约26.75N、81.05W。
- FCC Clewiston：https://docs.fcc.gov/public/attachments/DOC-355200A1.pdf 。搜索索引可读，直接访问本轮返回403，精确原表尚未完整提取。
- Telstra三站：https://www.telstrainternational.com/en/news-research/articles/telstra-providing-satellite-ground-infrastructure-for-oneweb
- Telespazio两站：https://www.telespazio.com/documents/559023/0/PR%2BTelespazio%2BMarica_en.pdf?t=1677688656941
- NT泰国站：https://www.ntsatellite.net/en/news-2/
- ESA项目材料：https://nebula.esa.int/sites/default/files/neb_tec_study/2499/public/FIGSI_Presentation_Project_Overview_at_FP_ESO_Marco%20Lanucara.pdf

## 第二阶段地域线索

Eutelsat提交的招股资料列出澳大利亚、巴西、日本、南非、智利、葡萄牙、意大利、哥斯达黎加、加纳、美国，并说明加拿大与挪威TT&C站兼作SNP。只能据此建立国家级检索线索，不能假定任一当地teleport都承载OneWeb。

https://prod.eutelsat.com/files/23-Project%20Orion%20-%20Prospectus%20-%20Final%20Submission.pdf

Eutelsat 2024-01公告证实南非、毛里求斯SNP激活，并称加纳、安哥拉待上线；该历史状态不能当作今天的状态：
https://echanges.dila.gouv.fr/OPENDATA/AMF/BWR/2024/01/FCBWR154674_20240119.pdf

这些区域应与日本、智利、葡萄牙一起优先补查，逐步形成16–24站的多区域实验集。16–24是实验规模建议，不是官方站点数量或统计充分性结论。

## 可复用科研数据入口

University of Victoria PanLab页面提供SNP地图，说明名单源自OneWeb AWS数据和各国监管资料，且显式区分已确认/推断坐标与仅确认区域的站点：
https://onlineacademiccommunity.uvic.ca/oneweb/

论文：Measuring the OneWeb Satellite Network，TMA 2025。代码入口：https://github.com/clarkzjw/tma25-oneweb 。该论文实测的是网络性能，不能直接代替本课题的物理干扰实验。地图属于研究团队/社区整理，坐标仍须逐条溯源。

SNP是卫星馈电网关，PoP是互联网接入设施，UT是用户终端；不能把PoP或UT加入Ka馈电网关集合。意大利的已确认OneWeb资料指向Scanzano，不能因Fucino是知名teleport就把它加入OneWeb名单。

## 对课题的含义与实验配置

现有4站仅涉及阿拉斯加、美国本土东部、夏威夷、关岛。它们可以用于局部模型验证，但不能支撑全球布局代表性或大规模加速结论。若每站统一4/8/16副工作天线，OneWeb活动链路上限分别16/32/64条；12站为48/96/192条，24站为96/192/384条。实际上限还受可见卫星与关联限制，工作天线数均为实验假设。

不要求OneWeb与Starlink站数相等。建议分别设置：

1. 等站数、等工作天线数的配对实验，隔离轨道和跨系统算法效果。
2. 按公开非对称站址布局的多区域实验，比较独立分频与联合管理。
3. 固定地理范围做4/8/12/16/24站规模敏感性，在可用资料范围内构建；额外合成站必须标为合成。

报告全系统和分星座LF Rate、活动链路数、跨星座干扰贡献及端到端耗时。必须先确认两个星座同时活动、共享研究频谱、接收位置处存在有效干扰几何；增加远方站点未必增加局部干扰。不能通过人为复制站址或强制同频去宣称真实网络干扰严重。

## 接入门槛

每条新增数据记录至少保存：站名、SNP角色证据、坐标及精度、WGS84基准、来源链接/日期、研究频段是否逐站确认、运营状态日期、文档天线数与仿真工作天线数。站点存在、精确位置、频段许可、当前运行是四项独立核查。

本轮交付是扩展证据与实施顺序；运行系统仍为OneWeb原4站，避免未核实坐标改变GSO参考点生成或现有研究场景。


## 已实施：13站研究场景

在用户授权后，新增Santa Paula（FCC文件DOC-358650A1，后续授权DOC-376504A1）、Clewiston两站精确DMS坐标与研究频段证据，形成6站FCC集；另加入前述7个非美国区域项目的明确仿真位置，共13站。区域坐标为研究者手动选定的粗略位置，未从项目资料提取，不声称实际天线位置。Darwin/Charlton/Wangara资料是2022年项目计划，不能当作当前已运营证明。

Santa Paula FCC坐标：34°24′7.20″N，119°4′23.50″W；Clewiston：26°44′51.80″N，81°2′57.20″W。

新增来源：https://docs.fcc.gov/public/attachments/DOC-358650A1.pdf 和 https://docs.fcc.gov/public/attachments/DOC-376504A1.pdf 。

原4站目录保持原样，扩展数据位于realdatas/OneWeb_research_gateways.json。网页白边为FCC、蓝边为区域仿真位置，支持仅核实站点筛选。系统地面站总数243：Starlink218、OneWeb13、GSO12。GSO一星一站配置保持。

13站统一4/8/16副工作天线的活动链路数量上限为52/104/208，仍须检查卫星可见性、关联和频段。当前仅接入位置与可视化，尚未启用馈电活动链路计算。
