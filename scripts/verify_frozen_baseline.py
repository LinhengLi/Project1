"""Check the frozen contract without enabling unfinished RF computations."""
import hashlib,json,sys,math
from pathlib import Path
from collections import Counter
root=Path(__file__).resolve().parents[1]
project=root/'em-situational-system-main/em-situational-system-main'
sys.path.insert(0,str(project/'backend'))
from app.services.scenario_manager import SimulationManager
manifest=json.loads((project/'data/baselines/feeder_v1/manifest.json').read_text(encoding='utf-8'))
for f in manifest['files']:assert hashlib.sha256((project/f['path']).read_bytes()).hexdigest()==f['sha256']
m=SimulationManager();m.load_scenario('feeder_baseline_v1.json');s=m.scenario;c=s.external_sources['research_baseline']
assert Counter(g.constellation_id for g in s.ground_stations)=={'starlink':6,'oneweb':6,'gso':12}
assert s.time_step_sec==10 and s.simulation_duration_sec==7200 and s.orbit_only
assert s.default_links['sgl_tx_power_dbm']==c['ngso_tx_power_dbw']+30
assert c['channel_count']*c['channel_bandwidth_mhz']==800
assert all(abs(f-(17.85+i*.1))<1e-10 for i,f in enumerate(c['channel_centers_ghz']))
assert all(g.visible_elevation_deg==40 and g.antenna_gain_dbi==45.76 for g in s.ground_stations if g.constellation_id!='gso')
assert len({g.research_metadata['pointing_norad'] for g in s.ground_stations if g.constellation_id=='gso'})==12
assert m.get_snapshot().links==[]
assert len(m.get_satellite_positions())==11274
print('PASS: snapshot hashes, 6+6+12 stations, parameters, power units, GSO associations and position loading')
