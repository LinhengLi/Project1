"""Create figures, weekly-report text and a read-only scan viewer."""
import csv,hashlib,json,shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/feeder_first_frame_scan_20261117'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    summary=read(OUT/'summary.json');config=read(OUT/'config.json');proof=read(OUT/'frequency_only_feasibility.json')
    rows=list(csv.DictReader((OUT/'candidates.csv').open(encoding='utf-8-sig')))
    font=Path('C:/Windows/Fonts/msyh.ttc')
    if font.exists():font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams['axes.unicode_minus']=False
    x=np.arange(1,len(rows)+1);lf=np.array([float(r['lf'])*100 for r in rows]);time=np.array([float(r['interference_s']) for r in rows]);cum=np.cumsum(time);margin=np.array([float(r['gso_max_margin_db']) for r in rows])
    fig,axes=plt.subplots(2,2,figsize=(13,8))
    axes[0,0].plot(x,cum,color='#138c84');axes[0,0].set(xlabel='累计候选方案评价次数',ylabel='累计完整干扰计算耗时 / 秒',title='相同首帧，重复评价不同分频方案')
    axes[0,1].plot(x,time,color='#467cb8');axes[0,1].set(xlabel='方案序号',ylabel='本方案完整干扰计算 / 秒',title='每个方案重新计算全部物理预算')
    axes[1,0].plot(x,lf,color='#aaa',lw=.8,label='各候选方案LF');axes[1,0].plot(x,np.minimum.accumulate(lf),color='#cf435a',label='已评价方案中的最低LF（不保证GSO）');axes[1,0].set(xlabel='累计候选方案评价次数',ylabel='LF / %',title='搜索预算与指标变化');axes[1,0].legend(fontsize=8)
    axes[1,1].plot(x,margin,color='#d08637');axes[1,1].axhline(0,color='#cf435a',ls='--',label='满足瞬时参考上限');axes[1,1].set(xlabel='方案序号',ylabel='GSO最坏超限裕量 / dB',title='当前固定关联与功率下，分频无法消除违例');axes[1,1].legend(fontsize=8)
    for ax in axes.flat:ax.grid(alpha=.25);ax.axvline(101,color='#8096aa',ls=':',lw=1)
    fig.suptitle('V1.5首帧分频扫描：1个原始方案＋100个随机探索＋100个局部候选',fontsize=13);fig.tight_layout(rect=(0,0,1,.95));fig.savefig(OUT/'scan_evidence.png',dpi=180);fig.savefig(OUT/'scan_evidence.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4));vals=[r['source_only_worst_margin_db'] for r in proof['all_channel_witnesses']];ax.bar(range(8),vals,color='#3c8eac');ax.axhline(0,color='#cf435a',ls='--');ax.set(xlabel='分配给主导源的频道编号',ylabel='单源最坏超限裕量 / dB',title='单源下界证据：主导源分配任一频道仍超出参考上限');ax.set_xticks(range(8));ax.grid(axis='y',alpha=.25);fig.tight_layout();fig.savefig(OUT/'frequency_only_infeasibility.png',dpi=180);fig.savefig(OUT/'frequency_only_infeasibility.svg');plt.close(fig)
    # Audit every persisted actual assignment and independent metric reconstruction.
    with np.load(OUT/'candidate_results.npz') as z:
        channels=z['channels'];ratio=z['in_linear'];gs=z['gso_window_system_w_m2'];ids=z['source_link_ids'].tolist()
        assert channels.shape==(201,1250) and len({r.tobytes() for r in channels})==201
        import gzip
        with gzip.open(OUT/'input_000.json.gz','rt',encoding='utf-8') as f:inp=json.load(f)
        for g in {r['gateway_id'] for r in inp['links']}:
            js=[i for i,r in enumerate(inp['links']) if r['gateway_id']==g]
            assert all(len(set(r[js]))==len(js) for r in channels)
        for i,row in enumerate(rows):
            assert int((ratio[i]>10**(-12.2/10)).sum())==int(row['failed'])
        np.testing.assert_allclose(gs[:,:,:,:,0]+gs[:,:,:,:,1],gs[:,:,:,:,2],rtol=1e-12,atol=0)
        from scan_feeder_first_frame_v1_5 import FROZEN
        expected=read(FROZEN/'results/feeder_openloop_v1_5/result_000.json')
        frozen_config=read(FROZEN/'results/feeder_openloop_v1_5/config.json')
        for b,bw in enumerate([4e4,1e6]):
            js=[j for j,w in enumerate(frozen_config['model']['windows']) if w['bandwidth_hz']==bw]
            actual=gs[0][:,:,js,:].max(axis=2);saved=np.array(expected['epfd_peaks_db'][b],dtype=float)
            np.testing.assert_array_equal(np.isnan(saved),actual==0);valid=actual>0;np.testing.assert_allclose(10*np.log10(actual[valid]),saved[valid],rtol=0,atol=1e-10)
    # Independent scalar evaluation of every channel in the infeasibility witness.
    from app.services.feeder_interference import angle,s1428,tx_pattern_at_frequency,C
    from skyfield.api import wgs84
    sites=read(FROZEN/'results/feeder_openloop_v1_5/stations.json');site_map={g['id']:g for g in sites}
    ground={g['id']:wgs84.latlon(g['latitude'],g['longitude'],elevation_m=g['altitude_m']).itrs_xyz.m for g in sites}
    pos={s:np.array(p) for s,p in inp['positions_ecef_m'].items()};link=proof['source_link'];source=pos[link['satellite_id']];target=ground[link['gateway_id']];scalar=[]
    for witness in proof['all_channel_witnesses']:
        receiver=witness['receiver'];g=ground[receiver];protected=next(r for r in inp['protected_links'] if r['gateway_id']==receiver);boresight=pos[protected['satellite_id']]-g;delta=source-g;freq=witness['window']['center_hz'];diam=witness['diameter_m'];bw=witness['window']['bandwidth_hz']
        gt=tx_pattern_at_frequency(angle(target-source,g-source),freq,18.2e9,35,frozen_config['model']['tx_half_width_deg']);gr=s1428(angle(boresight,delta),diam*freq/C)-s1428(0,diam*freq/C)
        p=10**1.2*bw/1e8*10**((gt+gr)/10)/(4*np.pi*np.linalg.norm(delta)**2);margin=10*np.log10(p)-(-164 if bw==4e4 else -150)
        np.testing.assert_allclose(margin,witness['source_only_worst_margin_db'],rtol=0,atol=1e-8);scalar.append(float(margin))
    assert min(scalar)>0
    dump(OUT/'completed_validation.json',dict(status='passed',unique_valid_assignments=201,channel_shape=[201,1250],ngso_failure_counts_reconstructed=True,all_gso_system_sums_valid=True,baseline_all_epfd_peaks_match_frozen=True,scalar_witness_margins_db=scalar,all_candidates_infeasible=summary['feasible_evaluations']==0))
    text=f'''# 周报素材：V1.5首帧子信道分配扫描

周会日期：2026-11-18。实验完成日期：2026-11-17。

## 一句话结论

同一个卫星几何快照，在分频决策中可以需要评价大量不同资源配置。本次明确设置201次候选评价预算，逐候选完整重算耗时{summary['full_recompute_seconds']['total']:.2f}秒，平均{summary['full_recompute_seconds']['mean']:.3f}秒/方案。评价次数并非所有优化算法的必需次数；它由搜索方法、预算、收敛规则和约束可行性共同决定。

## 已冻结的基础

V1.5冻结目录：baselines/feeder_v1_5_20261117，24项相关测试通过。保留两小时720帧完整开环基准、代码、输入、结果、测试、环境及哈希。此次扫描是独立派生实验，不改写冻结版、原两小时结果和既有V1.5可视化。

## 本次固定与改变的量

- 固定UTC：2026-11-13T12:00:00Z；固定1250条最大仰角活动关联、位置、天线、12dBW功率及全部研究物理假设。
- 仅改变8个子信道的分配；230个活动网关内不重频，站间复用。
- 初始方案1个、独立随机分配100个、基于当前最优解的局部候选100个，总计201个互不相同的合法分配。
- 候选更新规则：站内交换两个频道，或改用站内空闲频道；局部搜索交替选取失败链路所在站点与随机站点。随机种子20261117。
- 采用可行优先规则：若满足全部GSO瞬时参考上限，则减少NGSO失败链路；不可行方案按最坏GSO超限dB、违例接收配置数、NGSO失败链路数排序。未证明收敛或全局最优。
- GSO研究约束：12站、1/2/5m、40kHz和1MHz、30个已评价窗口，两系统合计分别对照−164/−150dB(W/m²)。评价的是匹配配置的100%时间瞬时参考上限，不是完整长期合规判定。

## 实测结果

| 项目 | 结果 |
|---|---:|
| 实际候选评价次数（含原始方案） | {summary['evaluations']} |
| 完整干扰计算累计耗时 | {summary['full_recompute_seconds']['total']:.3f}秒 |
| 单方案均值 / P95 | {summary['full_recompute_seconds']['mean']:.6f} / {summary['full_recompute_seconds']['p95']:.6f}秒 |
| 原始失败链路 / LF | {summary['initial']['failed']} / {summary['initial']['lf']:.4%} |
| 全部候选中最低失败数 / LF（不保证GSO） | {summary['best_ngso_without_gso_guarantee']['failed']} / {summary['best_ngso_without_gso_guarantee']['lf']:.4%} |
| 满足全部GSO研究门限的候选 | {summary['feasible_evaluations']} |
| 原始分配的一轮完整局部邻域 | {summary['initial_neighborhood_size']}个候选 |
| 按实测单次均值外推一轮完整邻域（未实际枚举） | {summary['estimated_full_initial_neighborhood_s']:.1f}秒，约{summary['estimated_full_initial_neighborhood_s']/60:.1f}分钟 |

![扫描证据](scan_evidence.png)

## 不是“多试几次就能满足约束”

不仅201个候选未找到可行分配，还获得了固定关联、固定功率条件下的单源不可行证据：{proof['source_link']['link_id']}。对其8个频道逐一计算独立贡献，最小的最坏超限裕量仍为{proof['minimum_over_8_channels_worst_margin_db']:.6f}dB。聚合贡献非负，因此其他源无法抵消它。

这说明在上述12站、全部窗口和参考口径保护要求下，任何仅分频方案都无法完全满足门限。频道调整将主导干扰移到另一个被评价窗口，而不是移出保护频段。该结论仅适用于当前假设模型、固定活动关联和功率，不代表真实运营系统违规，也不证明引入换星、暂停链路或功率控制后的问题不可行。

![分频不可行证据](frequency_only_infeasibility.png)

## 周会上可以怎么说

> 我们已完成并冻结异构星座两小时720快照的完整干扰评价基准。单个既定配置约1秒，但一个决策需要评价多少次，取决于优化器。本次在同一首帧实际扫描201个合法分配，累计完整干扰计算约{summary['full_recompute_seconds']['total']:.0f}秒。一个常用站内交换/空闲频道调整邻域就有5510个候选，如果全部采用当前完整重算实现，一轮估计约{summary['estimated_full_initial_neighborhood_s']/60:.0f}分钟。因此，需要研究面向决策过程的高效干扰评价和动态更新。同时，单源下界表明本帧仅靠分频不能完全满足GSO保护，需要先明确后续允许的管理动作。

## 必须保留的比较边界

1. 201是实验预算，不是证明一次决策至少必须算201次；5510是指定完整邻域的大小，不代表任何优化器都要枚举。
2. 本次是同一静态几何下的重复方案评价，还不是跨时刻动态算法，也不是连续时间闭环。
3. 当前逐候选重算包括NGSO全部N×N几何、方向图、功率，及GSO全部参考窗口、聚合指标；不缓存几何、不做近似。I/O、候选生成及预先进行的8次单源响应诊断不计入候选干扰累计时间，分别记录。
4. 固定几何下的精确缓存、确定零贡献排除等工程优化可能大幅降耗；本实验不能证明AI或近似不可替代，后续需要加入强精确对照。
5. 目标中的GSO最坏裕量差别可能很小，LF最低方案不一定是可行优先目标最优方案。两者分别报告，不混用。
6. 合法分配空间约为10^{config['global_assignment_log10']:.2f}量级，只用于说明组合规模；绝不能按该数量乘单次耗时，声称是实际算法开销。

## 复现与文件

`scripts/scan_feeder_first_frame_v1_5.py`读取冻结快照首帧，输出到results/feeder_first_frame_scan_20261117；输出目录存在时拒绝覆盖。candidate_results.npz保留全部201个实际频道向量、逐链路I/N和全窗口三系统贡献；candidates.csv保留逐次指标、阶段、最优解接受情况和直接计时。原始输入、配置、单源证据、验证和哈希同目录保存。
'''
    (OUT/'周报说明.md').write_text(text,encoding='utf-8')
    materials=ROOT/'周报素材/20261118_V1_5首帧分频扫描';materials.mkdir(parents=True,exist_ok=True)
    for name in ['周报说明.md','scan_evidence.png','scan_evidence.svg','frequency_only_infeasibility.png','frequency_only_infeasibility.svg','summary.json','candidates.csv','frequency_only_feasibility.json']:shutil.copy2(OUT/name,materials/name)
    page=ROOT/'可视化页面/首帧分频扫描_20261117';page.mkdir(exist_ok=True)
    for name in ['scan_evidence.png','frequency_only_infeasibility.png','summary.json','candidates.csv','config.json','frequency_only_feasibility.json','周报说明.md']:shutil.copy2(OUT/name,page/name)
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V1.5首帧分频扫描 · 周报</title><style>body{{background:#0a1525;color:#e0edf8;font:16px system-ui;max-width:1200px;margin:30px auto;padding:20px}}a{{color:#6de3c8}}p{{line-height:1.8;color:#acc0d8}}.cards{{display:flex;gap:20px;flex-wrap:wrap}}.card{{background:#183048;padding:22px;border-radius:12px}}b{{font-size:26px;color:#71dfc5}}img{{width:100%;background:white;margin:18px 0;border-radius:10px}}</style><a href="../">← 档案首页</a><h1>同一快照，为一个决策评价多少分频方案？</h1><p>V1.5首帧 · UTC 2026-11-13 12:00:00 · 1250条固定活动链路 · 230个活动网关 · 站内无重频</p><div class="cards"><div class="card">实测候选评价<br><b>201次</b></div><div class="card">累计完整干扰计算<br><b>{summary['full_recompute_seconds']['total']:.2f}秒</b></div><div class="card">GSO全部门限可行方案<br><b>{summary['feasible_evaluations']}个</b></div></div><p>201次是设定搜索预算，不是所有算法的必要次数。原始分配的一轮完整站内交换/空闲频道调整邻域有5510个候选，按实测单次均值外推约{summary['estimated_full_initial_neighborhood_s']/60:.1f}分钟（估计，未实际枚举）。</p><img src="scan_evidence.png" alt="扫描次数、累计耗时、LF和GSO超限变化"><h2>仅分频不可行的证据</h2><p>在固定关联和功率下，一条主导链路无论分配到8个频道中的哪一个，其单独贡献仍超出至少一项GSO瞬时参考上限约{proof['minimum_over_8_channels_worst_margin_db']:.2f}dB；其他源的非负贡献无法抵消它。此结论属于当前假设模型，不是现实违规判定。</p><img src="frequency_only_infeasibility.png" alt="8个频道下的单源超限下界"><p>本次展示未缓存几何的完整重算成本，不证明该成本不可避免，也不证明AI必需。后续应与固定几何精确缓存及增量评价进行公平比较。</p><a href="周报说明.md">周报讲稿与口径说明</a> · <a href="candidates.csv">逐候选数据CSV</a> · <a href="summary.json">汇总JSON</a></html>'''
    (page/'index.html').write_text(html,encoding='utf-8')
    home=ROOT/'可视化页面/index.html';s=home.read_text(encoding='utf-8')
    link='<a class="card hero" href="首帧分频扫描_20261117/"><b>周报 · 独立派生实验</b><h2>V1.5首帧子信道分配扫描</h2><p>201次实测评价、累计耗时及分频不可行证据</p></a>'
    if 'href="首帧分频扫描_20261117/"' not in s:home.write_text(s.replace('<div class="grid">',link+'<div class="grid">'),encoding='utf-8')
    dump(OUT/'manifest.json',dict(files=[dict(path=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='manifest.json'],source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'scripts/scan_feeder_first_frame_v1_5.py',Path(__file__)]}))
    print('report and figures created',materials,flush=True)

if __name__=='__main__':main()
