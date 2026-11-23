# 六个目标期刊相关工作调研与阅读路线

检索日期：2026-11-18。主要检索2023–2026年的工作，实际入选正式/在线年份以逐条记录为准。本轮精选15条：TWC 3、TCOM 2、TCCN 4、TVT 3、JSAC 2、TGCN 1。全部为待阅读线索，不改变现有已读记录。

## 范围与证据

课题基准：NGSO–NGSO–GSO异构星座下行馈电共存，固定功率下联合选星与子信道，保留GSO聚合参考窗口保护；研究重点是可靠快速干扰评价与动态决策。优先筛选卫星共存、馈电链路、动态干扰/资源决策，其次才是感知和绿色通信补充。

检索组合：satellite / feeder link / GEO LEO / NGSO + interference management / spectrum sharing / cognitive radio / dynamic resource allocation / graph / hypergraph / reinforcement learning / energy efficiency，加六刊全名或缩写；补充按完整题名和DOI追溯。使用IEEE摘要、ComSoc目录、作者高校存档、NASA/NSF记录；普通聚合站只用于发现线索，不据此判定算法成果。部分IEEE DOI无法直接解析，已在相应记录说明。

这是定向文献筛选和阅读规划，不是穷尽检索或全文系统综述。不同条目的核验深度不同，逐条列出；没有按引用量排序，也不声称未发现的方向不存在。

P1：优先精读/准备基线；P2：特定模块阅读；P3：拓展方向。相关程度和可迁移性是结合本项目作出的研究判断，不是作者结论。

## 建议阅读顺序

1. R04：已有本地PDF，先把ILP、运营约束和规模化求解作为非AI强基线。
2. R02：理解GEO–LEO共享的保护对象与认知决策闭环。
3. R03：已有本地PDF，分析动态超图是否真正减少构图和物理评价成本。
4. R01：直接涉及馈电/用户链路，学习耦合分解与MADRL可扩展性。
5. R05、R12：多域干扰管理和跳波束调度，对照服务规模、停用与时域动作。
6. R06：补齐聚合干扰、频谱泄漏与保护尾部风险的物理分析视角。
7. R07–R11按需读；R13–R15作为保护制度、结构化优化、绿色通信拓展。

## 逐篇阅读卡


### R01 · P1 · Dependency-Elimination MADRL: Scalable On-Board Resource Allocation for Feeder- and User-Link Integrated Satellite Communications

