"""Continuous-window feeder experiment; select windows before optimizing."""
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from qv_sim.sharing import Flow, solve


def select_windows(slots, gateways, length=24):
    """Two-minute windows on genuinely contiguous 5-second data only."""
    times = sorted(slots)
    candidates = []
    for i in range(len(times)-length+1):
        ts = times[i:i+length]
        if (ts[-1]-ts[0]).total_seconds() != 5*(length-1):
            continue
        counts = np.array([[sum(g == e[0] for e in slots[t]) for g in gateways] for t in ts])
        candidates.append((ts, counts))
    transitions = []
    for ts, counts in candidates:
        for j, g in enumerate(gateways):
            low = np.flatnonzero(counts[:, j] <= 2)
            if len(low) and low[0] >= 6 and low[-1] < length-6:
                transitions.append((int(counts[:, j].min()), -len(low), ts[0], g, ts))
    if not transitions:
        raise ValueError('No complete decline/recovery window in existing fine data')
    _, _, _, bottleneck, event = min(transitions)
    stable = []
    for ts, counts in candidates:
        if ts[0] < event[-1]+timedelta(seconds=5) and ts[-1] >= event[0]:
            continue
        if counts.min() <= 2:
            continue
        sets = [set(slots[t]) for t in ts]
        churn = sum(len(a ^ b) for a, b in zip(sets, sets[1:]))
        stable.append((churn, int(np.abs(np.diff(counts, axis=0)).sum()), ts[0], ts))
    if not stable:
        raise ValueError('No disjoint stable continuous control window')
    return {'decline_recovery': event, 'stable': min(stable)[-1]}, bottleneck


def baseline(links, elevations, gateways, greedy=False, capacity=1.5, demand=1.2):
    remaining = {s: capacity for _, s in links}
    association = {}
    for g in gateways:  # Explicit, fixed station-ID order, not optimized per outcome.
        edges = [e for e in links if e[0] == g]
        if edges:
            def key(e):
                rate = min(links[e], remaining[e[1]], demand) if greedy else links[e]
                return (-rate, -elevations[e], e[1])
            edge = min(edges, key=key)
            association[g] = edge[1]
            remaining[edge[1]] -= min(links[edge], remaining[edge[1]], demand)
    return association


def metrics(rows, gateways, evaluation_seconds):
    passes = []
    longest = 0
    for g in gateways:
        rr = [r for r in rows if r['gateway'] == g]
        n = evaluation_seconds//5
        for i in range(len(rr)-n+1):  # every complete rolling window, no partial tails
            passes.append(sum(r['high'] for r in rr[i:i+n])/n >= .5-1e-5)
        run = 0
        for r in rr:
            run = run+5 if r['high'] < .5-1e-5 else 0
            longest = max(longest, run)
    duration = len(rows)//len(gateways)*5
    return {'evaluation_seconds': evaluation_seconds, 'high_attainment': sum(passes)/len(passes),
            'complete_station_windows': len(passes), 'longest_under_seconds': longest,
            'ordinary_gbit': sum(r['ordinary']*5 for r in rows),
            'total_gbit': sum((r['high']+r['ordinary'])*5 for r in rows),
            'throughput_gbps': sum((r['high']+r['ordinary'])*5 for r in rows)/duration,
            'switches': sum(r['switch'] for r in rows),
            'invalid_link_station_seconds': sum(r['invalid_link']*5 for r in rows),
            'high_under_station_seconds': sum((r['high'] < .5-1e-5)*5 for r in rows),
            'invalid_under_station_seconds': sum((r['high'] < .5-1e-5)*r['invalid_link']*5 for r in rows)}


