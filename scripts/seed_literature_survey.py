import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
rows=[]
def add(id,journal,year,title,authors,priority,tags,summary,use,boundary,question,source,doi='',access='',evidence='出版社摘要/作者机构记录核验，未完成全文精读',local=''):
 rows.append(dict(id=id,journal=journal,year=year,title=title,authors=authors,priority=priority,tags=tags,summary=summary,relevance=use,boundary=boundary,question=question,source=source,doi=doi,access=access,evidence=evidence,local=local,status='待阅读'))
add('R01','TCOM','2025','Dependency-Elimination MADRL: Scalable On-Board Resource Allocation for Feeder- and User-Link Integrated Satellite Communications','Qiaolin Ouyang et al.','P1',['馈电链路','多智能体强化学习','动态决策'],
'针对馈电/用户链路资源竞争及上下行数据流耦合，用模型分解、链路解耦与智能体协作安排波束、功率和带宽。',
'优先研究“耦合在哪里、如何解耦”，为联合选星分频的状态/动作设计和可扩展基线提供参照。',
'包含馈电链路不等于研究NGSO–GSO下行馈电聚合EPFD；它的控制变量也超出当前项目固定功率范围。',
'模型解耦是否仍保持原约束？复杂度收益来自学习、动作降维还是带宽解析分配？',
'https://ieeexplore.ieee.org/document/10839405/','10.1109/TCOMM.2025.3529212',evidence='IEEE摘要与73(8):6673–6688；在线2025-01-13')
add('R02','TCCN','2025','Joint Beam Management and Resource Allocation in a GEO and LEO Spectrum-Sharing System for Effective Interference Avoidance','D. Zhao, B. Song, X. Du','P1',['GEO–LEO','认知无线电','深度强化学习','干扰管理'],
'联合波束管理、频道和功率，结合空间信息图及模型驱动/无模型DRL，在改善吞吐时维持GEO用户服务。',
'最接近我们的异构星座共存叙事，可对照保护对象、决策状态、离散/连续动作及闭环。',
'用户链路与同线干扰规避不能直接替代馈电链路参考窗口EPFD；QoS保护也不自动等同法规保护。',
'GEO保护是硬约束还是奖励项？训练外轨道、强干扰源是否仍满足保护？',
'https://researchwith.stevens.edu/en/publications/joint-beam-management-and-resource-allocation-in-a-geo-and-leo-sp/','10.1109/TCCN.2024.3516034',evidence='作者机构摘要；11(4):2662–2675，正式2025；DOI含2024')
add('R03','TWC','在线2025；卷25','Interference-Suppressed Joint Channel and Power Allocation for Downlinks in Large-Scale Satellite Networks: A Dynamic Hypergraph Neural Network Approach','Bo Zhang et al.','P1',['动态超图','AI赋能','频道功率','干扰管理'],
'以动态超图表达波束覆盖与用户参与的时变关系，用DynHGNN支持联合频道/功率资源分配。',
'可用于检验超图是否比二元图更能保留聚合干扰结构，以及图更新和推理成本。',
'场景是大规模卫星下行波束/用户；不能声称已处理我们S.1428/S.1528预算或GSO聚合EPFD。',
'超边具体连接什么？构图是否仍需完整逐对预算？物理约束如何验证？',
'https://ieeexplore.ieee.org/abstract/document/11080232/','10.1109/TWC.2025.3586230',evidence='IEEE摘要：在线2025-07-14，卷25、728–742；不把在线年当卷期年',local='Interference-Suppressed_Joint_Channel_and_Power_Allocation_for_Downlinks_in_Large-Scale_Satellite_Networks_A_Dynamic_Hypergraph_Neural_Network_Approach.pdf')
add('R04','TWC','2024（在线2023）','Frequency Plan Design for Multibeam Satellite Constellations Using Integer Linear Programming','Juan Jose Garau-Luis et al.','P1',['整数规划','频率规划','强基线','切换'],
'用ILP编码干扰、切换和网关规模约束，并设计迭代求解以提升规模适应性。',
'作为学习算法之前的强优化基线；阅读如何显式保留运营约束、拆分大问题。',
'波束频率规划不等于逐链路馈电共存；不同版本摘要的增益数字不同，比较必须使用同一版本。',
'哪些约束可映射到一星一站、站内无重频？如何报告最优间隙与求解时间？',
'https://doi.org/10.1109/TWC.2023.3307349','10.1109/TWC.2023.3307349','https://arxiv.org/abs/2204.12494',evidence='IEEE摘要与23(4):3312–3327；作者arXiv为较早版本',local='Frequency_Plan_Design_for_Multibeam_Satellite_Constellations_Using_Integer_Linear_Programming.pdf')
add('R05','TVT','2024','Interference Management by Harnessing Multi-Domain Resources in Spectrum-Sharing Aided Satellite-Ground Integrated Networks','Xiaojin Ding et al.','P1',['双NGSO','动态决策','干扰管理','LSTM/DQN'],
'两个NGSO星座与地面基站共频；联合波束开关/切换与功率调度，并使用时序预测及DQN。',
'同时涉及跨星座干扰和多域决策，可对照我们“仅分频不可行后释放关联”的动机。',
'存在主动关波束和功率调节；必须公平控制服务数量，不能直接拿其低干扰与固定活动规模比较。',
'关闭波束的服务损失如何计入目标？预测误差如何影响干扰和中断？',
'https://eprints.soton.ac.uk/486222/1/MitigateINGSOV2.pdf','10.1109/TVT.2024.3354980','https://arxiv.org/abs/2310.15011',evidence='作者机构全文入口及摘要，TVT 73(6):8306–8321；arXiv初稿2023')
add('R06','TWC','2024（在线2023）','Interference Analysis for Coexistence of Terrestrial Networks With Satellite Services','Byungju Lim, Mai Vu','P1',['聚合干扰','带外泄漏','保护约束','物理分析'],
'分析地面网络对卫星业务的同频和带外泄漏，并推导聚合干扰分布与网络保护设计准则。',
'是物理评价方法参考：区分单源贡献、聚合分布、谱形和保护条件，再考虑近似加速。',
'地面到卫星的干扰方向和天线几何不同；解析分布不能未经验证迁移到我们的确定性轨道快照。',
'哪些条件使解析分布成立？误差在尾部和保护门限附近是否更大？',
'https://par.nsf.gov/servlets/purl/10560872',access='https://par.nsf.gov/servlets/purl/10560872',evidence='NSF存档论文首页/摘要，TWC 23(4):3146起')
add('R07','TCCN','2025在线；记录为卷12','Evolutionary Reinforcement Learning for Resource Efficiency Optimization in Downlink Multi-LEO Communication System with Cross-Layer Interference','Qing Wei et al.','P2',['多LEO','进化强化学习','资源效率'],
'作者机构记录确认多LEO下行、跨层干扰和进化强化学习主题；具体状态/奖励/约束需要全文核对。',
'适合比较单纯DRL与进化搜索混合时的决策效率、稳定性和样本成本。',
'当前仅据机构摘要记录筛选，不推断其“跨层”一定指GSO/NGSO轨道层，也不编造加速结果。',
'跨层指协议层还是轨道层？进化步骤是离线训练还是在线开销？',
'https://openresearch.surrey.ac.uk/esploro/outputs/journalArticle/Evolutionary-Reinforcement-Learning-for-Resource-Efficiency/991059266502346','10.1109/TCCN.2025.3632396',access='https://openresearch.surrey.ac.uk/esploro/outputs/journalArticle/Evolutionary-Reinforcement-Learning-for-Resource-Efficiency/991059266502346',evidence='Surrey作者机构检索记录，在线2025-11-13；页面直接抓取403，全文未读')
add('R08','TCCN','2024（在线2023）','Radio Map-Based Cognitive Satellite-UAV Networks Towards 6G On-Demand Coverage','Wei Feng et al.','P2',['认知无线电','无线电地图','大尺度CSI'],
'面向卫星/UAV认知网络，利用无线电地图及大尺度CSI辅助共享与按需覆盖。',
'为“已有几何/地图信息如何辅助决策”提供方法参考，贴近状态估计—评价—决策闭环。',
'UAV覆盖问题并非馈电选星；无线电地图也不能替代轨道与双端离轴角物理预算。',
'地图预计算与在线更新如何分摊？对估计误差是否鲁棒？',
'https://durham-repository.worktribe.com/output/2048656/radio-map-based-cognitive-satellite-uav-networks-towards-6g-on-demand-coverage','10.1109/TCCN.2023.3345857',access='https://repository.kaust.edu.sa/bitstreams/df5f6ada-cddb-45ef-9591-e7738a1339fc/download',evidence='作者机构摘要与10(3):1075–1089')
add('R09','TCCN','2026（在线2025）','SATSense: Multi-Satellite Collaborative Framework for Spectrum Sensing','作者名单请见来源页','P2',['协作感知','图学习','认知无线电'],
'多卫星协作频谱感知，将感知数据建图，并结合压缩及对比学习缓解传输和丢包影响。',
'若今后从已知精确场景走向不完备观测，可作为感知前端参考。',
'目前我们的轨道/配置是已知输入；感知分类准确率不等于物理EPFD评价误差或决策安全性。',
'感知结果如何转为物理干扰状态？观测成本与检测漏报如何进入闭环？',
'https://scholars.cityu.edu.hk/en/publications/satsense-multi-satellite-collaborative-framework-for-spectrum-sen/','10.1109/TCCN.2025.3584228',evidence='作者机构摘要，卷12:2325–2338，在线2025-06-30，正式2026')
add('R10','TVT','2026（DOI年2025）','Cooperative Spectrum Sharing for Interference Management in LEO Based Integrated Satellite–Terrestrial Networks','Sanguk Park et al.','P2',['认知感知','多普勒','邻频干扰','鲁棒优化'],
'独立星地系统信息不互通时，以能量检测协作感知和功率分配处理同频/邻频干扰，采用SAA。',
'帮助判断“有完整信息”与“需要感知”两种共存问题的差别，并提示多普勒邻频因素。',
'这是星地共享而非NGSO–GSO馈电；当前项目也尚未纳入其邻频/信道不确定性。',
'感知耗时如何影响速率？SAA怎样处理概率约束与样本外风险？',
'https://pure.kaist.ac.kr/en/publications/cooperative-spectrum-sharing-for-interference-management-in-leo-b/','10.1109/TVT.2025.3621705',evidence='作者机构摘要与75(4):6962–6967，2026-04')
add('R11','TVT','2024','Interference Mitigation for Reverse Spectrum Sharing in B5G/6G Satellite-Terrestrial Networks','Hao-Wei Lee et al.','P2',['干扰管理','资源分组','星地共享'],
'围绕反向频谱共享，使用干扰感知资源组共享及网络分组，协调地面与卫星网络资源。',
'适合作为非AI、结构化调度基线，观察分组如何控制搜索规模。',
'地固波束、反向共享场景与我们的下行馈电不同；摘要中的容量收益不能直接迁移。',
'分组所需信息和开销多大？是否遗漏组间聚合干扰？',
'https://wmnlab.ee.ntu.edu.tw/lab/publication/Journal/%5BJ%5D2023_%5BTVT%5DInterference_Mitigation_for_NTN_TN_Spectrum_Sharing_in_B5G_6G_Satellite_Terrestrial_Networks.pdf','10.1109/TVT.2023.3328599',access='https://wmnlab.ee.ntu.edu.tw/lab/publication/Journal/%5BJ%5D2023_%5BTVT%5DInterference_Mitigation_for_NTN_TN_Spectrum_Sharing_in_B5G_6G_Satellite_Terrestrial_Networks.pdf',evidence='作者实验室全文入口/摘要；DOI含2023，论文版面©2024')
add('R12','JSAC','2024','Satellites Beam Hopping Scheduling for Interference Avoidance','Huimin Deng et al.','P1',['跳波束','干扰规避','动态调度'],
'建立吞吐驱动与满意度驱动跳波束问题，采用松弛分解和遗传算法处理调度。',
'适合研究服务目标、干扰规避与时域动作如何结合，并作为学习方法外的搜索基线。',
'调度/用户侧共享不等于馈电EPFD管理；应核对避让造成的服务损失和保护约束。',
'时间槽如何设计？规避约束是几何排斥还是累加功率门限？',
'https://udspace.udel.edu/server/api/core/bitstreams/33fd9739-0567-418a-905b-c2142fa05e10/content','10.1109/JSAC.2024.3459083',access='https://udspace.udel.edu/server/api/core/bitstreams/33fd9739-0567-418a-905b-c2142fa05e10/content',evidence='作者机构存档摘要及42(12):3647–3658；直接抓取有超时')
add('R13','JSAC','2024','Facilitating Spectrum Sharing With Passive Satellite Incumbents','Jonathan Chamberlain, David Starobinski, Joel T. Johnson','P3',['主用户保护','频谱共享','机制设计'],
'NASA官方记录确认该文研究被动卫星既有用户的频谱共享；重点作为保护优先级与制度设计阅读。',
'辅助理解共享不是单纯吞吐最大化，应先明确既有系统权利与保护优先级。',
'被动遥感保护与GSO通信接收EPFD规则不同；不是我们的物理评价算法强基线。',
'优先使用权如何落地？其保护机制依赖哪些观测或外部制度？',
'https://gpm.nasa.gov/node/5130','10.1109/JSAC.2024.3459034',evidence='NASA文献记录：42(12):3719–3733；本轮仅元数据级核验')
add('R14','TCOM','2026（在线2025）','Interference Mitigation in Multibeam Satellite Networks as an Optimal Sublattice Problem','Francesco Lisi et al.','P3',['频率复用','子格优化','非AI基线'],
'将周期网格资源分布转为最优子格，借助可并行枚举改善同资源空间间隔，应用于固定GEO多波束。',
'展示利用问题结构构造有效算法的路线，提醒先对比强结构方法再论证AI。',
'固定GEO周期布局与移动NGSO馈电几何不同，不能直接套用子格假设。',
'周期结构能否在局部近似成立？并行枚举的总开销如何核算？',
'https://researchportal.hw.ac.uk/en/publications/interference-mitigation-in-multibeam-satellite-networks-as-an-opt/','10.1109/TCOMM.2025.3621253',access='https://researchportal.hw.ac.uk/en/publications/interference-mitigation-in-multibeam-satellite-networks-as-an-opt/',evidence='作者机构摘要，74:1940–1951；在线2025-10-14，正式2026')
add('R15','TGCN','2026','Energy Efficient Design for Active RIS-Assisted Integrated Satellite-Terrestrial Networks With RSMA','Jianfeng Shi, Yujie Kang, Yue Li, Baolong Li','P3',['能效','干扰管理','RSMA','RIS'],
'IEEE ComSoc目录核验题名、作者和页码；从标题可知涉及有源RIS、RSMA与星地网络能效。算法细节尚未核对。',
'仅当课题增加通信/计算能耗目标时作为绿色通信方向补充。',
'当前属于目录级线索，不把第三方摘要当作已验证全文；RIS/RSMA也不是现有馈电模型配置。',
'能耗分母计入了哪些电路、RIS放大和计算成本？是否存在能效/保护权衡？',
'https://www.comsoc.org/system/files/2026-02/publications_contents_digest_2025-jan_0.pdf','10.1109/TGCN.2025.3631854',evidence='IEEE ComSoc目录标注2026、1378–1390；DOI来自检索线索，解析未成功，正式引用前再核对')
P=R/'paper_notes'/'论文文献综述'/'六刊相关工作调研_20261118.json'
P.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('Saved',len(rows),'screened records')
