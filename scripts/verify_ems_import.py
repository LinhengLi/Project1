"""Exercise mixed TLE/OMM import and all satellite positions without a browser."""
import sys
import math
from pathlib import Path
from collections import Counter
from time import perf_counter

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'em-situational-system-main/em-situational-system-main/backend'))
from app.services.scenario_manager import SimulationManager

manager = SimulationManager()
manager.load_scenario('three_constellations.json')
counts = Counter(s.constellation_id for s in manager.satellites)
stations = manager.scenario.ground_stations
assert Counter(s.constellation_id for s in stations) == {'starlink': 218, 'oneweb': 13, 'gso': 12}
assert sum(s.research_metadata['position_verified'] for s in stations) == 10
assert len(manager.orbit.ground_stations) == 243
oneweb_stations = [s for s in stations if s.constellation_id == 'oneweb']
assert sum(s.research_metadata['position_verified'] for s in oneweb_stations) == 6
assert sum(s.research_metadata.get('simulation_location', False) for s in oneweb_stations) == 7
gso_stations = [s for s in stations if s.constellation_id == 'gso']
assert len({s.research_metadata['pointing_norad'] for s in gso_stations}) == 12
assert len(gso_stations) == 12
assert len({(s.latitude, s.longitude) for s in gso_stations}) == 12
assert len({s.research_metadata['protected_link_id'] for s in gso_stations}) == 12
assert all(s.research_metadata['minimum_sampled_elevation_24h_deg'] >= 10 for s in gso_stations)
assert counts == {'starlink': 10611, 'oneweb': 651, 'gso': 12}, counts
started = perf_counter()
positions = manager.get_satellite_positions()
assert len(positions) == 11274
for pos in positions:
    assert all(math.isfinite(pos[k]) for k in ('latitude', 'longitude', 'altitude_m')), pos
    assert -90 <= pos['latitude'] <= 90
    assert -180 <= pos['longitude'] <= 180
assert manager.get_snapshot().links == []
before = positions[0]['ecef_m']
manager.step(60)
after = manager.orbit.propagate(manager.satellites[0].id, manager.current_time)['ecef_m']
assert before != after
print(dict(counts), 'all positions finite; time step verified;', round(perf_counter()-started, 2), 'seconds')
