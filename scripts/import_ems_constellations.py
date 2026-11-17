"""Copy local orbit snapshots into the EMS system and create a reproducible scene."""
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
project = root / 'em-situational-system-main/em-situational-system-main'
target = project / 'data/orbits'
target.mkdir(parents=True, exist_ok=True)
groups = []
for name, filename, fmt in [('starlink', 'starlink.tle', 'tle'), ('oneweb', 'oneweb.json', 'omm'), ('gso', 'geo.json', 'omm')]:
    if name == 'gso' and (root / 'realdatas/geo_research_candidates.json').exists():
        filename = 'geo_research_candidates.json'
    shutil.copy2(root / 'realdatas' / filename, target / filename)
    groups.append(dict(id=name, source='../orbits/' + filename, format=fmt))
stations = []
for system, filename in [('starlink', 'Starlink_Gen1_constellation.json'), ('oneweb', 'OneWeb_research_gateways.json' if (root / 'realdatas/OneWeb_research_gateways.json').exists() else 'OneWeb_constellation.json'), ('gso', 'GSO_reference_receivers.json' if (root / 'realdatas/GSO_reference_receivers.json').exists() else 'GSO_constellation.json')]:
    source = json.loads((root / 'realdatas' / filename).read_text(encoding='utf-8-sig'))
    for row in source['gateway_sites']:
        lat, lon = row['latitude_deg'], row['longitude_deg']
        assert -90 <= lat <= 90 and -180 <= lon <= 180
        stations.append(dict(id=row['id'], name=row['name'], latitude=lat, longitude=lon, altitude_m=row.get('altitude_m_assumed', 0), constellation_id=system, research_metadata=dict(row, import_source_file=filename)))
assert len({s['id'] for s in stations}) == len(stations)
scene = dict(scenario_id='three_constellations', name='异构星座 · Starlink / OneWeb / GSO', epoch='2026-11-13T12:00:00Z', time_step_sec=60, simulation_duration_sec=86400, orbit_only=True, constellation=dict(type='mixed_local', groups=groups), ground_stations=stations, default_links={}, jammers=[])
(project / 'data/scenarios/three_constellations.json').write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding='utf-8')
print('Imported local orbit snapshots into', target)
print('Gateway stations:', len(stations))
