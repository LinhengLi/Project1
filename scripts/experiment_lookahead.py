"""Frozen-window 2x2 ideal-information experiment; no window reselection."""
import csv
import gzip
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

from qv_sim.holding import solve_period
from qv_sim.sharing import Flow, solve
from experiment_temporal import metrics


def write_csv(path, rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    out=Path('results/holding_qos');out.mkdir(parents=True,exist_ok=True)
    original=json.loads(Path('results/temporal_qos/config.json').read_text())
    source=Path(original['source'])
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != original['sha256']:
        raise ValueError('Frozen source hash changed')
    windows={}
    for name,w in original['windows'].items():
        start,end=map(datetime.fromisoformat,[w['start'],w['end_exclusive']])
        n=int((end-start).total_seconds()/5)
        if n%6:
            raise ValueError('Only full holding periods supported')
        windows[name]=[start+timedelta(seconds=5*i) for i in range(n)]
    wanted={t for times in windows.values() for t in times}
    slots={t:{} for t in wanted}
    with gzip.open(source,'rt') as f:
        for r in csv.DictReader(f):
            t=datetime.fromisoformat(r['utc'])
            if t in wanted:
                slots[t][r['station_id'],r['norad_id']]=float(r['capacity_loss10_gbps'])
    gateways=sorted(s['station_id'] for s in json.loads(Path('realdatas/gateway_main_8.json').read_text())['sites'])
    config={'frozen_input':original,'sha256_verified':digest,'period_seconds':30,
            'targets_gbit':{'high':15,'ordinary':9},'load_per_class_gbps':[.6,.9],
            'information':'Saved future links; ideal-information oracle, not operational forecast.',
            'eligible_association':'Available at period start; cannot select a satellite that only appears later.',
            'policies':{'current_throughput':'Unchanged snapshot throughput-first/QoS-second, reallocate every step.',
                        'current_qos':'Unchanged snapshot weighted-deficit-first/throughput-second, reallocate every step.',
                        'future_throughput':'30s delivery, then high deficit, then ordinary deficit.',
                        'future_qos':'30s high deficit, then ordinary deficit, then delivery.'},
            'diagnostics':'Free-reselection future QoS relaxation and fixed-throughput-association QoS allocation isolate resource/association/allocation effects.',
            'protection':'Not applied. No physical protection geometry, victim threshold or coupling model exists yet.'}
    (out/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    traces=[];periods=[];summary=[];diagnostics=[]
    for scenario,times in windows.items():
        for load in [.6,.9]:
            flows=[Flow(g,name,load,minimum,weight) for g in gateways
                   for name,minimum,weight in [('high',.5,4),('ordinary',.3,1)]]
            for policy in config['policies']:
                rows=[];previous={};station_periods=[]
                for start in range(0,len(times),6):
                    tt=times[start:start+6];links=[slots[t] for t in tt]
                    caps=[{s:1.5 for _,s in step} for step in links]
                    objective='throughput' if policy.endswith('throughput') else 'qos'
                    if policy.startswith('future'):
                        result=solve_period(links,caps,flows,objective)
                        association=result['association'];rates=result['rates']
                    else:
                        association=solve(links[0],caps[0],flows,objective)['association']
                        rates=[solve(ls,cs,flows,objective,fixed=association)['rates'] for ls,cs in zip(links,caps)]
                    for k,t in enumerate(tt):
                        for j,g in enumerate(gateways):
                            rows.append({'utc':t.isoformat(),'gateway':g,'high':rates[k][2*j],
                                         'ordinary':rates[k][2*j+1],'satellite':association.get(g,''),
                                         'candidate_count':sum(e[0]==g for e in links[k]),
                                         'switch':int(k==0 and start>0 and previous.get(g)!=association.get(g)),
                                         'invalid_link':int(g in association and (g,association[g]) not in links[k])})
                    for j,g in enumerate(gateways):
                        high=5*sum(r[2*j] for r in rates);ordinary=5*sum(r[2*j+1] for r in rates)
                        station_periods.append({'start':tt[0].isoformat(),'gateway':g,'high_gbit':high,
                                               'ordinary_gbit':ordinary,'high_deficit_gbit':max(0,15-high),
                                               'ordinary_deficit_gbit':max(0,9-ordinary)})
                    if policy=='future_throughput':
                        frozen=solve_period(links,caps,flows,'qos',fixed=association)
                        relaxed=solve_period(links,caps,flows,'qos',free_association=True)
                        diagnostics.append({'scenario':scenario,'load':load,'start':tt[0].isoformat(),
                                            'throughput_high_deficit':result['high_deficit_gbit'],
                                            'fixed_throughput_qos_high_deficit':frozen['high_deficit_gbit'],
                                            'free_reselection_qos_high_deficit':relaxed['high_deficit_gbit']})
                    previous=association
                tag={'scenario':scenario,'load':load,'policy':policy}
                traces.extend(dict(tag,**r) for r in rows)
                periods.extend(dict(tag,**r) for r in station_periods)
                for w in [30,60]:
                    summary.append(dict(tag,**metrics(rows,gateways,w),
                                        high_deficit_gbit=sum(r['high_deficit_gbit'] for r in station_periods),
                                        ordinary_deficit_gbit=sum(r['ordinary_deficit_gbit'] for r in station_periods),
                                        aligned_high_attainment=sum(r['high_deficit_gbit']<=1e-5 for r in station_periods)/len(station_periods)))
                print(scenario,load,policy,flush=True)
    for name,rows in [('summary',summary),('traces',traces),('periods',periods),('diagnostics',diagnostics)]:
        write_csv(out/f'{name}.csv',rows)
    lines=['# 30 秒业务保障选星：四组对照','',
           '复用已有两个窗口；所有组均 30 秒重选、每星 1.5 Gbit/s。未来组使用理想信息。缺口为逐站逐周期正缺口之和，单位 Gbit；交付量为整个 120 秒窗口八站合计。','',
           '|场景|每类负载|策略|高优缺口|普通缺口|对齐达标率 %|滚动30s %|滚动60s %|最长欠速 s|普通交付 Gbit|总交付 Gbit|切换|',
           '|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in summary:
        if r['evaluation_seconds']!=30:
            continue
        other=next(x for x in summary if all(x[k]==r[k] for k in ['scenario','load','policy']) and x['evaluation_seconds']==60)
        lines.append(f"|{r['scenario']}|{r['load']}|{r['policy']}|{r['high_deficit_gbit']:.3f}|{r['ordinary_deficit_gbit']:.3f}|{100*r['aligned_high_attainment']:.2f}|{100*r['high_attainment']:.2f}|{100*other['high_attainment']:.2f}|{r['longest_under_seconds']}|{r['ordinary_gbit']:.3f}|{r['total_gbit']:.3f}|{r['switches']}|")
    lines.extend(['','## 贡献拆分','',
                  '当前与未来 QoS 的比较同时改变信息与目标，不能解释为纯信息收益。当前→未来吞吐量的比较较接近前瞻收益，但次级目标仍不同。最干净的业务目标对照是未来两组；固定未来吞吐关联后重做 QoS 分配进一步区分分配与关联作用。'])
    for scenario in windows:
        for load in [.6,.9]:
            lookup={r['policy']:r for r in summary if r['scenario']==scenario and r['load']==load and r['evaluation_seconds']==30}
            t,q=lookup['future_throughput'],lookup['future_qos']
            dd=[r for r in diagnostics if r['scenario']==scenario and r['load']==load]
            fixed=sum(r['fixed_throughput_qos_high_deficit'] for r in dd)
            relaxed=sum(r['free_reselection_qos_high_deficit'] for r in dd)
            lines.append(f"- {scenario}, load {load}: 前瞻吞吐→前瞻 QoS，高优缺口减少 {t['high_deficit_gbit']-q['high_deficit_gbit']:.3f} Gbit，普通交付变化 {q['ordinary_gbit']-t['ordinary_gbit']:+.3f} Gbit，总交付变化 {q['total_gbit']-t['total_gbit']:+.3f} Gbit。固定吞吐关联再做 QoS 的高优缺口 {fixed:.3f} Gbit；自由逐步重选松弛下界 {relaxed:.3f} Gbit；前瞻 QoS {q['high_deficit_gbit']:.3f} Gbit。下界非零部分在本资源/业务模型内不能仅靠选星消除；与下界的差不能全部解释为预测误差。")
    lines.extend(['','## 边界','',
                  '所有词典序阶段要求求解器报告最优，目标锁定容差 1e-6。未加入平滑或切换惩罚；多解会影响逐步欠速和切换，不能把某次时序分配当作唯一最优解。',
                  '未加入频谱保护：不能把容量任意打折声称为 EESS/NGSO 保护。后续需固定受保护接收机、频段/带宽、耦合或天线增益、限值和聚合规则，再将其映射成逐步容量或显式共享约束。当前求解器已接受逐步变化的链路与星上容量，但尚不包含干扰耦合约束。'])
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    main()
