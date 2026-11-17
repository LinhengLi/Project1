"""Read completed outputs, audit replay inputs, render shareable plots/report."""
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/feeder_openloop_v1_5'


def main():
    data=json.loads((OUT/'replay.json').read_text(encoding='utf-8'))
    summary=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
    config=data['config']; frames=data['frames']; timing=data['timings']; t=np.arange(len(frames))*10/60
    assert len(frames)==720 and frames[-1]['timestamp']=='2026-11-13T13:59:50+00:00'
    source=ROOT/'em-situational-system-main/em-situational-system-main/backend/app/services'
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'scripts/run_feeder_openloop_v1_5.py',ROOT/'scripts/replay_feeder_openloop_v1_5.py',ROOT/'scripts/summarize_feeder_openloop_v1_5.py',ROOT/'scripts/serve_feeder_openloop_v1_5.py',ROOT/'tests/test_feeder_openloop_v1_5.py',ROOT/'experiments/feeder_openloop_v1_5/index.html',source/'feeder_interference.py',source/'feeder_association.py',source/'feeder_gso_epfd.py',source/'feeder_fast_interference.py']}
    operator_samples=Counter(); operator_failed=Counter(); failures=Counter(); total_category=np.zeros(3); maximum_epoch_offset=0; min_gso_elevation=90; propagation_errors=0
    for i,f in enumerate(frames):
        with gzip.open(OUT/f'input_{i:03d}.json.gz','rt',encoding='utf-8') as handle:inp=json.load(handle)
        result=json.loads((OUT/f'result_{i:03d}.json').read_text(encoding='utf-8'))
        links=inp['links'];channels=inp['channels']
        assert len(links)==f['active']==len(channels)
        assert len({r['satellite_id'] for r in links})==len(links)
        for g in set(r['gateway_id'] for r in links):
            ch=[c for r,c in zip(links,channels) if r['gateway_id']==g]
            assert len(ch)<=8 and len(set(ch))==len(ch)
        assert all(r['elevation_deg']>=40 for r in links)
        assert len(inp['protected_links'])==12 and all(r['geometry_visible'] for r in inp['protected_links'])
        min_gso_elevation=min(min_gso_elevation,min(r['elevation_deg'] for r in inp['protected_links']))
        assert result['failed']==len(result['failed_link_ids'])==f['failed']
        for r in links:operator_samples[r['constellation_id']]+=1
        for op,v in result['operators'].items():operator_failed[op]+=v['failed']
        failures.update(result['failed_link_ids']);total_category+=np.array(result['category_power_w']).sum(axis=1)
        orbit=inp['orbit_audit'];maximum_epoch_offset=max(maximum_epoch_offset,abs(orbit['epoch_age_days_min']),abs(orbit['epoch_age_days_max']));propagation_errors+=orbit['propagation_errors']
    # Check persisted system sums for every window (777600 records).
    window_rows=0;peak={};epfd_exceed=Counter()
    with gzip.open(OUT/'window_epfd.csv.gz','rt',encoding='utf-8') as handle:
        for r in csv.DictReader(handle):
            a,b,c=[float(r[k]) for k in ['starlink_w_m2','oneweb_w_m2','combined_w_m2']]
            assert np.isfinite([a,b,c]).all() and min(a,b,c)>=0 and np.isclose(a+b,c,rtol=1e-12,atol=0)
            window_rows+=1
    assert window_rows==720*12*3*30
    for bandwidth in [0,1]:
        for d,diam in enumerate([1,2,5]):
            for system,op in enumerate(['starlink','oneweb','combined']):
                values=np.array([f['epfd_peaks_db'][bandwidth][d] for f in frames],dtype=float)[:,:,system]
                maximum=float(np.nanmax(values));fi,ri=np.unravel_index(np.nanargmax(values),values.shape)
                wi=frames[fi]['peak_window_indices'][bandwidth][d][ri][system]
                key=f'{diam}m_{[40000,1000000][bandwidth]}Hz_{op}'
                peak[key]=dict(dbw_m2=maximum,frame=int(fi),receiver=data['receivers'][ri],window=data['windows'][wi],exceeding_receiver_snapshot_samples=int(np.sum(values>[-164,-150][bandwidth])))
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.25})
    def save(fig,name):
        fig.tight_layout();fig.savefig(OUT/f'{name}.png',dpi=170);fig.savefig(OUT/f'{name}.svg');plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True)
    axes[0].plot(t,[f['failed'] for f in frames],color='#c44457',lw=1);axes[0].set_ylabel('Failed active links')
    axes[1].plot(t,[f['lf']*100 for f in frames],color='#168e85',lw=1);axes[1].set_ylabel('Instantaneous LF (%)');axes[1].set_xlabel('Minutes since 2026-11-13 12:00:00 UTC')
    save(fig,'ngso_failure_lf')
    fig,axes=plt.subplots(4,3,figsize=(15,11),sharex=True,sharey=True)
    for i,ax in enumerate(axes.flat):
        for s,op in enumerate(['Starlink','OneWeb','Combined']):
            values=[f['epfd_peaks_db'][0][0][i][s] for f in frames]
            ax.plot(t,[np.nan if x is None else x for x in values],lw=.7,label=op)
        ax.axhline(-164,color='#c44457',ls='--',lw=.8);ax.set_title(data['receivers'][i],fontsize=8)
        ax.set_xlabel('Minutes');ax.set_ylabel('EPFD dB(W/m2)')
    axes.flat[0].legend(fontsize=7);fig.suptitle('1m / 40kHz: maximum over evaluated windows; dashed = instantaneous reference ceiling',fontsize=11)
    fig.tight_layout(rect=(0,0,1,.97));fig.savefig(OUT/'gso_12_receivers.png',dpi=170);fig.savefig(OUT/'gso_12_receivers.svg');plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(13,8))
    for k,label in [('interference_s','Interference wall'),('ngso_s','NGSO'),('gso_s','GSO')]:axes[0,0].plot(t,[r[k] for r in timing],label=label,lw=.8)
    axes[0,0].legend();axes[0,0].set(xlabel='Minutes',ylabel='Seconds per snapshot')
    axes[0,1].plot(t,[r['active_links'] for r in timing]);axes[0,1].set(xlabel='Minutes',ylabel='Active links')
    for ax,key,label in [(axes[1,0],'active_links','Active links'),(axes[1,1],'ngso_budget_pairs','N*N evaluated NGSO budgets')]:
        ax.scatter([r[key] for r in timing],[r['interference_s'] for r in timing],s=5,alpha=.45);ax.set(xlabel=label,ylabel='Interference wall seconds')
    save(fig,'timing_and_scale')
    validation=dict(status='passed',frames=720,window_rows=window_rows,station_channel_policy='all frames without replacement',max_absolute_epoch_offset_days=maximum_epoch_offset,propagation_error_samples=propagation_errors,min_gso_elevation_deg=min_gso_elevation,operator_samples=dict(operator_samples),operator_failed_samples=dict(operator_failed),category_total_power_w=total_category.tolist(),category_names=['intra_gateway','same_operator_inter_gateway','cross_operator'],epfd_peaks=peak,source_hashes=source_hashes)
    validation['replay_checks']=[json.loads((ROOT/f'results/feeder_openloop_v1_5_replay_check_{i:03d}/validation.json').read_text(encoding='utf-8')) for i in [0,360,719]]
    if (OUT/'peak_scalar_validation.json').exists():
        validation['peak_scalar_check']=json.loads((OUT/'peak_scalar_validation.json').read_text(encoding='utf-8'))
        extra=ROOT/'scripts/check_feeder_openloop_peak_v1_5.py'
        validation['source_hashes'][str(extra.relative_to(ROOT))]=hashlib.sha256(extra.read_bytes()).hexdigest()
    (OUT/'completed_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
    timing_rows='\n'.join(f"| {k} | {v['total']:.3f} | {v['mean']:.6f} | {v['median']:.6f} | {v['p95']:.6f} | {v['maximum']:.6f} |" for k,v in summary['timing_seconds'].items())
    p=peak['1m_40000Hz_combined']
    text=f'''# V1.5 两小时逐快照开环完整计算基准

日期：2026-11-17。站内随机分频不允许重频，由用户明确确认。V1.4.1及原feeder_v1保持不变。

## 场景与口径

使用既有three_constellations场景：218个Starlink站点、13个OneWeb站点、12条原GSO固定保护关联。轨道候选分别10611、651、12条，Starlink文件并非严格Gen1身份筛选结果。保留既有站点来源、社区近似位置及人工仿真点；未确认真实运营状态。没有下载或扩充新数据。

UTC从2026-11-13T12:00:00Z至13:59:50Z，10秒采样，720个起点快照；不另算7200秒终点。初始轨道epoch偏移见audit.json，全程最大绝对偏移{maximum_epoch_offset:.6f}天；传播错误样本{propagation_errors}。沿用Starlink 300–650km、OneWeb 1100–1300km瞬时高度筛选，不声称运行状态筛选。

同运营商、网关ID升序轮询，最高仰角优先，同仰角按卫星ID；仰角至少40°，每站最多8条，每星最多1条。每站8频道无放回随机分配、站间复用；种子20261115，SHA256(seed/frame/gateway)前128位大端构造PCG64随机流。实际频道写入每帧输入。

使用原12dBW/100MHz载波、398K、I/N严格大于−12.2dB判失效；S.1528-0和S.1428-1参数保持。GSO使用1/2/5m、30个既定窗口，Starlink/OneWeb/合计分别保存。完整逐对预算采用原标量公式的数组求值，没有弱项筛选、时间复用、预测或反馈优化。

## 结果

- 活动链路：{summary['active_links_min']}–{summary['active_links_max']}条/帧。
- 失败链路样本：{summary['failed_link_samples']} / 活动链路样本{summary['active_link_samples']}。
- 主汇总LF：{summary['sample_weighted_lf']:.8%}；逐帧LF均值：{summary['frame_mean_lf']:.8%}。均不是连续时间失效时长比例。
- 1m/40kHz/合计的已评价窗口全程峰值：{p['dbw_m2']:.6f}dB(W/m²)，第{p['frame']}帧，{p['receiver']}；超过匹配100%时间瞬时参考上限的接收点快照样本数为{p['exceeding_receiver_snapshot_samples']}（不是连续超限时长）。完整18种口径/带宽/系统峰值见completed_validation.json。
- 站内无重频使同站干扰在理想零邻频泄漏模型下为零，这是基线规则的结果，不能解释为真实设备不存在同站干扰。

## 计时

单调高精度perf_counter，顺序单进程，未主动预热，首帧计入；平台、依赖版本与线程环境见config.json，未强制设置数值库线程数。整体干扰wall time直接测量，包含数组准备、全部逐对几何、方向图、功率、聚合和指标统计。传播、选星、分频、输入/结果I/O、额外独立验证分别记录；网页绘图不计入。输出snapshot_s是快照处理时间，不含启动加载及最终报告生成。分项求和不代替wall time。本轮在日常桌面环境运行，期间有短时测试、抽样重建和浏览器验证活动，未隔离系统负载；这些耗时作为初始规模测量，不作为严格隔离条件下的算法加速比或实时保证。

| 项目（秒） | 总和 | 均值 | 中位数 | P95 | 最大值 |
|---|---:|---:|---:|---:|---:|
{timing_rows}

N*N包含期望信号对角预算，N*(N−1)为非自身有序干扰对；cochannel_pairs为其中同频对，visible_cochannel_pairs为地平线上同频有效对。GSO同时记录12*N几何对、3*12*30*N窗口源槽数及实际有贡献槽数。槽数不等于独立几何计算次数。

## 图与回放

![NGSO](../results/feeder_openloop_v1_5/ngso_failure_lf.png)

![GSO](../results/feeder_openloop_v1_5/gso_12_receivers.png)

![耗时与规模](../results/feeder_openloop_v1_5/timing_and_scale.png)

执行`.venv-ems/Scripts/python.exe scripts/serve_feeder_openloop_v1_5.py`，访问`http://127.0.0.1:8765/experiments/feeder_openloop_v1_5/`。页面提供播放/暂停、跳转、系统/站点/连线筛选、口径/带宽/系统贡献切换，所有指标来自预计算结果；解压逐帧输入需支持DecompressionStream的现代浏览器。

## 验证与复现

新增4项测试：方向图分段及边界对照标量模型；原61帧输入中0/30/60帧完整矩阵对照；随机流站点独立且无重频；原12条GSO关联完全保留。首帧另检查3个受扰链路对全部源的标量预算，以及3颗卫星批量传播与既有Skyfield传播一致性。全720帧审计频道、唯一性、仰角、GSO可见性、失效ID/计数、777600条窗口系统线性贡献求和。

输入保存在input_XXX.json.gz，结果保存在result_XXX.json，window_epfd.csv.gz保留每帧全部窗口系统贡献；只保存首帧完整矩阵，其余可从输入和config重建。无需重跑传播/选星来比较后续算法。

复现命令（输出目录必须不存在，禁止覆盖）：

```powershell
.venv-ems/Scripts/python.exe scripts/run_feeder_openloop_v1_5.py --frames 3 --out results/feeder_openloop_v1_5_pilot_new
.venv-ems/Scripts/python.exe scripts/run_feeder_openloop_v1_5.py --frames 720 --out results/feeder_openloop_v1_5_new
.venv-ems/Scripts/python.exe -m pytest tests/test_feeder_openloop_v1_5.py -q
```

文件哈希见manifest.json，实现及模型源码哈希见completed_validation.json。V1.5是派生研究基准，当前未创建独立冻结快照。

保护线只作为匹配配置的100%时间瞬时参考上限：40kHz −164、1MHz −150dB(W/m²)。单系统与合计分别关联Article22表22-1B及第76号决议表1B，不据此宣称完整曲线或真实运营系统合规。当前未做槽内细采样、全球最坏几何或长期统计；也未实现快速近似算法。下一步可在相同保存输入上测量瓶颈，设计并比较快速算法的误差、漏检与耗时。
'''
    if 'peak_scalar_check' in validation:
        peak_check=validation['peak_scalar_check']; dominant=peak_check['top_sources'][0]
        text+=f"\n## 最高峰专项复核\n\n对第{peak_check['frame']}帧1m/40kHz全程峰值进行了独立逐源标量公式复核，与窗口模型一致（绝对容差1e-10dB）。主导源为{dominant['link_id']}，发射离轴{dominant['tx_offaxis_deg']:.6f}°、GSO接收离轴{dominant['rx_offaxis_deg']:.6f}°，斜距{dominant['range_km']:.6f}km，贡献占比{peak_check['dominant_source_fraction']:.8%}。该保护接收点与该源服务网关在本场景中同址；接近GSO接收主轴的活动下行束导致强峰值。当前无GSO避让或反馈管理，因此这种几何没有被主动排除。复核只确认本模型预算，不确认真实设备或实际同址运行。详见peak_scalar_validation.json。\n"
    report=ROOT/'研究进展/V1_5_两小时开环完整计算基准_20261117.md'
    report.write_text(text,encoding='utf-8')
    # Update final output audit after rendering and validation, never include itself.
    paths=[p for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='manifest.json']
    manifest=dict(files=[dict(path=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],report_sha256=hashlib.sha256(report.read_bytes()).hexdigest())
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status='passed',frames=720,window_rows=window_rows,report=str(report),output_bytes=sum(p.stat().st_size for p in paths)),ensure_ascii=False))


if __name__=='__main__':main()
