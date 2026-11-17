"""GSO V1.4.1: explicit spectral windows, per-source EPFD, no legal verdict."""
import sys,json,hashlib,csv,time
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1];project=root/'em-situational-system-main/em-situational-system-main'
sys.path.insert(0,str(project/'backend'))
from skyfield.api import wgs84
from app.services.feeder_gso_epfd import epfd_windows
from app.services.feeder_interference import C,s1428
source=root/'results/feeder_association_v1_1/associations.json';data=json.loads(source.read_text(encoding='utf-8'))
profile_path=root/'results/feeder_antenna_sensitivity_v1_2/selected_profile.json';profile=json.loads(profile_path.read_text(encoding='utf-8'))
manifest=project/'data/baselines/feeder_v1/manifest.json'
for item in json.loads(manifest.read_text())['files']:assert hashlib.sha256((project/item['path']).read_bytes()).hexdigest()==item['sha256']
assert hashlib.sha256(source.read_bytes()).hexdigest()==profile['association_sha256']
out=root/'results/feeder_gso_epfd_v1_4_1';out.mkdir(exist_ok=True)
centers=[17.85e9+1e8*c for c in range(8)];edges=[17.9e9+1e8*c for c in range(7)]
windows=[dict(id=f'{kind}_{i}_{int(bw)}',kind=kind,center_hz=f,bandwidth_hz=bw) for kind,values in [('carrier_center',centers),('channel_boundary',edges)] for i,f in enumerate(values) for bw in [4e4,1e6]]
diameters=[1.,2.,5.];grounds={};normals={}
for g in data['ground_stations']:
 grounds[g['id']]=wgs84.latlon(g['latitude'],g['longitude'],elevation_m=g['altitude_m']).itrs_xyz.m
 lat,lon=np.radians([g['latitude'],g['longitude']]);normals[g['id']]=[np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)]
rows=[];start=time.perf_counter();max_identity_error=0
for frame_index,frame in enumerate(data['frames']):
 links=frame['links'];protected=frame['protected_links'];position={p['entity_id']:p['ecef_m'] for p in frame['positions']}
 for mode in ['antenna_index','all_cochannel']:
  channels=np.array([r['antenna_index'] if mode=='antenna_index' else 0 for r in links]);frequencies=17.85e9+1e8*channels
  result=epfd_windows(sources=[position[r['satellite_id']] for r in links],targets=[grounds[r['gateway_id']] for r in links],receivers=[grounds[r['gateway_id']] for r in protected],boresights=[position[r['satellite_id']] for r in protected],normals=[normals[r['gateway_id']] for r in protected],carrier_centers_hz=frequencies,carrier_bandwidths_hz=[1e8]*len(links),tx_powers_w=[10**1.2]*len(links),windows=windows,diameters_m=diameters,tx_half_width_deg=profile['tx_half_width_deg'])
  epfd=result['epfd_w_m2_by_source'];received=result['received_w_by_source'];assert np.all(np.isfinite(epfd)) and np.all(epfd>=0)
  # Piecewise midpoint identity verifies flux-density vs received-power units.
  for d,diameter in enumerate(diameters):
   for w in range(len(windows)):
    valid=result['in_window_tx_power_w'][w]>0
    for j in np.where(valid)[0]:
     f=result['intersection_midpoint_hz'][w,j]
     area=10**(s1428(0,diameter*f/C)/10)*(C/f)**2/(4*np.pi)
     np.testing.assert_allclose(received[d,:,w,j],epfd[d,:,w,j]*area,rtol=1e-12,atol=0)
  np.savez_compressed(out/f'frame_{frame_index:03d}_{mode}.npz',**result,source_link_ids=np.array([r['link_id'] for r in links]),receiver_link_ids=np.array([r['link_id'] for r in protected]),source_operators=np.array([r['constellation_id'] for r in links]))
  for d,diameter in enumerate(diameters):
   for i,receiver in enumerate(protected):
    for w,window in enumerate(windows):
     system={op:float(np.sum(epfd[d,i,w,np.array([l['constellation_id']==op for l in links])])) for op in ['starlink','oneweb']}
     total=float(np.sum(epfd[d,i,w]));assert np.isclose(sum(system.values()),total,rtol=1e-12,atol=0)
     def db(v):return float(10*np.log10(v)) if v>0 else None
     rows.append(dict(frame=frame_index,timestamp=frame['timestamp'],mode=mode,receiver=receiver['link_id'],diameter_m=diameter,window_id=window['id'],window_kind=window['kind'],center_hz=window['center_hz'],reference_bandwidth_hz=window['bandwidth_hz'],starlink_w_m2=system['starlink'],oneweb_w_m2=system['oneweb'],combined_w_m2=total,starlink_dbw_m2=db(system['starlink']),oneweb_dbw_m2=db(system['oneweb']),combined_dbw_m2=db(total),received_reference_power_w=float(np.sum(received[d,i,w]))))
 if frame_index%10==0:print('frame',frame_index,flush=True)
with (out/'window_epfd.csv').open('w',newline='',encoding='utf-8-sig') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
config=dict(version='v1.4.1_gso_window_epfd',frames=len(data['frames']),reference_diameters_m=diameters,windows=windows,tx_power_dbw=12,carrier_bandwidth_hz=1e8,tx_pattern='S1528-0 1.2 z=1, peak 35dBi at18.2GHz; fixed effective aperture frequency scaling; LN -20',tx_half_width_ref_deg=profile['tx_half_width_deg'],rx_pattern='S1428-1 at spectral intersection midpoint',spectrum='flat rectangular PSD; ideal rectangular reference windows; gain/propagation narrow-window midpoint approximation; incoherent linear power sum',source_scope='only selected active feeder beams, not entire operational constellations',gso_association='12 fixed pairings; positions/coverage/band operation not fully verified',time_scope='600seconds inclusive 61 snapshots at10s; not converged long-term statistics',regulatory_status='RESEARCH_EPFD_ONLY; no compliance verdict or limit curves executed; center and boundary windows are samples, not full worst-frequency scan',zero_power='linear zero; CSV dB empty; no arbitrary finite floor',association_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),profile_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest(),source_hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),project/'backend/app/services/feeder_gso_epfd.py',project/'backend/app/services/feeder_interference.py']})
(out/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
summary=dict(rows=len(rows),frames=61,receivers=12,windows=len(windows),diameters=len(diameters),elapsed_including_validation_and_io_s=time.perf_counter()-start,peaks=[])
for mode in ['antenna_index','all_cochannel']:
 for diameter in diameters:
  for bw in [4e4,1e6]:
   candidates=[r for r in rows if r['mode']==mode and r['diameter_m']==diameter and r['reference_bandwidth_hz']==bw]
   r=max(candidates,key=lambda r:r['combined_w_m2'])
   summary['peaks'].append({k:r[k] for k in ['mode','diameter_m','reference_bandwidth_hz','frame','receiver','window_id','combined_dbw_m2']})
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))
