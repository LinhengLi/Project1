"""Derived weekly-report scan: frozen first frame, fixed geometry, exact recompute.

201 evaluations are an explicit search budget, not a necessary iteration count.
"""
import csv,gzip,hashlib,json,math,platform,sys
from collections import Counter
from pathlib import Path
from time import perf_counter
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/'baselines/feeder_v1_5_20261117/workspace'
sys.path.insert(0,str(FROZEN/'scripts'))
from run_feeder_openloop_v1_5 import exact_ngso,epfd_windows,K,wgs84

OUT=ROOT/'results/feeder_first_frame_scan_20261117'
def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    source=FROZEN/'results/feeder_openloop_v1_5'
    config=json.loads((source/'config.json').read_text(encoding='utf-8'));model=config['model']
    with gzip.open(source/'input_000.json.gz','rt',encoding='utf-8') as f:inp=json.load(f)
    stations=json.loads((source/'stations.json').read_text(encoding='utf-8'))
    ground={};normal={}
    for g in stations:
        ground[g['id']]=wgs84.latlon(g['latitude'],g['longitude'],elevation_m=g['altitude_m']).itrs_xyz.m
        lat,lon=np.radians([g['latitude'],g['longitude']]);normal[g['id']]=np.array([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)])
    links=inp['links'];protected=inp['protected_links'];pos=inp['positions_ecef_m'];n=len(links)
    groups={g:np.array([i for i,r in enumerate(links) if r['gateway_id']==g]) for g in sorted({r['gateway_id'] for r in links})}
    operators=np.array([r['constellation_id'] for r in links]);noise=K*model['noise_k']*model['bandwidth_hz']
    windows=model['windows'];limits=np.array([-164 if w['bandwidth_hz']==4e4 else -150 for w in windows])
    def gso(ch):
        return epfd_windows(sources=[pos[r['satellite_id']] for r in links],targets=[ground[r['gateway_id']] for r in links],receivers=[ground[r['gateway_id']] for r in protected],boresights=[pos[r['satellite_id']] for r in protected],normals=[normal[r['gateway_id']] for r in protected],carrier_centers_hz=17.85e9+1e8*ch,carrier_bandwidths_hz=model['bandwidth_hz'],tx_powers_w=10**(model['tx_dbw']/10),windows=windows,diameters_m=model['diameters_m'],tx_half_width_deg=model['tx_half_width_deg'])['epfd_w_m2_by_source']
    def score(r):
        return (0,r['failed'],r['gso_max_margin_db']) if r['gso_feasible'] else (1,r['gso_max_margin_db'],r['gso_exceeding_receiver_configs'],r['failed'])
    neighborhood=sum(len(js)*(len(js)-1)//2+len(js)*(8-len(js)) for js in groups.values())
    logspace=sum(math.lgamma(9)/math.log(10)-math.lgamma(9-len(js))/math.log(10) for js in groups.values())
    setup=dict(version='first_frame_scan_from_frozen_v1_5',timestamp=inp['timestamp'],active_links=n,active_gateways=len(groups),occupancy=dict(Counter(len(v) for v in groups.values())),candidate_budget=201,
        stages='original 1 + independent random assignments 100 + incumbent-based one-gateway local moves 100',seed=20261117,
        constraints='fixed satellite association, positions, 12dBW power; <=8 channels per gateway without repetition; same channel may be reused across gateways',
        objective='feasible first: minimize NGSO failures if all GSO reference ceilings satisfied; otherwise reduce worst GSO excess dB, then violating receiver configurations, then NGSO failures; only research instantaneous ceilings',
        gso_constraints='combined contributions at all 12 receivers, 1/2/5m, both 40kHz and1MHz, all30 evaluated windows; ceilings -164/-150dB(W/m2); no full statistical compliance claim',
        neighbor_definition='one pair swap within one gateway OR move one active link to one locally unused channel',initial_neighborhood_size=neighborhood,global_assignment_log10=logspace,
        timing='full NGSO N*N geometry/pattern/budget recomputed and GSO all reference windows recomputed for every candidate; no geometry cache or incremental evaluation; perf_counter; validation and I/O separately timed; no warmup',
        limitation='baseline policy, not unavoidable computation cost; budgets and neighborhood are chosen, no global optimality or convergence claim; fixed-geometry exact caching remains a required future comparison',
        frozen_manifest_sha256=digest(FROZEN.parent/'manifest.json'),input_sha256=digest(source/'input_000.json.gz'),script_sha256=digest(Path(__file__)),platform=platform.platform(),dependencies=config['dependencies'])
    dump(OUT/'config.json',setup)
    # Single-source lower bound: sum of nonnegative contributions >= each source.
    # All-same-channel calls below tabulate source responses, not feasible allocations.
    witness_start=perf_counter();source_margins=[];source_locations=[]
    for ch in range(8):
        ep=gso(np.full(n,ch))
        margin=10*np.log10(np.maximum(ep,np.finfo(float).tiny))-limits[None,None,:,None]
        source_margins.append(margin.max(axis=(0,1,2)))
        source_locations.append(margin.reshape(-1,n).argmax(axis=0))
    source_margins=np.array(source_margins);minimum=source_margins.min(axis=0);j=int(minimum.argmax())
    witnesses=[]
    for ch in range(8):
        d,r,w=np.unravel_index(source_locations[ch][j],(3,12,30))
        witnesses.append(dict(channel=ch,source_only_worst_margin_db=float(source_margins[ch,j]),receiver=protected[r]['gateway_id'],diameter_m=model['diameters_m'][d],window=windows[w]))
    feasibility=dict(status='frequency_only_infeasible_certificate' if minimum[j]>0 else 'not_proved_infeasible',source_link=links[j],minimum_over_8_channels_worst_margin_db=float(minimum[j]),all_channel_witnesses=witnesses,diagnostic_gso_calls=8,wall_s=perf_counter()-witness_start,
        argument='Under the stated fixed-association/power constraints, this source alone exceeds at least one required ceiling for every available channel. Aggregate nonnegative power cannot cancel it. This proves no frequency-only feasible allocation if the reported minimum margin is positive. Diagnostic source response calls are not counted as feasible search candidates.')
    dump(OUT/'frequency_only_feasibility.json',feasibility)
    print('feasibility',feasibility['status'],'minimum margin',round(float(minimum[j]),3),flush=True)
    rng=np.random.default_rng(20261117);channels=np.array(inp['channels']);incumbent=channels.copy();incumbent_row=None;best_index=0;best_lf_index=0;seen=set();records=[];assignments=[];ratios=[];gso_values=[];cumulative=0.;start=perf_counter()
    for candidate in range(201):
        proposal_start=perf_counter()
        if candidate==0:proposal=channels.copy();stage='original'
        elif candidate<=100:
            proposal=np.zeros(n,dtype=int);stage='random_exploration'
            for js in groups.values():proposal[js]=rng.permutation(8)[:len(js)]
        else:
            stage='local_search'
            for attempt in range(10000):
                proposal=incumbent.copy()
                # Alternate targeted and uniform gateway choice, independent of future states.
                if candidate%2 and records:
                    bad=np.where(ratios[best_index]>10**(model['threshold_db']/10))[0]
                    gateway=links[int(rng.choice(bad))]['gateway_id'] if len(bad) else str(rng.choice(list(groups)))
                else:gateway=str(rng.choice(list(groups)))
                js=groups[gateway];i=int(rng.choice(js));available=np.setdiff1d(np.arange(8),proposal[js])
                if len(available) and rng.random()<.35:proposal[i]=int(rng.choice(available))
                else:
                    a,b=rng.choice(js,size=2,replace=False);proposal[a],proposal[b]=proposal[b],proposal[a]
                if proposal.tobytes() not in seen:break
            else:raise RuntimeError('No unique neighbor found')
        assert proposal.tobytes() not in seen;seen.add(proposal.tobytes())
        for js in groups.values():assert len(np.unique(proposal[js]))==len(js)
        proposal_s=perf_counter()-proposal_start
        wall=perf_counter();t=perf_counter()
        power=exact_ngso(links,pos,ground,normal,proposal,model['tx_half_width_deg'],model['rx_diameter_m']);ngso_s=perf_counter()-t;t=perf_counter()
        ep=gso(proposal);gso_s=perf_counter()-t;t=perf_counter()
        mask=proposal[:,None]==proposal[None,:];np.fill_diagonal(mask,False)
        ratio=(power*mask).sum(axis=1)/noise;failed=ratio>10**(model['threshold_db']/10)
        sums=np.stack([ep[:,:,:,operators==op].sum(axis=-1) for op in ['starlink','oneweb']]+[ep.sum(axis=-1)],axis=-1)
        combined=sums[:,:,:,2];margin=10*np.log10(np.maximum(combined,np.finfo(float).tiny))-limits[None,None,:]
        receiver_margins=np.stack([margin[:,:,np.array([w['bandwidth_hz']==bw for w in windows])].max(axis=2) for bw in [4e4,1e6]],axis=-1)
        maxmargin=float(margin.max());exceed=int((receiver_margins>0).sum());aggregation_s=perf_counter()-t;interference_s=perf_counter()-wall
        cumulative+=interference_s
        row=dict(candidate=candidate,stage=stage,changed_from_incumbent=int(np.sum(proposal!=incumbent)),assignment_sha256=hashlib.sha256(proposal.tobytes()).hexdigest(),failed=int(failed.sum()),lf=float(failed.mean()),failed_starlink=int(failed[operators=='starlink'].sum()),failed_oneweb=int(failed[operators=='oneweb'].sum()),gso_feasible=exceed==0,gso_exceeding_receiver_configs=exceed,gso_max_margin_db=maxmargin,ngso_s=ngso_s,gso_s=gso_s,aggregation_s=aggregation_s,interference_s=interference_s,cumulative_interference_s=cumulative,proposal_s=proposal_s)
        improved=incumbent_row is None or score(row)<score(incumbent_row)
        if improved:incumbent=proposal.copy();incumbent_row=row.copy();best_index=candidate
        row['accepted_as_incumbent']=improved;row['incumbent_candidate']=best_index;row['incumbent_failed']=incumbent_row['failed'];row['incumbent_gso_max_margin_db']=incumbent_row['gso_max_margin_db']
        if candidate and row['failed']<records[best_lf_index]['failed']:best_lf_index=candidate
        records.append(row);assignments.append(proposal.copy());ratios.append(ratio);gso_values.append(sums)
        if candidate==0:
            expected=json.loads((source/'result_000.json').read_text(encoding='utf-8'))
            assert row['failed']==expected['failed']==19
            vals=np.array(expected['in_db'],dtype=float);valid=np.isfinite(vals);np.testing.assert_allclose(10*np.log10(ratio[valid]),vals[valid],atol=1e-10,rtol=0)
        if candidate%10==0 or candidate==200:print(json.dumps({k:row[k] for k in ['candidate','stage','failed','gso_max_margin_db','interference_s','cumulative_interference_s','incumbent_candidate']}),flush=True)
    io_start=perf_counter()
    with (OUT/'candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    np.savez_compressed(OUT/'candidate_results.npz',channels=np.array(assignments,dtype=np.int8),in_linear=np.array(ratios),gso_window_system_w_m2=np.array(gso_values),source_link_ids=np.array([r['link_id'] for r in links]),receiver_link_ids=np.array([r['link_id'] for r in protected]))
    shutil_source=OUT/'input_000.json.gz';shutil_source.write_bytes((source/'input_000.json.gz').read_bytes())
    times=np.array([r['interference_s'] for r in records]);best=records[best_index];lfbest=records[best_lf_index]
    summary=dict(evaluations=len(records),feasible_evaluations=sum(r['gso_feasible'] for r in records),initial=records[0],best_by_stated_objective=best,best_ngso_without_gso_guarantee=lfbest,full_recompute_seconds=dict(total=float(times.sum()),mean=float(times.mean()),median=float(np.median(times)),p95=float(np.percentile(times,95)),maximum=float(times.max())),search_wall_s=perf_counter()-start,result_io_s=perf_counter()-io_start,initial_neighborhood_size=neighborhood,estimated_full_initial_neighborhood_s=neighborhood*float(times.mean()),global_assignment_log10=logspace,frequency_only_infeasibility_proved=minimum[j]>0,
        budgets=[dict(evaluations=k,measured_interference_s=records[k-1]['cumulative_interference_s'],best_failed=min(r['failed'] for r in records[:k])) for k in [1,21,51,101,151,201]],
        limitations=setup['limitation'])
    summary['frequency_only_infeasibility_proved']=bool(summary['frequency_only_infeasibility_proved'])
    dump(OUT/'summary.json',summary)
    dump(OUT/'validation.json',dict(status='passed',unique_assignments=len(seen),all_station_channels_without_repetition=True,baseline_failed_and_in_matches_frozen=True,gso_shape=list(np.array(gso_values).shape),maxima_finite=bool(np.all(np.isfinite(times)))))
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