- 期刊/年份：TCOM，2025。
- 作者：Qiaolin Ouyang et al.。
- 关键词：馈电链路 / 多智能体强化学习 / 动态决策。
- 阅读状态：待阅读；核验深度：IEEE摘要与73(8):6673–6688；在线2025-01-13。
- 已核验内容：针对馈电/用户链路资源竞争及上下行数据流耦合，用模型分解、链路解耦与智能体协作安排波束、功率和带宽。
- 对本项目的阅读价值【研究判断】：优先研究“耦合在哪里、如何解耦”，为联合选星分频的状态/动作设计和可扩展基线提供参照。
- 迁移边界：包含馈电链路不等于研究NGSO–GSO下行馈电聚合EPFD；它的控制变量也超出当前项目固定功率范围。
- 精读时的问题：模型解耦是否仍保持原约束？复杂度收益来自学习、动作降维还是带宽解析分配？
- [一手来源](https://ieeexplore.ieee.org/document/10839405/)；[DOI入口](https://doi.org/10.1109/TCOMM.2025.3529212)。


### R02 · P1 · Joint Beam Management and Resource Allocation in a GEO and LEO Spectrum-Sharing System for Effective Interference Avoidance

- 期刊/年份：TCCN，2025。
- 作者：D. Zhao, B. Song, X. Du。
- 关键词：GEO–LEO / 认知无线电 / 深度强化学习 / 干扰管理。
- 阅读状态：待阅读；核验深度：作者机构摘要；11(4):2662–2675，正式2025；DOI含2024。
- 已核验内容：联合波束管理、频道和功率，结合空间信息图及模型驱动/无模型DRL，在改善吞吐时维持GEO用户服务。
- 对本项目的阅读价值【研究判断】：最接近我们的异构星座共存叙事，可对照保护对象、决策状态、离散/连续动作及闭环。
- 迁移边界：用户链路与同线干扰规避不能直接替代馈电链路参考窗口EPFD；QoS保护也不自动等同法规保护。
- 精读时的问题：GEO保护是硬约束还是奖励项？训练外轨道、强干扰源是否仍满足保护？
- [一手来源](https://researchwith.stevens.edu/en/publications/joint-beam-management-and-resource-allocation-in-a-geo-and-leo-sp/)；[DOI入口](https://doi.org/10.1109/TCCN.2024.3516034)。


### R03 · P1 · Interference-Suppressed Joint Channel and Power Allocation for Downlinks in Large-Scale Satellite Networks: A Dynamic Hypergraph Neural Network Approach

- 期刊/年份：TWC，在线2025；卷25。
- 作者：Bo Zhang et al.。
- 关键词：动态超图 / AI赋能 / 频道功率 / 干扰管理。
- 阅读状态：待阅读；核验深度：IEEE摘要：在线2025-07-14，卷25、728–742；不把在线年当卷期年。
- 已核验内容：以动态超图表达波束覆盖与用户参与的时变关系，用DynHGNN支持联合频道/功率资源分配。
- 对本项目的阅读价值【研究判断】：可用于检验超图是否比二元图更能保留聚合干扰结构，以及图更新和推理成本。
- 迁移边界：场景是大规模卫星下行波束/用户；不能声称已处理我们S.1428/S.1528预算或GSO聚合EPFD。
- 精读时的问题：超边具体连接什么？构图是否仍需完整逐对预算？物理约束如何验证？
- [一手来源](https://ieeexplore.ieee.org/abstract/document/11080232/)；[DOI入口](https://doi.org/10.1109/TWC.2025.3586230)。
- 已有本地PDF：`paper_notes/阅读论文原文/Interference-Suppressed_Joint_Channel_and_Power_Allocation_for_Downlinks_in_Large-Scale_Satellite_Networks_A_Dynamic_Hypergraph_Neural_Network_Approach.pdf`。


### R04 · P1 · Frequency Plan Design for Multibeam Satellite Constellations Using Integer Linear Programming

- 期刊/年份：TWC，2024（在线2023）。
- 作者：Juan Jose Garau-Luis et al.。
- 关键词：整数规划 / 频率规划 / 强基线 / 切换。
- 阅读状态：待阅读；核验深度：IEEE摘要与23(4):3312–3327；作者arXiv为较早版本。
- 已核验内容：用ILP编码干扰、切换和网关规模约束，并设计迭代求解以提升规模适应性。
- 对本项目的阅读价值【研究判断】：作为学习算法之前的强优化基线；阅读如何显式保留运营约束、拆分大问题。
- 迁移边界：波束频率规划不等于逐链路馈电共存；不同版本摘要的增益数字不同，比较必须使用同一版本。
- 精读时的问题：哪些约束可映射到一星一站、站内无重频？如何报告最优间隙与求解时间？
- [一手来源](https://doi.org/10.1109/TWC.2023.3307349)；[DOI入口](https://doi.org/10.1109/TWC.2023.3307349)；[作者开放版本/获取入口](https://arxiv.org/abs/2204.12494)。
- 已有本地PDF：`paper_notes/阅读论文原文/Frequency_Plan_Design_for_Multibeam_Satellite_Constellations_Using_Integer_Linear_Programming.pdf`。


### R05 · P1 · Interference Management by Harnessing Multi-Domain Resources in Spectrum-Sharing Aided Satellite-Ground Integrated Networks

- 期刊/年份：TVT，2024。
- 作者：Xiaojin Ding et al.。
- 关键词：双NGSO / 动态决策 / 干扰管理 / LSTM/DQN。
- 阅读状态：待阅读；核验深度：作者机构全文入口及摘要，TVT 73(6):8306–8321；arXiv初稿2023。
- 已核验内容：两个NGSO星座与地面基站共频；联合波束开关/切换与功率调度，并使用时序预测及DQN。
- 对本项目的阅读价值【研究判断】：同时涉及跨星座干扰和多域决策，可对照我们“仅分频不可行后释放关联”的动机。
- 迁移边界：存在主动关波束和功率调节；必须公平控制服务数量，不能直接拿其低干扰与固定活动规模比较。
- 精读时的问题：关闭波束的服务损失如何计入目标？预测误差如何影响干扰和中断？
- [一手来源](https://eprints.soton.ac.uk/486222/1/MitigateINGSOV2.pdf)；[DOI入口](https://doi.org/10.1109/TVT.2024.3354980)；[作者开放版本/获取入口](https://arxiv.org/abs/2310.15011)。


### R06 · P1 · Interference Analysis for Coexistence of Terrestrial Networks With Satellite Services

- 期刊/年份：TWC，2024（在线2023）。
- 作者：Byungju Lim, Mai Vu。
- 关键词：聚合干扰 / 带外泄漏 / 保护约束 / 物理分析。
- 阅读状态：待阅读；核验深度：NSF存档论文首页/摘要，TWC 23(4):3146起。
- 已核验内容：分析地面网络对卫星业务的同频和带外泄漏，并推导聚合干扰分布与网络保护设计准则。
- 对本项目的阅读价值【研究判断】：是物理评价方法参考：区分单源贡献、聚合分布、谱形和保护条件，再考虑近似加速。
- 迁移边界：地面到卫星的干扰方向和天线几何不同；解析分布不能未经验证迁移到我们的确定性轨道快照。
- 精读时的问题：哪些条件使解析分布成立？误差在尾部和保护门限附近是否更大？
- [一手来源](https://par.nsf.gov/servlets/purl/10560872)；[作者开放版本/获取入口](https://par.nsf.gov/servlets/purl/10560872)。


### R07 · P2 · Evolutionary Reinforcement Learning for Resource Efficiency Optimization in Downlink Multi-LEO Communication System with Cross-Layer Interference

- 期刊/年份：TCCN，2025在线；记录为卷12。
- 作者：Qing Wei et al.。
- 关键词：多LEO / 进化强化学习 / 资源效率。
- 阅读状态：待阅读；核验深度：Surrey作者机构检索记录，在线2025-11-13；页面直接抓取403，全文未读。
- 已核验内容：作者机构记录确认多LEO下行、跨层干扰和进化强化学习主题；具体状态/奖励/约束需要全文核对。
- 对本项目的阅读价值【研究判断】：适合比较单纯DRL与进化搜索混合时的决策效率、稳定性和样本成本。
- 迁移边界：当前仅据机构摘要记录筛选，不推断其“跨层”一定指GSO/NGSO轨道层，也不编造加速结果。
- 精读时的问题：跨层指协议层还是轨道层？进化步骤是离线训练还是在线开销？
- [一手来源](https://openresearch.surrey.ac.uk/esploro/outputs/journalArticle/Evolutionary-Reinforcement-Learning-for-Resource-Efficiency/991059266502346)；[DOI入口](https://doi.org/10.1109/TCCN.2025.3632396)；[作者开放版本/获取入口](https://openresearch.surrey.ac.uk/esploro/outputs/journalArticle/Evolutionary-Reinforcement-Learning-for-Resource-Efficiency/991059266502346)。


### R08 · P2 · Radio Map-Based Cognitive Satellite-UAV Networks Towards 6G On-Demand Coverage

- 期刊/年份：TCCN，2024（在线2023）。
- 作者：Wei Feng et al.。
- 关键词：认知无线电 / 无线电地图 / 大尺度CSI。
- 阅读状态：待阅读；核验深度：作者机构摘要与10(3):1075–1089。
- 已核验内容：面向卫星/UAV认知网络，利用无线电地图及大尺度CSI辅助共享与按需覆盖。
- 对本项目的阅读价值【研究判断】：为“已有几何/地图信息如何辅助决策”提供方法参考，贴近状态估计—评价—决策闭环。
- 迁移边界：UAV覆盖问题并非馈电选星；无线电地图也不能替代轨道与双端离轴角物理预算。
- 精读时的问题：地图预计算与在线更新如何分摊？对估计误差是否鲁棒？
- [一手来源](https://durham-repository.worktribe.com/output/2048656/radio-map-based-cognitive-satellite-uav-networks-towards-6g-on-demand-coverage)；[DOI入口](https://doi.org/10.1109/TCCN.2023.3345857)；[作者开放版本/获取入口](https://repository.kaust.edu.sa/bitstreams/df5f6ada-cddb-45ef-9591-e7738a1339fc/download)。


### R09 · P2 · SATSense: Multi-Satellite Collaborative Framework for Spectrum Sensing

- 期刊/年份：TCCN，2026（在线2025）。
- 作者：作者名单请见来源页。
- 关键词：协作感知 / 图学习 / 认知无线电。
- 阅读状态：待阅读；核验深度：作者机构摘要，卷12:2325–2338，在线2025-06-30，正式2026。
- 已核验内容：多卫星协作频谱感知，将感知数据建图，并结合压缩及对比学习缓解传输和丢包影响。
- 对本项目的阅读价值【研究判断】：若今后从已知精确场景走向不完备观测，可作为感知前端参考。
- 迁移边界：目前我们的轨道/配置是已知输入；感知分类准确率不等于物理EPFD评价误差或决策安全性。
- 精读时的问题：感知结果如何转为物理干扰状态？观测成本与检测漏报如何进入闭环？
- [一手来源](https://scholars.cityu.edu.hk/en/publications/satsense-multi-satellite-collaborative-framework-for-spectrum-sen/)；[DOI入口](https://doi.org/10.1109/TCCN.2025.3584228)。


### R10 · P2 · Cooperative Spectrum Sharing for Interference Management in LEO Based Integrated Satellite–Terrestrial Networks

- 期刊/年份：TVT，2026（DOI年2025）。
- 作者：Sanguk Park et al.。
- 关键词：认知感知 / 多普勒 / 邻频干扰 / 鲁棒优化。
- 阅读状态：待阅读；核验深度：作者机构摘要与75(4):6962–6967，2026-04。
- 已核验内容：独立星地系统信息不互通时，以能量检测协作感知和功率分配处理同频/邻频干扰，采用SAA。
- 对本项目的阅读价值【研究判断】：帮助判断“有完整信息”与“需要感知”两种共存问题的差别，并提示多普勒邻频因素。
- 迁移边界：这是星地共享而非NGSO–GSO馈电；当前项目也尚未纳入其邻频/信道不确定性。
- 精读时的问题：感知耗时如何影响速率？SAA怎样处理概率约束与样本外风险？
- [一手来源](https://pure.kaist.ac.kr/en/publications/cooperative-spectrum-sharing-for-interference-management-in-leo-b/)；[DOI入口](https://doi.org/10.1109/TVT.2025.3621705)。


### R11 · P2 · Interference Mitigation for Reverse Spectrum Sharing in B5G/6G Satellite-Terrestrial Networks

- 期刊/年份：TVT，2024。
- 作者：Hao-Wei Lee et al.。
- 关键词：干扰管理 / 资源分组 / 星地共享。
- 阅读状态：待阅读；核验深度：作者实验室全文入口/摘要；DOI含2023，论文版面©2024。
- 已核验内容：围绕反向频谱共享，使用干扰感知资源组共享及网络分组，协调地面与卫星网络资源。
- 对本项目的阅读价值【研究判断】：适合作为非AI、结构化调度基线，观察分组如何控制搜索规模。
- 迁移边界：地固波束、反向共享场景与我们的下行馈电不同；摘要中的容量收益不能直接迁移。
- 精读时的问题：分组所需信息和开销多大？是否遗漏组间聚合干扰？
- [一手来源](https://wmnlab.ee.ntu.edu.tw/lab/publication/Journal/%5BJ%5D2023_%5BTVT%5DInterference_Mitigation_for_NTN_TN_Spectrum_Sharing_in_B5G_6G_Satellite_Terrestrial_Networks.pdf)；[DOI入口](https://doi.org/10.1109/TVT.2023.3328599)；[作者开放版本/获取入口](https://wmnlab.ee.ntu.edu.tw/lab/publication/Journal/%5BJ%5D2023_%5BTVT%5DInterference_Mitigation_for_NTN_TN_Spectrum_Sharing_in_B5G_6G_Satellite_Terrestrial_Networks.pdf)。


### R12 · P1 · Satellites Beam Hopping Scheduling for Interference Avoidance

- 期刊/年份：JSAC，2024。
- 作者：Huimin Deng et al.。
- 关键词：跳波束 / 干扰规避 / 动态调度。
- 阅读状态：待阅读；核验深度：作者机构存档摘要及42(12):3647–3658；直接抓取有超时。
- 已核验内容：建立吞吐驱动与满意度驱动跳波束问题，采用松弛分解和遗传算法处理调度。
- 对本项目的阅读价值【研究判断】：适合研究服务目标、干扰规避与时域动作如何结合，并作为学习方法外的搜索基线。
- 迁移边界：调度/用户侧共享不等于馈电EPFD管理；应核对避让造成的服务损失和保护约束。
- 精读时的问题：时间槽如何设计？规避约束是几何排斥还是累加功率门限？
- [一手来源](https://udspace.udel.edu/server/api/core/bitstreams/33fd9739-0567-418a-905b-c2142fa05e10/content)；[DOI入口](https://doi.org/10.1109/JSAC.2024.3459083)；[作者开放版本/获取入口](https://udspace.udel.edu/server/api/core/bitstreams/33fd9739-0567-418a-905b-c2142fa05e10/content)。


### R13 · P3 · Facilitating Spectrum Sharing With Passive Satellite Incumbents

- 期刊/年份：JSAC，2024。
- 作者：Jonathan Chamberlain, David Starobinski, Joel T. Johnson。
- 关键词：主用户保护 / 频谱共享 / 机制设计。
- 阅读状态：待阅读；核验深度：NASA文献记录：42(12):3719–3733；本轮仅元数据级核验。
- 已核验内容：NASA官方记录确认该文研究被动卫星既有用户的频谱共享；重点作为保护优先级与制度设计阅读。
- 对本项目的阅读价值【研究判断】：辅助理解共享不是单纯吞吐最大化，应先明确既有系统权利与保护优先级。
- 迁移边界：被动遥感保护与GSO通信接收EPFD规则不同；不是我们的物理评价算法强基线。
- 精读时的问题：优先使用权如何落地？其保护机制依赖哪些观测或外部制度？
- [一手来源](https://gpm.nasa.gov/node/5130)；[DOI入口](https://doi.org/10.1109/JSAC.2024.3459034)。


### R14 · P3 · Interference Mitigation in Multibeam Satellite Networks as an Optimal Sublattice Problem

- 期刊/年份：TCOM，2026（在线2025）。
- 作者：Francesco Lisi et al.。
- 关键词：频率复用 / 子格优化 / 非AI基线。
- 阅读状态：待阅读；核验深度：作者机构摘要，74:1940–1951；在线2025-10-14，正式2026。
- 已核验内容：将周期网格资源分布转为最优子格，借助可并行枚举改善同资源空间间隔，应用于固定GEO多波束。
- 对本项目的阅读价值【研究判断】：展示利用问题结构构造有效算法的路线，提醒先对比强结构方法再论证AI。
- 迁移边界：固定GEO周期布局与移动NGSO馈电几何不同，不能直接套用子格假设。
- 精读时的问题：周期结构能否在局部近似成立？并行枚举的总开销如何核算？
- [一手来源](https://researchportal.hw.ac.uk/en/publications/interference-mitigation-in-multibeam-satellite-networks-as-an-opt/)；[DOI入口](https://doi.org/10.1109/TCOMM.2025.3621253)；[作者开放版本/获取入口](https://researchportal.hw.ac.uk/en/publications/interference-mitigation-in-multibeam-satellite-networks-as-an-opt/)。


### R15 · P3 · Energy Efficient Design for Active RIS-Assisted Integrated Satellite-Terrestrial Networks With RSMA

- 期刊/年份：TGCN，2026。
- 作者：Jianfeng Shi, Yujie Kang, Yue Li, Baolong Li。
- 关键词：能效 / 干扰管理 / RSMA / RIS。
- 阅读状态：待阅读；核验深度：IEEE ComSoc目录标注2026、1378–1390；DOI来自检索线索，解析未成功，正式引用前再核对。
- 已核验内容：IEEE ComSoc目录核验题名、作者和页码；从标题可知涉及有源RIS、RSMA与星地网络能效。算法细节尚未核对。
- 对本项目的阅读价值【研究判断】：仅当课题增加通信/计算能耗目标时作为绿色通信方向补充。
- 迁移边界：当前属于目录级线索，不把第三方摘要当作已验证全文；RIS/RSMA也不是现有馈电模型配置。
- 精读时的问题：能耗分母计入了哪些电路、RIS放大和计算成本？是否存在能效/保护权衡？
- [一手来源](https://www.comsoc.org/system/files/2026-02/publications_contents_digest_2025-jan_0.pdf)；[DOI入口](https://doi.org/10.1109/TGCN.2025.3631854)。


## 额外跟踪：发表状态需再核对

- [Digital-Twin-Aided Dynamic Spectrum Sharing and Resource Management in Integrated Satellite-Terrestrial Networks](https://arxiv.org/abs/2602.09191)，2026，arXiv v2（7月15日）仍写“Submitted to TWC”。另有聚合索引给出期刊DOI，但本轮未获取IEEE一手确认，故不计入15篇已定位期刊清单。方法是时间窗预测规划加实时反馈修正，使用压缩感知和SCA；它说明动态决策不必自动等于神经网络。适合借鉴“粗计划—快速修正”的时间尺度划分，不能直接声称加速我们的EPFD预算。
- [AoI-Aware Energy Efficiency Resource Allocation for Integrated Satellite-Terrestrial IoT Networks](https://www.comsoc.org/system/files/2025-03/Publications_Contents_Digest_2025_Mar.pdf)，TGCN 2025，9(1):125–139，作者Qingming Wang、Xiao Liang、Hua Zhang、Linghui Ge。官方目录题名线索，尚未核对摘要/方法，作为能效与信息新鲜度补充，不计入上述详细卡片。

## 与现有研究的对比结论【研究判断】

- 直接含馈电链路的是R01；最接近异构轨道共享的是R02、R05；最值得比较动态结构表示的是R03。三者都不自动等价于当前NGSO–GSO参考窗口聚合EPFD问题。
- 构图、完整干扰预算、求解/推理是不同成本，不能仅比较神经网络推理时间。我们应记录预处理、精确校验、失败回退和整次决策端到端耗时。
- 普通图/超图和DRL是否保证聚合保护，需要逐篇看约束形式；硬约束、奖励惩罚、平均违约和瞬时逐接收点保证不能混用。
- 本轮未确认一篇同时覆盖我们的双端方向图、NGSO–NGSO–GSO聚合保护、固定服务规模联合选星分频、误差可控增量评价的完全同题工作；这不是创新性证明，下一轮应沿上述论文参考文献和被引继续检索。
- 若目标TGCN，需要真实能耗或能效建模；缩短程序时间本身不能作为绿色贡献。若目标TCCN，应明确可观测状态、感知/推理、决策、执行反馈及不确定性。

## 精读记录模板

逐篇补充：版本/页码 → 链路方向与受保护对象 → 物理预算 → 聚合方式 → 决策变量 → 瞬时/长期约束 → 状态与动作 → 算法/训练 → 强基线 → 时间与规模 → 误差/违约/服务公平性 → 可复现材料。阅读完成后再加入已读PDF/MD配对库，不能把筛选卡称作已完成精读。
