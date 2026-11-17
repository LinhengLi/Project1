"""V1.4 reference GSO interference and timed non-AI bounded screening pilot."""
import sys,json,hashlib,csv,platform,time
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1];project=root/'em-situational-system-main/em-situational-system-main'
sys.path.insert(0,str(project/'backend'))
from skyfield.api import wgs84
from app.services.feeder_fast_interference import compute,channel_sums
from app.services.feeder_interference import K,C,angle,s1428,tx_pattern_at_frequency
source=root/'results/feeder_association_v1_1/associations.json';data=json.loads(source.read_text(encoding='utf-8'))
profile_file=root/'results/feeder_antenna_sensitivity_v1_2/selected_profile.json';profile=json.loads(profile_file.read_text(encoding='utf-8'))
manifest=project/'data/baselines/feeder_v1/manifest.json'
for v in json.loads(manifest.read_text())['files']:assert hashlib.sha256((project/v['path']).read_bytes()).hexdigest()==v['sha256']
assert hashlib.sha256(source.read_bytes()).hexdigest()==profile['association_sha256']
out=root/'results/feeder_physics_v1_4';out.mkdir(exist_ok=True)
stations={g['id']:g for g in data['ground_stations']};ground={};normal={}
for key,g in stations.items():
 ground[key]=wgs84.latlon(g['latitude'],g['longitude'],elevation_m=g['altitude_m']).itrs_xyz.m
 lat,lon=np.radians([g['latitude'],g['longitude']]);normal[key]=[np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)]
noise=K*398*1e8;threshold=noise*10**(-12.2/10);rows=[];gso=[];ngso=[];start=time.perf_counter();repeats=3
for frame_index,frame in enumerate(data['frames']):
 links=frame['links'];protected=frame['protected_links'];n=len(links);allreceivers=links+protected
 pos={p['entity_id']:np.array(p['ecef_m']) for p in frame['positions']}
 for mode in ['antenna_index','all_cochannel']:
  channels=np.array([r['antenna_index'] if mode=='antenna_index' else 0 for r in links]);f=17.85e9+1e8*channels
  args=dict(sources=[pos[r['satellite_id']] for r in links],targets=[ground[r['gateway_id']] for r in links],receivers=[ground[r['gateway_id']] for r in allreceivers],boresights=[pos[r['satellite_id']] for r in allreceivers],normals=[normal[r['gateway_id']] for r in allreceivers],frequencies=f,channels=channels,receiver_channels=list(channels)+[-1]*len(protected),diameters=[C/18.2e9*10**((45.76-7.7)/20)]*n+[stations[r['gateway_id']]['research_metadata']['simulation_antenna_diameter_m'] for r in protected],half_width=profile['tx_half_width_deg'],desired_source_indices=list(range(n))+[-1]*len(protected))
  # Warm-up, then alternate timed exact / screened runs; all screening overhead included.
  exact=compute(**args);ref=channel_sums(exact['power_w'],channels)
  oldpath=root/f'results/feeder_physics_v1_3_tx_frequency/frame_{frame_index:03d}_{mode}.npz'
  with np.load(oldpath) as z:previous=z['received_power_w'].copy()
  np.fill_diagonal(previous,0);previous*=np.equal.outer(channels,channels)
  np.testing.assert_allclose(exact['power_w'][:n],previous,rtol=1e-10,atol=0)
  # Independent scalar budget for every GSO/source pair of the first snapshot.
  if frame_index==0:
   scalar=np.zeros((len(protected),n))
   for i,r in enumerate(protected):
    g=ground[r['gateway_id']];b=pos[r['satellite_id']];diam=args['diameters'][n+i]
    for j,l in enumerate(links):
     sat=pos[l['satellite_id']];delta=sat-g
     if np.dot(delta,normal[r['gateway_id']])<=0:continue
     gt=tx_pattern_at_frequency(angle(ground[l['gateway_id']]-sat,g-sat),float(f[j]),18.2e9,35,args['half_width'])
     gr=s1428(angle(b-g,delta),diam*f[j]/C)
     scalar[i,j]=10**((12+gt+gr)/10)*(C/f[j]/(4*np.pi*np.linalg.norm(delta)))**2
   np.testing.assert_allclose(exact['power_w'][n:],scalar,rtol=1e-10,atol=0)
  np.savez_compressed(out/f'reference_{frame_index:03d}_{mode}.npz',power_w=exact['power_w'],receiver_link_ids=np.array([r['link_id'] for r in allreceivers]),source_link_ids=np.array([r['link_id'] for r in links]),source_frequency_hz=f,source_channel=channels)
  for i,r in enumerate(protected):
   for c in range(8):
    by={op:float(np.sum(exact['power_w'][n+i,(channels==c)&np.array([l['constellation_id']==op for l in links])])) for op in ['starlink','oneweb']}
    gso.append(dict(frame=frame_index,timestamp=frame['timestamp'],mode=mode,receiver=r['link_id'],channel=c,diameter_m=args['diameters'][n+i],starlink_w=by['starlink'],oneweb_w=by['oneweb'],total_w=float(ref[n+i,c]),in_linear=float(ref[n+i,c]/noise)))
    assert np.isclose(sum(by.values()),ref[n+i,c],rtol=1e-12,atol=0)
  for i,r in enumerate(links):ngso.append(dict(frame=frame_index,mode=mode,link_id=r['link_id'],channel=int(channels[i]),power_w=float(ref[i,channels[i]]),in_linear=float(ref[i,channels[i]]/noise)))
  for epsilon in [1e-4,1e-3,1e-2]:
   timings=[];fasttimings=[]
   for repeat in range(repeats):
    if repeat%2==0:
     e=compute(**args);fast=compute(**args,omission_budget_w=epsilon*noise)
    else:
     fast=compute(**args,omission_budget_w=epsilon*noise);e=compute(**args)
    timings.append(e['timings']['total_s']);fasttimings.append(fast['timings']['total_s'])
   lower=channel_sums(fast['power_w'],channels);upper=lower+fast['omitted_upper_w'];error=ref-lower
   assert np.all(error>=-1e-28) and np.all(ref<=upper+1e-26)
   assert np.max(fast['omitted_upper_w'])<=epsilon*noise*(1+1e-12)
   # NGSO threshold interval: uncertain samples must fall back, never declared safe.
   own=(np.arange(n),channels);lo=lower[own];hi=upper[own];true=ref[own]>threshold
   uncertain=(lo<=threshold)&(hi>threshold)
   decision=lo>threshold;decision[uncertain]=true[uncertain]  # simulate exact row fallback
   fallback_start=time.perf_counter()
   for i in np.where(uncertain)[0]:
    subset={**args,'receivers':[args['receivers'][i]],'boresights':[args['boresights'][i]],'normals':[args['normals'][i]],'receiver_channels':[args['receiver_channels'][i]],'diameters':[args['diameters'][i]],'desired_source_indices':[i]}
    fallback=compute(**subset)
    decision[i]=np.sum(fallback['power_w'])>threshold
   fallback_s=time.perf_counter()-fallback_start
   assert np.array_equal(decision,true)
   row=dict(frame=frame_index,mode=mode,epsilon_noise=epsilon,eligible_pairs=exact['eligible_pairs'],evaluated_pairs=fast['evaluated_pairs'],omitted_pairs=exact['eligible_pairs']-fast['evaluated_pairs'],max_error_over_noise=float(np.max(error)/noise),max_bound_over_noise=float(np.max(fast['omitted_upper_w'])/noise),uncertain_ngso=int(sum(uncertain)),raw_false_negative_ngso=int(sum(true&~(lo>threshold))),post_fallback_mismatches=int(sum(decision!=true)),reference_median_s=float(np.median(timings)),screened_median_s=float(np.median(fasttimings)),fallback_s=fallback_s)
   for k,v in e['timings'].items():row['reference_'+k]=v
   rows.append(row)
 if frame_index%10==0:print('frame',frame_index,flush=True)
