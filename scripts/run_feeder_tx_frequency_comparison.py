"""Paired TX-frequency comparison on immutable V1.3 baseline matrices."""
import sys,json,csv,hashlib,math
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1];project=root/'em-situational-system-main/em-situational-system-main'
sys.path.insert(0,str(project/'backend'))
from app.services.feeder_interference import s1528,tx_pattern_at_frequency,aggregate
src=root/'results/feeder_physics_v1_3_10min';out=root/'results/feeder_physics_v1_3_tx_frequency';out.mkdir(exist_ok=True)
association=root/'results/feeder_association_v1_1/associations.json';data=json.loads(association.read_text(encoding='utf-8'))
profile_path=root/'results/feeder_antenna_sensitivity_v1_2/selected_profile.json';profile=json.loads(profile_path.read_text(encoding='utf-8'))
oldsummary=json.loads((src/'summary.json').read_text());assert hashlib.sha256(association.read_bytes()).hexdigest()==oldsummary['association_sha256']
assert hashlib.sha256(profile_path.read_bytes()).hexdigest()==oldsummary['profile_sha256']
manifest=project/'data/baselines/feeder_v1/manifest.json'
for v in json.loads(manifest.read_text())['files']:assert hashlib.sha256((project/v['path']).read_bytes()).hexdigest()==v['sha256']
width=profile['tx_half_width_deg'];rows=[];perlink=[];hashes={};statistics={}
for mode in ['all_cochannel','antenna_index']:
    deltas=[];pair_deltas=[];changed=0;changed_frames=0;oldfails=0;newfails=0;total=0
    for index,frame in enumerate(data['frames']):
        path=src/f'frame_{index:03d}_{mode}.npz';hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        with np.load(path) as z:
            power=z['received_power_w'];theta=z['tx_offaxis_deg'];freq=z['source_frequency_hz'];ids=z['link_ids']
        links=frame['links'];assert ids.tolist()==[r['link_id'] for r in links]
        channels=[0]*len(links) if mode=='all_cochannel' else [r['antenna_index'] for r in links]
        delta=np.array([[tx_pattern_at_frequency(t,float(freq[j]),18.2e9,35,width,-20)-s1528(t,35,width,-20) for j,t in enumerate(row)] for row in theta])
        corrected=power*10**(delta/10)
        old=aggregate(power,links,channels);new=aggregate(corrected,links,channels)
        a=np.array(old['in_linear']);b=np.array(new['in_linear']);mask=(a>0)&(b>0);diff=10*np.log10(b[mask]/a[mask]);deltas.extend(diff.tolist())
        same=np.equal.outer(channels,channels);np.fill_diagonal(same,False);pair_deltas.extend(delta[same&(power>0)].tolist())
        af=a>10**(-12.2/10);bf=b>10**(-12.2/10);flips=int(sum(af!=bf));changed+=flips;changed_frames+=int(flips>0);oldfails+=int(sum(af));newfails+=int(sum(bf));total+=len(links)
        rows.append(dict(frame=index,timestamp=frame['timestamp'],mode=mode,links=len(links),fixed_lf=old['lf_rate'],scaled_lf=new['lf_rate'],classification_flips=flips,max_abs_delta_in_db=float(max(abs(diff))) if len(diff) else 0))
        for i,r in enumerate(links):
            perlink.append(dict(frame=index,timestamp=frame['timestamp'],mode=mode,link_id=r['link_id'],channel=channels[i],frequency_hz=float(freq[i]),fixed_in_linear=float(a[i]),scaled_in_linear=float(b[i]),delta_in_db=float(10*np.log10(b[i]/a[i])) if a[i]>0 and b[i]>0 else None,fixed_failed=bool(af[i]),scaled_failed=bool(bf[i]),fixed_desired_w=float(power[i,i]),scaled_desired_w=float(corrected[i,i])))
        np.savez_compressed(out/f'frame_{index:03d}_{mode}.npz',received_power_w=corrected,link_ids=ids,source_frequency_hz=freq)
    statistics[mode]=dict(link_samples=total,fixed_failed=oldfails,scaled_failed=newfails,fixed_weighted_lf=oldfails/total,scaled_weighted_lf=newfails/total,classification_flips=changed,frames_with_flips=changed_frames,max_abs_delta_in_db=float(max(abs(np.array(deltas)))),median_abs_delta_in_db=float(np.median(abs(np.array(deltas)))),p95_abs_delta_in_db=float(np.percentile(abs(np.array(deltas)),95)),max_abs_cochannel_pair_delta_db=float(max(abs(np.array(pair_deltas)))))
for name,values in [('frame_comparison.csv',rows),('per_link_comparison.csv',perlink)]:
    with (out/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
summary=dict(version='v1.3_tx_frequency_comparison',frames=len(data['frames']),formula='Gpeak(f)=35+20log10(f/18.2GHz); half_width(f)=half_width_ref*18.2GHz/f; LN=-20dB; recompute all S1528-0 1.2 segment boundaries, LF/LB; fixed D and efficiency assumption',scope='same geometry, source channels, power 12dBW, RX and FSPL as V1.3; only TX frequency model changes; theoretical reference, not measured hardware',association_sha256=oldsummary['association_sha256'],profile_sha256=oldsummary['profile_sha256'],baseline_npz_sha256=hashes,results=statistics)
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(statistics,indent=2))
