"""Create baseline v1 once; subsequent invocations verify, never overwrite it."""
import hashlib, json, math, shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
project=root/'em-situational-system-main/em-situational-system-main'
data=project/'data'
bundle=data/'baselines/feeder_v1'
scene_path=data/'scenarios/feeder_baseline_v1.json'
manifest_path=bundle/'manifest.json'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    for entry in manifest['files']:
        p=project/entry['path'];assert digest(p)==entry['sha256'],p
    print('Frozen baseline v1: all hashes verified')
if manifest_path.exists():
    verify();raise SystemExit(0)
if bundle.exists() or scene_path.exists():raise SystemExit('Partial baseline exists; inspect before creating a new version')
scene=json.loads((data/'scenarios/three_constellations.json').read_text(encoding='utf-8'))
ow=sorted([g for g in scene['ground_stations'] if g['constellation_id']=='oneweb' and g['research_metadata']['position_verified']],key=lambda x:x['id'])
assert len(ow)==6
sl=[g for g in scene['ground_stations'] if g['constellation_id']=='starlink']
def distance(a,b):
    la,lb=map(math.radians,[a['latitude'],b['latitude']]);dl=math.radians(b['longitude']-a['longitude'])
    return 6371*2*math.asin(min(1,math.sqrt(math.sin((lb-la)/2)**2+math.cos(la)*math.cos(lb)*math.sin(dl/2)**2)))
pairs=[];chosen=[]
for station in ow:
    candidates=[s for s in sl if s['id'] not in {c['id'] for c in chosen}]
    neighbor=min(candidates,key=lambda s:(distance(station,s),s['id']))
    chosen.append(neighbor);pairs.append(dict(oneweb_id=station['id'],starlink_id=neighbor['id'],distance_km=round(distance(station,neighbor),3),selection='nearest_unique_catalogue_site; source confidence retained'))
gso=[g for g in scene['ground_stations'] if g['constellation_id']=='gso']
assert len(gso)==len({g['research_metadata']['pointing_norad'] for g in gso})==12
bundle.mkdir(parents=True)
files=[]
for group in scene['constellation']['groups']:
    src=(data/'scenarios'/group['source']).resolve();dst=bundle/src.name;shutil.copy2(src,dst);files.append(dst)
    group['source']='../baselines/feeder_v1/'+dst.name
for name in ['GSO_17p8_18p6_screening.json','GSO_reference_receivers.json']:
    dst=bundle/name;shutil.copy2(root/'realdatas'/name,dst);files.append(dst)
config=dict(version='feeder_v1',frozen_date='2026-11-15',purpose='Heterogeneous downlink feeder interference management and AI dynamic-computation acceleration',stage='configuration_only',seed=20261115,epoch_utc='2026-11-13T12:00:00Z',time_step_sec=10,duration_sec=7200,study_band_ghz=[17.8,18.6],channel_count=8,channel_bandwidth_mhz=100,channel_centers_ghz=[17.85+i*.1 for i in range(8)],frequency_overlap_policy='interval_intersection; per-GSO frequency masks from screening snapshot',ngso_working_antennas_per_gateway=8,ngso_tx_power_dbw=12,ngso_tx_power_convention='fixed total power per active 100MHz carrier; no power scaling for subsequent bandwidth variants without an explicit policy',ngso_satellite_peak_gain_dbi=35,ngso_gateway_peak_gain_dbi=45.76,ngso_noise_temperature_k=398,ngso_min_elevation_deg=40,ngso_reference_lf_threshold_db=-12.2,lf_threshold_status='paper-derived experimental criterion; not a universal regulatory threshold',association_policy='same_operator; highest_elevation_then_satellite_id; at_most_one_gateway_per_satellite; up_to_8_links_per_gateway; allow_idle_antennas',gso_association_policy='12 fixed one-to-one reference associations; no handover',coordination_assumption='ideal centralized cross-operator frequency coordination; not evidence of real operator coordination',antenna_patterns=dict(ngso_tx='ITU-R S.1528 reference family; exact revision/formula must be pinned before RF execution',ngso_rx='ITU-R S.1428-1 reference; formula pending',gso_rx='reference pattern and applicable regulatory antenna class pending'),parameter_provenance='12dBW/35dBi/45.76dBi/398K/40deg/-12.2dB are controlled paper-reference assumptions, not operator measurements',gso_parameters='per-station assumptions in frozen metadata; 3.5m/0.65 efficiency/398K/10deg',orbit_policy='frozen raw catalogue candidates; operational/altitude filtering is deferred and must create a derived version with a selection manifest',station_pairs=pairs,counts=dict(starlink_gateways=6,oneweb_gateways=6,gso_receivers=12),readiness=dict(active_feeder_links=False,antenna_patterns=False,aggregate_interference=False,graph_coloring=False,lf_fsr=False,gso_epfd_compliance=False,ai_acceleration=False),metrics=['NGSO LF overall and by constellation','FSR on continuing associations','end-to-end and stage runtime','GSO protection metric after definition'],excluded_scope=['user traffic','QoS scheduling','routing'],change_policy='No overwrite of v1; changes require v2 or a named derived experiment')
for g in chosen+ow:
    g['visible_elevation_deg']=40;g['antenna_gain_dbi']=45.76
    g['research_metadata']['baseline_working_antennas']=8
    g['research_metadata']['baseline_rf_parameters_are_assumed']=True
scene.update(scenario_id='feeder_baseline_v1',name='冻结基线 v1 · 异构下行馈电干扰管理',epoch=config['epoch_utc'],time_step_sec=10,simulation_duration_sec=7200,ground_stations=chosen+ow+gso,orbit_only=True,default_links=dict(sgl_center_freq_hz=18.2e9,sgl_bandwidth_hz=100e6,sgl_tx_power_dbm=42))
scene.setdefault('external_sources',{})['research_baseline']=config
scene_path.write_text(json.dumps(scene,ensure_ascii=False,indent=2),encoding='utf-8');files.append(scene_path)
config_path=bundle/'research_config.json';config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8');files.append(config_path)
manifest=dict(baseline_id='feeder_v1',files=[dict(path=p.relative_to(project).as_posix(),sha256=digest(p),size_bytes=p.stat().st_size) for p in files])
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
public=project/'frontend/static/feeder_baseline_v1.json'
public.write_text(json.dumps(dict(config=config,manifest=manifest),ensure_ascii=False,indent=2),encoding='utf-8')
verify();print('Pairs:',pairs)
