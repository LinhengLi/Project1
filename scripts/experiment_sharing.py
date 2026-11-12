"""Small deterministic eight-GS slot/load experiment using existing candidates."""
import csv
import gzip
import json
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from qv_sim.sharing import Flow, solve


def main():
    out=Path('results/single_slot_sharing');out.mkdir(parents=True,exist_ok=True)
    sites=json.loads(Path('realdatas/gateway_main_8.json').read_text())['sites']
    # Systematic first-day snapshots, not selected by algorithm performance.
    times=[f'2026-11-05T{h:02d}:00:00+00:00' for h in [0,6,12,18]]
    slots=defaultdict(dict)
    source=Path('results/real_gateway_refinement/candidate_links.csv.gz')
    with gzip.open(source,'rt') as f:
        for r in csv.DictReader(f):
            if r['utc'] in times:
                slots[r['utc']][r['station_id'],r['norad_id']]=float(r['capacity_loss10_gbps'])
    if set(slots)!=set(times): raise ValueError('Missing requested snapshots')
    config={'slots':times,'load_factors':[.5,1,1.5,2,3], 'satellite_capacity_gbps':1.5,
            'tightening_factor':.25,'tightening_rule':'For every GS retain its two highest-rate links; multiply all other rates by factor. Synthetic stress test, NOT UEL.',
            'flows_at_load1':[{'name':'high','demand':.6,'minimum':.5,'weight':4},
                              {'name':'ordinary','demand':.6,'minimum':.3,'weight':1}],
            'primary_metric':'sum(w*max(minimum-rate,0))/sum(w*minimum)',
            'note':'Equal-weight slot averages; no queues, user path, interference or end-to-end claims.'}
    (out/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    results=[]
    for time in times:
        original=slots[time]
        for tight in [False,True]:
            links=dict(original)
            if tight:
                for site in sites:
                    g=site['station_id']
                    ranked=sorted([e for e in links if e[0]==g],key=lambda e:(-original[e],e[1]))
                    for edge in ranked[2:]: links[edge]*=config['tightening_factor']
            caps={s:1.5 for _,s in links}
            for load in config['load_factors']:
                flows=[Flow(site['station_id'],f['name'],load*f['demand'],load*f['minimum'],f['weight'])
                       for site in sites for f in config['flows_at_load1']]
                solved={p:solve(links,caps,flows,p) for p in ['independent','throughput','qos']}
                for policy,result in solved.items():
                    result.update({'utc':time,'tightened':tight,'load':load,'policy':policy})
                    results.append(result)
                # Same QoS allocator and constraints, only association fixed to throughput baseline.
                frozen=solve(links,caps,flows,'qos',fixed=solved['throughput']['association'])
                solved['qos']['fixed_throughput_association_deficit']=frozen['weighted_deficit']
                solved['qos']['changed_vs_throughput']=[g for g in sorted(solved['qos']['association'])
                                                        if solved['qos']['association'].get(g)!=solved['throughput']['association'].get(g)]
                print(time,tight,load,flush=True)
    (out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,tight in zip(axes,[False,True]):
        for policy in ['independent','throughput','qos']:
            values=[sum(r['normalized_weighted_deficit'] for r in results if r['tightened']==tight and r['load']==load and r['policy']==policy)/len(times) for load in config['load_factors']]
            ax.plot(config['load_factors'],values,marker='o',label=policy)
        ax.set_title('Synthetic tightening' if tight else 'Original link rates')
        ax.set_xlabel('Business load multiplier');ax.grid(alpha=.3);ax.legend()
    axes[0].set_ylabel('Normalized weighted minimum-rate deficit')
    fig.tight_layout();fig.savefig(out/'qos_load_curve.png',dpi=180);fig.savefig(out/'qos_load_curve.svg');plt.close(fig)


if __name__=='__main__':main()
