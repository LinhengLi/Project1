"""Export the first 10 minutes of associations from the frozen v1 inputs."""
import sys,json,hashlib,shutil
from pathlib import Path
from datetime import timedelta
from collections import Counter
root=Path(__file__).resolve().parents[1]
project=root/'em-situational-system-main/em-situational-system-main'
sys.path.insert(0,str(project/'backend'))
from app.services.scenario_manager import SimulationManager
from app.services.feeder_association import evaluate
manifest=project/'data/baselines/feeder_v1/manifest.json'
for f in json.loads(manifest.read_text())['files']:
    assert hashlib.sha256((project/f['path']).read_bytes()).hexdigest()==f['sha256']
m=SimulationManager();m.load_scenario('feeder_baseline_v1.json')
frames=[]
for seconds in range(0,601,10):
    frame=evaluate(m,m.current_time+timedelta(seconds=seconds))
    links=frame['links'];assert len({r['satellite_id'] for r in links})==len(links)
    assert all(r['elevation_deg']>=40 for r in links)
    assert all(x['active_count']<=8 for x in frame['station_summary'])
    assert len(frame['protected_links'])==12
    assert all(x['geometry_visible'] for x in frame['protected_links'])
    frames.append(frame)
    if seconds%100==0:print('t=',seconds,'active links=',len(links),flush=True)
out=root/'results/feeder_association_v1_1';out.mkdir(parents=True,exist_ok=True)
payload=dict(version='feeder_association_v1_1',duration_seconds=600,step_seconds=10,
    policy='same operator; gateway ID ascending each round; highest elevation then satellite ID; unique satellites; capacity 8',
    orbit_filter='study geometry eligibility only, not operational status; Starlink 300-650km, OneWeb1100-1300km at each sampled epoch; exclude propagation errors; epoch offset >7days warns',
    station_geometry='WGS84 ellipsoid station ECEF + Skyfield ITRS satellite ECEF',
    frozen_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
    parameters_sha256=hashlib.sha256((root/'研究进展/feeder_v1_paper_aligned_parameters.json').read_bytes()).hexdigest(),
    ground_stations=[g.model_dump(mode='json') for g in m.scenario.ground_stations],frames=frames)
path=out/'associations.json';path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2(root/'研究进展/feeder_v1_paper_aligned_parameters.json',out/'parameters_snapshot.json')
shutil.copy2(path,project/'frontend/static/feeder_associations_v1_1.json')
summary=dict(frames=len(frames),ngso_active_min=min(len(f['links']) for f in frames),ngso_active_max=max(len(f['links']) for f in frames),initial_by_operator=dict(Counter(r['constellation_id'] for r in frames[0]['links'])),initial_exclusions=dict(Counter(r['reason'] for r in frames[0]['orbit_audit']['excluded'])),gso_links=12,all_sampled_gso_visible=True,interference_computed=False)
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(summary)