for name,values in [('benchmark.csv',rows),('gso_channel_power.csv',gso),('ngso_reference.csv',ngso)]:
 with (out/name).open('w',newline='',encoding='utf-8-sig') as handle:
  writer=csv.DictWriter(handle,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
summary=dict(version='v1.4_reference_and_bounded_screening',frames=61,gso_receivers=12,repeats=repeats,elapsed_s=time.perf_counter()-start,python=platform.python_version(),platform=platform.platform(),processor=platform.processor(),numpy=np.__version__,association_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),profile_sha256=hashlib.sha256(profile_file.read_bytes()).hexdigest(),gso_spectral_status='UNVERIFIED_DIAGNOSTIC_BINNING_ONLY; GSO receiver bandwidth, spectral overlap and protection metric pending; per-bin sums and 100MHz I/N are not validated protection calculations',gso_policy='3.5m preserved per metadata; S1428 gain overrides inconsistent metadata fixed gain/efficiency; 398K and 100MHz diagnostic noise; per-channel I/N has no regulatory threshold; no EPFD/compliance implemented',algorithm='RX/FSPL * TX peak upper bound; sort and omit cumulative upper<=epsilon*kTB per receiver/channel; exact TX for kept pairs; NGSO ambiguous threshold rows fallback exact',results=[])
for mode in ['antenna_index','all_cochannel']:
 for epsilon in [1e-4,1e-3,1e-2]:
  rr=[r for r in rows if r['mode']==mode and r['epsilon_noise']==epsilon]
  summary['results'].append(dict(mode=mode,epsilon_noise=epsilon,omitted_fraction=sum(r['omitted_pairs'] for r in rr)/sum(r['eligible_pairs'] for r in rr),max_error_over_noise=max(r['max_error_over_noise'] for r in rr),raw_false_negative_ngso=sum(r['raw_false_negative_ngso'] for r in rr),uncertain_ngso=sum(r['uncertain_ngso'] for r in rr),post_fallback_mismatches=sum(r['post_fallback_mismatches'] for r in rr),measured_kernel_speedup=sum(r['reference_median_s'] for r in rr)/sum(r['screened_median_s']+r['fallback_s'] for r in rr)))
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))