def main():
    out = Path('results/temporal_qos'); out.mkdir(parents=True, exist_ok=True)
    source = Path('results/real_gateway_refinement/candidate_links.csv.gz')
    slots = defaultdict(dict); elevations = defaultdict(dict)
    with gzip.open(source, 'rt') as f:
        for r in csv.DictReader(f):
            t = datetime.fromisoformat(r['utc']); edge = (r['station_id'], r['norad_id'])
            slots[t][edge] = float(r['capacity_loss10_gbps'])
            elevations[t][edge] = float(r['elevation_deg'])
    gateways = sorted(s['station_id'] for s in json.loads(Path('realdatas/gateway_main_8.json').read_text())['sites'])
    windows, bottleneck = select_windows(slots, gateways)
    config = {'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'windows': {k: {'start': v[0].isoformat(), 'end_exclusive': (v[-1]+timedelta(seconds=5)).isoformat()} for k,v in windows.items()},
              'bottleneck_gateway': bottleneck, 'selection': '120s contiguous; event contains <=2 with >=30s before/after; rank minimum count, longest low duration, earliest time; disjoint control min>2, minimum edge-set churn then count variation',
              'step_seconds': 5, 'association_periods': [5,30], 'load_per_class_gbps': [.6,.9],
              'minimum_gbps': [.5,.3], 'weights': [4,1], 'satellite_capacity_gbps': 1.5,
              'capacity_column': 'capacity_loss10_gbps', 'protection': False,
              'evaluation': 'Per-GS rolling mean high rate >=0.5; pooled complete windows at 5s stride. Longest instantaneous high under-rate across GS. Volume is delivered Gbit. Switch counts changes of association after initial selection, including disconnect/reconnect.',
              'model': 'Piecewise constant 5s service; no queue/carryover; expired link gives zero until recovery or scheduled reselection; initial association at window start. Raw means no synthetic tightening/protection, not zero extra loss. Throughput policy retains existing throughput-first/QoS-second allocator; baselines use QoS-first allocator.'}
    (out/'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    summary = []; traces = []
    policies = ['independent', 'capacity_greedy', 'throughput', 'qos']
    for scenario, times in windows.items():
        for load in [.6,.9]:
            flows = [Flow(g, name, load, minimum, weight) for g in gateways
                     for name, minimum, weight in [('high',.5,4),('ordinary',.3,1)]]
            cache = {}
            for period in [5,30]:
                for policy in policies:
                    rows = []; association = {}
                    for i,t in enumerate(times):
                        links = slots[t]; caps = {s:1.5 for _,s in links}
                        previous = association.copy()
                        if i*5 % period == 0:
                            if policy in ['independent','capacity_greedy']:
                                association = baseline(links,elevations[t],gateways,policy=='capacity_greedy',demand=2*load)
                            else:
                                if (t,policy) not in cache:
                                    cache[t,policy] = solve(links,caps,flows,policy)
                                association = cache[t,policy]['association']
                        # Preserve chosen association even when its edge disappears.
                        allocation = solve(links,caps,flows,'throughput' if policy=='throughput' else 'qos',fixed=association)
                        for j,g in enumerate(gateways):
                            rows.append({'utc':t.isoformat(),'gateway':g,'candidate_count':sum(e[0]==g for e in links),
                                         'satellite':association.get(g,''),'high':allocation['rates'][2*j],
                                         'ordinary':allocation['rates'][2*j+1],
                                         'switch':int(i>0 and previous.get(g)!=association.get(g)),
                                         'invalid_link':int(g in association and (g,association[g]) not in links),
                                         'reselection_allowed':int(i*5 % period == 0)})
                    tag = {'scenario':scenario,'load':load,'period_seconds':period,'policy':policy}
                    traces.extend(dict(tag,**r) for r in rows)
                    summary.extend(dict(tag,**metrics(rows,gateways,w)) for w in [30,60])
                    print(scenario,load,period,policy,flush=True)
    for name, records in [('summary',summary),('traces',traces)]:
        with (out/f'{name}.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    runs = []
    for scenario in windows:
        for load in [.6,.9]:
            for period in [5,30]:
                for policy in policies:
                    for g in gateways:
                        rr = [r for r in traces if (r['scenario'],r['load'],r['period_seconds'],r['policy'],r['gateway']) == (scenario,load,period,policy,g)]
                        active = []
                        for r in rr + [None]:
                            if r is not None and r['high'] < .5-1e-5:
                                active.append(r)
                            elif active:
                                runs.append({'scenario':scenario,'load':load,'period_seconds':period,'policy':policy,'gateway':g,
                                             'start':active[0]['utc'],'duration_seconds':5*len(active),
                                             'invalid_link_seconds':5*sum(a['invalid_link'] for a in active),
                                             'minimum_candidates':min(a['candidate_count'] for a in active),
                                             'end_reason':'window_end' if r is None else ('reselection' if r['reselection_allowed'] else 'within_hold_recovery')})
                                active = []
    with (out/'under_rate_runs.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(runs[0]));writer.writeheader();writer.writerows(runs)
    fig, axes = plt.subplots(3,2,figsize=(15,10),sharex='col')
    for col,scenario in enumerate(windows):
        for policy in policies:
            rr=[r for r in traces if r['scenario']==scenario and r['load']==.6 and r['period_seconds']==30 and r['policy']==policy and r['gateway']==bottleneck]
            x=np.arange(len(rr))*5
            axes[1,col].plot(x,[r['high'] for r in rr],label=policy)
            axes[2,col].plot(x,[r['ordinary'] for r in rr],label=policy)
            switches=[k*5 for k,r in enumerate(rr) if r['switch']]
            axes[0,col].scatter(switches,[policies.index(policy)+.2]*len(switches),marker='|',label=policy+' switch')
            if policy=='qos':
                axes[0,col].step(x,[r['candidate_count'] for r in rr],where='post',color='black',label='candidate count')
                for k,r in enumerate(rr):
                    if r['invalid_link']:
                        axes[1,col].axvspan(k*5,k*5+5,color='red',alpha=.12)
        axes[0,col].set_title(scenario+' / '+bottleneck+' / load 0.6 / reselection 30s')
        for row,threshold in [(1,.5),(2,.3)]:
            axes[row,col].axhline(threshold,color='black',ls='--',label='minimum')
        for ax in axes[:,col]:
            ax.legend(fontsize=7);ax.grid(alpha=.25)
        axes[2,col].set_xlabel('Seconds since window start')
    axes[0,0].set_ylabel('Candidates / switch policy index')
    axes[1,0].set_ylabel('High service (Gbit/s)')
    axes[2,0].set_ylabel('Ordinary service (Gbit/s)')
    fig.tight_layout();fig.savefig(out/'timeline.png',dpi=180);fig.savefig(out/'timeline.svg');plt.close(fig)
    lines=['# Continuous-window QoS experiment','', 'See config.json for frozen link-only selection and metric definitions. Red shading: QoS selected link invalid.','',
           '|Scenario|Load/class|Reselect s|Policy|Eval s|High attainment %|Longest under s|Ordinary Gbit|Total Gbit|Mean Gbit/s|Switches|Invalid-under GS-s|',
           '|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in summary:
        lines.append(f"|{r['scenario']}|{r['load']}|{r['period_seconds']}|{r['policy']}|{r['evaluation_seconds']}|{100*r['high_attainment']:.2f}|{r['longest_under_seconds']}|{r['ordinary_gbit']:.2f}|{r['total_gbit']:.2f}|{r['throughput_gbps']:.3f}|{r['switches']}|{r['invalid_under_station_seconds']}|")
    lines.extend(['','The 5s joint policies are the original freely reselected per-snapshot MILP reference, not a temporal look-ahead optimum. No queueing or end-to-end delay claim.'])
    lines.extend(['', '## Paired comparisons (percentage points; same frozen inputs)', ''])
    lookup = {(r['scenario'],r['load'],r['period_seconds'],r['policy'],r['evaluation_seconds']):r for r in summary}
    for scenario in windows:
        for load in [.6,.9]:
            q = lookup[scenario,load,30,'qos',30]
            b = lookup[scenario,load,30,'capacity_greedy',30]
            fast = lookup[scenario,load,5,'qos',30]
            lines.append(f"- {scenario}, load {load}: QoS minus capacity-aware baseline: high attainment {100*(q['high_attainment']-b['high_attainment']):+.2f} pp; longest under-rate shortened by {b['longest_under_seconds']-q['longest_under_seconds']} s; ordinary delivery {q['ordinary_gbit']-b['ordinary_gbit']:+.2f} Gbit; total delivery {q['total_gbit']-b['total_gbit']:+.2f} Gbit. QoS 5s to 30s attainment loss {100*(fast['high_attainment']-q['high_attainment']):+.2f} pp; longest under-rate {fast['longest_under_seconds']} -> {q['longest_under_seconds']} s. Invalid selected links account for {q['invalid_under_station_seconds']}/{q['high_under_station_seconds']} under-rate GS-seconds (not necessarily the longest run).")
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__ == '__main__':
    main()
