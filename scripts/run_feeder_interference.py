"""One-slot derived physics run; never writes frozen inputs or UI exports."""
import sys,json,hashlib,math
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
project=root/'em-situational-system-main/em-situational-system-main'
sys.path.insert(0,str(project/'backend'))
from skyfield.api import wgs84
from app.services.feeder_interference import C,matrix,aggregate
source=root/'results/feeder_association_v1_1/associations.json'
data=json.loads(source.read_text(encoding='utf-8')); frame=data['frames'][0]
manifest=project/'data/baselines/feeder_v1/manifest.json'
for f in json.loads(manifest.read_text())['files']:
    assert hashlib.sha256((project/f['path']).read_bytes()).hexdigest()==f['sha256']
grounds={}; normals={}
for g in data['ground_stations']:
    grounds[g['id']]=wgs84.latlon(g['latitude'],g['longitude'],elevation_m=g['altitude_m']).itrs_xyz.m
    lat,lon=np.radians([g['latitude'],g['longitude']]); normals[g['id']]=[math.cos(lat)*math.cos(lon),math.cos(lat)*math.sin(lon),math.sin(lat)]
frequency=18.2e9
config=dict(version='feeder_physics_v1_2',frequency_hz=frequency,tx_half_width_deg=1.0,tx_sidelobe_db=-20,tx_peak_dbi=35,tx_power_dbw=12,rx_diameter_m=C/frequency*10**((45.76-7.7)/20),assumptions=['TX half-width 1 degree and sidelobe -20 dB are explicit sensitivity baseline, not measured equipment or paper-verified parameters','S1528-0 1.2 circular model based on user-confirmed audit report; original PDF retrieval not required','RX diameter inferred from S1428 peak 45.76 dBi at nominal center frequency','FSPL only; co-polar; tangent-horizon visibility; nominal center frequency approximation','all-cochannel stress case and antenna-index channel diagnostic are not allocation algorithms'],source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),timestamp=frame['timestamp'])
links=frame['links']; satellites={p['entity_id']:p['ecef_m'] for p in frame['positions']}
result=matrix(links,satellites,grounds,normals,frequency,config['tx_half_width_deg'],config['rx_diameter_m'])
out=root/'results/feeder_physics_v1_2';out.mkdir(exist_ok=True)
np.savez_compressed(out/'single_slot_matrix.npz',**result,link_ids=np.array([r['link_id'] for r in links]))
summary=dict(config=config,active_links=len(links),matrix_orientation='row victim i, column source j; diagonal desired signal, excluded from aggregation',desired_power_w=np.diag(result['received_power_w']).tolist(),all_cochannel=aggregate(result['received_power_w'],links,[0]*len(links)),antenna_index_diagnostic=aggregate(result['received_power_w'],links,[r['antenna_index'] for r in links]))
(out/'single_slot_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(active_links=len(links),all_cochannel_lf=summary['all_cochannel']['lf_rate'],diagnostic_lf=summary['antenna_index_diagnostic']['lf_rate'],rx_diameter_m=config['rx_diameter_m']),indent=2))
