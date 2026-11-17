# 第一版冻结实验配置 feeder_v1

冻结日期：2026-11-15。范围：配置、数据快照与可视化；不启用活动馈电链路、干扰求解或AI。

研究目标：异构Starlink–OneWeb下行馈电动态干扰管理，GSO固定保护关联；评价LF、FSR与在线计算开销。用户业务/QoS/路由不在本阶段范围。

## 冻结配置

|项|值|性质|
|---|---|---|
|NGSO网关|Starlink6、OneWeb6|同区域最近不重复站址配对|
|GSO|12星、12站、12固定关联|仿真假设，波束待核实|
|时刻|2026-11-13 12:00 UTC|与本地轨道历元接近|
|时间步长/时窗|10秒/7200秒|共720个步进区间，若含初始点则721个快照；本阶段不批量生成|
|频谱|17.8–18.6GHz，8个100MHz子信道|理想集中协调共享资源|
|每NGSO站工作天线|8|至多8条活动馈电链路，允许空闲|
|发射功率|12dBW=42dBm/活动100MHz载波|固定每载波总功率，非运营商实测|
|NGSO峰值增益|卫星35dBi、网关45.76dBi|论文参考假设|
|噪温/最低仰角|398K / 40°|NGSO基线假设|
|LF门限|−12.2dB聚合I/N|实验判据，非通用法规门限|
|GSO接收参数|3.5m/效率0.65/398K/最低仰角10°|沿用独立固定配置|
|随机种子|20261115|后续算法显式使用|

子信道中心GHz：17.85, 17.95, 18.05, 18.15, 18.25, 18.35, 18.45, 18.55。18.2GHz为研究频段参考中心，不是每个载波都使用同一中心。每条链路只占一个子信道是后续实现约定。

关联约定：同运营商、最大仰角、相同仰角按卫星ID确定顺序；每星至多服务一个网关，每站最多8星。后续实现必须明确全局冲突处理，不能独立逐站选星后重复占用同星。此阶段未实现关联算法。

## 配对站点

|OneWeb|Starlink|距离km|Starlink资料|
|---|---|---:|---|
|Talkeetna Gateway, Alaska (OW-FCC-001)|Anchorage, AK (SL-C-004)|124.171|社区目录，位置与频段未逐站核实|
|Southbury SNP Gateway, Connecticut (OW-FCC-002)|Litchfield, CT (SL-C-160)|33.913|社区目录，位置与频段未逐站核实|
|Yona SNP Gateway, Guam (OW-FCC-003)|Tumon, GU (SL-C-100)|11.02|社区目录，位置与频段未逐站核实|
|Paumalu SNP Gateway, Hawaii (OW-FCC-004)|Molokai, HI (SL-C-062)|120.584|社区目录，位置与频段未逐站核实|
|Clewiston SNP, Florida (OW-FCC-005)|Punta Gorda, FL (SL-C-189)|100.89|社区目录，位置与频段未逐站核实|
|Santa Paula SNP, California (OW-FCC-006)|Hawthorne, CA (SL-C-038)|86.978|社区目录，位置与频段未逐站核实|

OneWeb6站有FCC坐标与频段资料；配对Starlink6站为社区目录。该配置是轨道驱动的可控仿真基线，不是双方真实联合运营网络。站址误差、运营状态和频谱许可须在后续实验中分开处理。

## 快照与变更规则

原始3组轨道文件、GSO频段筛选、GSO接收参考配置已复制到data/baselines/feeder_v1；场景和研究配置均写入SHA256清单。后续realdatas变化不会改变v1轨道快照。冻结脚本再次运行仅校验，不覆盖。新增筛选或参数变化创建v2或命名派生场景。

冻结的是原始轨道候选输入，尚未筛出运营卫星、标注Starlink代际或处理过低高度。下阶段创建筛选清单及派生轨道集合，不能悄悄改写v1。方向图确切公式/版本、GSO频率掩码消费、保护门限与统计流程仍待落地，未实现项在readiness中为false。
.
主场景继续保留全量218+13+12站；冻结场景为6+6+12站。共享后端只有一个当前场景，切换页面会切换全局场景，不可用两个标签同时运行独立实验。

网页： http://127.0.0.1:8000/static/constellations.html?scene=baseline
校验：`.venv-ems/Scripts/python scripts/verify_frozen_baseline.py`
哈希核验：`python scripts/freeze_feeder_baseline.py`
研究参数：系统项目data/baselines/feeder_v1/research_config.json
来源基线论文：https://arxiv.org/abs/2505.12429 。这里引用的通信参数是本地精读笔记中的论文参考值，非真实载荷规格。