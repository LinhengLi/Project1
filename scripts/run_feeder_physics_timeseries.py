"""61-frame frequency-aware diagnostics, fixed reference TX pattern over band."""
import sys,json,math,csv,hashlib,time
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1];project=root/'em-situational-system-main/em-situational-system-main'
sys.path.insert(0,str(project/'backend'))
from skyfield.api import wgs84
from app.services.feeder_interference import matrix,aggregate,s1528,s1428,C
source=root/'results/feeder_association_v1_1/associations.json';data=json.loads(source.read_text(encoding='utf-8'))
profile_path=root/'results/feeder_antenna_sensitivity_v1_2/selected_profile.json';profile=json.loads(profile_path.read_text(encoding='utf-8'))
manifest=project/'data/baselines/feeder_v1/manifest.json'
for item in json.loads(manifest.read_text())['files']:
    assert hashlib.sha256((project/item['path']).read_bytes()).hexdigest()==item['sha256']
assert hashlib.sha256(source.read_bytes()).hexdigest()==profile['association_sha256']
out=root/'results/feeder_physics_v1_3_10min';out.mkdir(exist_ok=True)
grounds={};normals={}
for g in data['ground_stations']:
    grounds[g['id']]=wgs84.latlon(g['latitude'],g['longitude'],elevation_m=g['altitude_m']).itrs_xyz.m
    lat,lon=np.radians([g['latitude'],g['longitude']]);normals[g['id']]=[math.cos(lat)*math.cos(lon),math.cos(lat)*math.sin(lon),math.sin(lat)]
rows=[];details=[];start=time.perf_counter();width0=profile['tx_half_width_deg'];rx_d=C/18.2e9*10**((45.76-7.7)/20)
for frame_index,frame in enumerate(data['frames']):
    links=frame['links'];n=len(links);sat={p['entity_id']:p['ecef_m'] for p in frame['positions']}
    base=matrix(links,sat,grounds,normals,18.2e9,width0,rx_d)
    tx0=np.array([[s1528(t,35,width0,-20) for t in row] for row in base['tx_offaxis_deg']])
    for mode,channels in [('all_cochannel',[0]*n),('antenna_index',[r['antenna_index'] for r in links])]:
        freq=np.array([17.85e9+.1e9*c for c in channels])
        rx0=np.array([[s1428(t,rx_d*18.2e9/C) for t in row] for row in base['rx_offaxis_deg']])
        rxf=np.array([[s1428(t,rx_d*freq[j]/C) for j,t in enumerate(row)] for row in base['rx_offaxis_deg']])
        corrected=base['received_power_w']*(18.2e9/freq[None,:])**2*10**((rxf-rx0)/10)
        for eta in [.4,.6,.8]:
            width=math.sqrt(1200)/math.sqrt(10**3.5/(eta*math.pi**2))
            for side in [-15,-20,-25,-30]:
                gain=np.array([[s1528(t,35,width,side) for t in row] for row in base['tx_offaxis_deg']])
                power=corrected*10**((gain-tx0)/10);a=aggregate(power,links,channels)
                ratio=np.array(a['in_linear']);failed=int(sum(ratio>10**(-12.2/10)))
                row=dict(frame=frame_index,timestamp=frame['timestamp'],active_links=n,efficiency=eta,half_width_deg=width,sidelobe_db=side,diagnostic=mode,failed_links=failed,lf_rate=a['lf_rate'],max_in_db=float(10*np.log10(max(ratio))) if max(ratio)>0 else None,total_interference_w=sum(a['aggregate_power_w']))
                rows.append(row)
                if eta==.6 and side==-20:
                    # Preserve per-link diagnostics, frequency-corrected matrices and nominal comparison.
                    nominal=aggregate(base['received_power_w'],links,channels)
                    details.append(dict(**row,link_ids=[r['link_id'] for r in links],channels=channels,frequency_hz=freq.tolist(),per_link=a,nominal_center_lf=nominal['lf_rate']))
                    np.savez_compressed(out/f'frame_{frame_index:03d}_{mode}.npz',**{**base,'received_power_w':power},link_ids=np.array([r['link_id'] for r in links]),source_frequency_hz=freq)
                    assert np.all(np.isfinite(power)) and np.all(power>=0)
                    np.testing.assert_allclose(sum(np.array(v) for v in a['category_power_w'].values()),a['aggregate_power_w'],rtol=1e-12,atol=0)
    if frame_index%10==0:print('frame',frame_index,'links',n,flush=True)
with (out/'sensitivity_timeseries.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(out/'baseline_per_link.json').write_text(json.dumps(details,indent=2),encoding='utf-8')
summary=dict(version='feeder_physics_v1_3_10min',frames=len(data['frames']),active_min=min(r['active_links'] for r in rows),active_max=max(r['active_links'] for r in rows),association_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),profile_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest(),elapsed_seconds=time.perf_counter()-start,frequency_policy='8 centers 17.85..18.55 GHz; column uses source carrier; ideal zero interchannel leakage; all-cochannel diagnostic uses channel0=17.85GHz',tx_policy='35dBi and selected angular reference pattern held constant over band; not fixed-aperture frequency scaling; RX physical diameter fixed, q and FSPL frequency dependent',sensitivity_policy='eta .4/.6/.8 induces reference widths at fixed peak; four sidelobe levels; same-operator normalized research parameters; not measured equipment',modes={})
for mode in ['all_cochannel','antenna_index']:
    selected=[r for r in rows if r['diagnostic']==mode and r['efficiency']==.6 and r['sidelobe_db']==-20]
    allrows=[r for r in rows if r['diagnostic']==mode]
    summary['modes'][mode]=dict(baseline_lf_min=min(r['lf_rate'] for r in selected),baseline_lf_max=max(r['lf_rate'] for r in selected),baseline_sample_weighted_lf=sum(r['failed_links'] for r in selected)/sum(r['active_links'] for r in selected),sensitivity_lf_min=min(r['lf_rate'] for r in allrows),sensitivity_lf_max=max(r['lf_rate'] for r in allrows),frequency_changed_lf_frames=sum(d['lf_rate']!=d['nominal_center_lf'] for d in details if d['diagnostic']==mode))
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))
