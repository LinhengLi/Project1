"""Refine low-candidate intervals; export geometry and hypothetical budgets."""
import csv
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from skyfield.api import EarthSatellite, load, wgs84
from sgp4 import omm
from sgp4.api import Satrec


def main():
    out = Path('results/real_gateway_refinement')
    out.mkdir(parents=True, exist_ok=True)
    source = Path('results/real_gateway_scan')
    config = json.loads((source/'config.json').read_text())
    sites = config['sites']
    start = datetime.fromisoformat(config['start_utc'])
    coarse = np.zeros((8, 4320), dtype=int)
    index = {s['station_id']: i for i,s in enumerate(sites)}
    with (source/'counts.csv').open() as f:
        for r in csv.DictReader(f):
            if int(r['mask_deg']) == 25:
                t = int((datetime.fromisoformat(r['utc'])-start).total_seconds()/60)
                coarse[index[r['station_id']], t] = int(r['visible_count'])
    flagged = np.any(coarse <= 2, axis=0)
    seconds = set(range(0, 72*3600, 60))
    for minute in np.flatnonzero(flagged):
        seconds.update(range(max(0,int(minute)*60-120), min(72*3600,int(minute)*60+180),5))
    seconds = np.array(sorted(seconds))
    dates = [start + timedelta(seconds=int(s)) for s in seconds]
    ts = load.timescale(builtin=True)
    times = ts.from_datetimes(dates)
    records = json.loads(Path('realdatas/starlink_real_1600_gp.json').read_text())
    observers = [wgs84.latlon(s['lat_deg'],s['lon_deg']) for s in sites]
    visible = np.zeros((8,len(records),len(seconds)), dtype=bool)
    # Explicit exploratory parameters, NOT measured Starlink or authorized spectrum.
    budget = {'frequency_ghz':48.0,'bandwidth_hz':250e6,'gs_eirp_dbw':65.0,
              'satellite_gt_db_per_k':5.0,'extra_loss_db_cases':[3.0,10.0,20.0],
              'implementation_gap_db':3.0,'spectral_efficiency_cap':6.0,
              'satellite_max_gs_cases':[1,2,4], 'satellite_capacity_gbps_cases':[1,2,4],
              'gs_demand_gbps_cases':[0.5,1,2],
              'warning':'Hypothetical sensitivity cases; no rain climatology, EESS/NGSO interference or frequency authorization model.'}
    count_capacity = np.zeros((3,8,len(seconds)))
    with gzip.open(out/'candidate_links.csv.gz','wt',newline='',encoding='utf-8') as f:
        writer=csv.writer(f)
        writer.writerow(['utc','station_id','norad_id','elevation_deg','range_km','capacity_loss3_gbps','capacity_loss10_gbps','capacity_loss20_gbps'])
        for k,r in enumerate(records):
            model=Satrec(); omm.initialize(model,r)
            sat=EarthSatellite.from_satrec(model,ts)
            state=sat.at(times)
            if state.message is not None and any(m for m in np.atleast_1d(state.message)):
                raise RuntimeError(f"Propagation failed: {r['NORAD_CAT_ID']}")
            for j,obs in enumerate(observers):
                alt,_,distance=(sat-obs).at(times).altaz()
                good=alt.degrees>=25
                if not np.isfinite(alt.degrees).all(): raise RuntimeError('Invalid geometry')
                visible[j,k]=good
                ix=np.flatnonzero(good)
                fspl=92.45+20*np.log10(distance.km[ix])+20*np.log10(budget['frequency_ghz'])
                capacities=[]
                for case,loss in enumerate(budget['extra_loss_db_cases']):
                    snr=65+5-fspl-loss+228.6-10*np.log10(250e6)-3
                    capacity=250e6*np.minimum(6,np.log2(1+10**(snr/10)))/1e9
                    capacities.append(capacity)
                    count_capacity[case,j,ix]+=capacity
                writer.writerows((dates[t].isoformat(),sites[j]['station_id'],r['NORAD_CAT_ID'],
                                  round(float(alt.degrees[t]),5),round(float(distance.km[t]),3),
                                  *(round(float(c[n]),6) for c in capacities)) for n,t in enumerate(ix))
            if (k+1)%400==0: print(f'Refined {k+1}/{len(records)}',flush=True)
    counts=visible.sum(axis=1)
    uniform=(seconds%60==0)
    refined=~uniform
    stats=[]
    for j,s in enumerate(sites):
        stats.append({'station_id':s['station_id'],'coarse_low_samples':int((coarse[j]<=2).sum()),
                      'min_over_all_evaluated_samples':int(counts[j].min()),
                      'zero_evaluated_samples':int((counts[j]==0).sum()),
                      'min_added_samples':int(counts[j,refined].min()) if refined.any() else None})
    # Exact cardinality feasibility for eight GS via generalized Hall condition.
    feasibility=[]
    for limit in [1,2,4]:
        feasible=np.ones(uniform.sum(),dtype=bool)
        best_deficit=np.zeros(uniform.sum(),dtype=int)
        v=visible[:,:,uniform]
        for subset in range(1,256):
            members=[j for j in range(8) if subset & (1<<j)]
            neighbors=v[members].any(axis=0).sum(axis=0)
            deficit=len(members)-limit*neighbors
            best_deficit=np.maximum(best_deficit,deficit)
            feasible &= deficit<=0
        feasibility.append({'max_gs_per_satellite':limit,'all_8_gs_assignable_fraction_60s':float(feasible.mean()),
                            'maximum_hall_deficit':int(best_deficit.max())})
    capacity_screen=[]
    for case,loss in enumerate(budget['extra_loss_db_cases']):
        for demand in budget['gs_demand_gbps_cases']:
            capacity_screen.append({'extra_loss_db':loss,'gs_demand_gbps':demand,
                                    'per_station_optimistic_insufficiency_fraction_60s':{
                                        s['station_id']:float((count_capacity[case,j,uniform]<demand).mean()) for j,s in enumerate(sites)}})
    result={'station_refinement':stats,'access_matching':feasibility,
            'capacity_screen':capacity_screen,
            'capacity_screen_note':'Sum of all candidate capacities is an optimistic bound, not a feasible resource allocation; assumes every candidate GS link can operate simultaneously.'}
    (out/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (out/'config.json').write_text(json.dumps({'source_scan':config,'low_threshold':2,'padding_seconds':120,
                                             'fine_step_seconds':5,'evaluated_times':len(seconds),
                                             'flagged_coarse_times':int(flagged.sum()),'budget':budget},indent=2),encoding='utf-8')
    with (out/'counts.csv').open('w',newline='') as f:
        w=csv.writer(f); w.writerow(['utc','station_id','count','is_uniform_60s_sample'])
        w.writerows((dates[t].isoformat(),s['station_id'],int(counts[j,t]),bool(uniform[t])) for j,s in enumerate(sites) for t in range(len(seconds)))
    # Group coarse low-candidate samples into runs, without implying exact boundaries.
    with (out/'low_intervals.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['station_id','first_low_sample','last_low_sample','coarse_samples'])
        for j,s in enumerate(sites):
            indexes=np.flatnonzero(coarse[j]<=2)
            for run in np.split(indexes,np.flatnonzero(np.diff(indexes)>1)+1):
                if len(run): w.writerow([s['station_id'],(start+timedelta(minutes=int(run[0]))).isoformat(),(start+timedelta(minutes=int(run[-1]))).isoformat(),len(run)])
    print(json.dumps({'station_refinement':stats,'access_matching':feasibility,'evaluated_times':len(seconds)},indent=2))


if __name__=='__main__': main()
