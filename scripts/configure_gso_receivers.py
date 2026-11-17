"""Create explicitly simulated GSO protected receiving points, not claimed teleports."""
import json, math, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'em-situational-system-main/em-situational-system-main/backend'))
from app.services.scenario_manager import SimulationManager
manager=SimulationManager();manager.load_scenario('three_constellations.json')
method='https://www.itu.int/epfdsupport/questions/'
sites=[]
for filename in ['Starlink_Gen1_constellation.json','OneWeb_constellation.json']:
    for row in json.loads((root/'realdatas'/filename).read_text(encoding='utf-8-sig'))['gateway_sites']:
        if not row['position_verified']:continue
        # Assumed pointing only. Visibility is validated independently below.
        sat=40882 if row['id'] in ['OW-FCC-001','OW-FCC-003','OW-FCC-004'] else 49332
        model=next(s for s in manager.satellites if s.omm and int(s.omm['NORAD_CAT_ID'])==sat)
        pos=manager.orbit.propagate(model.id,manager.current_time)
        elevation=manager.orbit._elevation_deg(pos['latitude'],pos['longitude'],pos['altitude_m'],row['latitude_deg'],row['longitude_deg'],0)
        assert elevation>=10,(row['id'],elevation)
        diameter=3.5;efficiency=.65;freq=18.2e9
        gain=10*math.log10(efficiency*(math.pi*diameter*freq/299792458)**2)
        sites.append(dict(id='GSO-REF-'+row['id'],name='GSO参考接收站 · '+row['name'],latitude_deg=row['latitude_deg'],longitude_deg=row['longitude_deg'],altitude_m_assumed=0,position_verified=False,research_band_verified=False,active_now_confirmed=False,simulation_reference=True,role='protected_gso_receiver',coordinate_basis='Simulation point co-located with an FCC-sourced NGSO gateway; no actual GSO facility asserted',anchor_station_id=row['id'],anchor_source=row['source'],pointing_satellite_id=model.id,pointing_satellite_name=model.name,pointing_norad=sat,epoch_elevation_deg=round(elevation,3),downlink_research_band_mhz=[17800,18600],simulation_antenna_diameter_m=diameter,simulation_aperture_efficiency=efficiency,simulation_peak_gain_dbi=round(gain,3),simulation_noise_temperature_k=398,simulation_center_frequency_ghz=18.2,simulation_minimum_elevation_deg=10,antenna_pattern_status='Not implemented; select applicable reference pattern before EPFD calculation',beam_coverage_status='Not verified at individual spot-beam level',epfd_limits_status='Not configured; no compliance claim',interference_calculation_enabled=False,source=dict(title='ITU EPFD methodology (not a source for these hypothetical locations)',url=method)))
from datetime import timedelta
anchors = []
for filename in ['Starlink_Gen1_constellation.json','OneWeb_constellation.json']:
    anchors.extend(json.loads((root/'realdatas'/filename).read_text(encoding='utf-8-sig'))['gateway_sites'])
# Keep one initial reference for each satellite, then add exactly one for each
# remaining satellite. Each receiver has a distinct geographic location.
sites = list({x['pointing_norad']: x for x in reversed(sites)}.values())
covered = {x['pointing_norad'] for x in sites}
used_coordinates = {(x['latitude_deg'], x['longitude_deg']) for x in sites}
for model in [s for s in manager.satellites if s.constellation_id == 'gso']:
    norad = int(model.omm['NORAD_CAT_ID'])
    if norad in covered: continue
    pos = manager.orbit.propagate(model.id, manager.current_time)
    def elevation_at(row):
        return manager.orbit._elevation_deg(pos['latitude'], pos['longitude'], pos['altitude_m'], row['latitude_deg'], row['longitude_deg'], 0)
    # Geographic anchor only: maximize elevation among available terrestrial sites.
    # This is not proof that the selected satellite beam covers that site.
    anchor = max((r for r in anchors if (r['latitude_deg'], r['longitude_deg']) not in used_coordinates), key=elevation_at)
    used_coordinates.add((anchor['latitude_deg'], anchor['longitude_deg']))
    assert elevation_at(anchor) >= 10
    station = dict(sites[0])
    station.update(id=f'GSO-REF-{norad}', name=f'GSO参考接收站 · {model.name} / {anchor["name"]}', latitude_deg=anchor['latitude_deg'], longitude_deg=anchor['longitude_deg'], anchor_station_id=anchor['id'], anchor_source=anchor['source'], pointing_satellite_id=model.id, pointing_satellite_name=model.name, pointing_norad=norad, epoch_elevation_deg=round(elevation_at(anchor),3), coordinate_basis='Synthetic GSO receiver at an existing NGSO catalogue anchor; maximum initial elevation, beam coverage not confirmed', anchor_position_verified=anchor['position_verified'])
    sites.append(station)
for station in sites:
    station['association_policy'] = 'fixed_satellite_no_handover'
    station['protected_link_id'] = f'protected:{station["pointing_norad"]}:{station["id"]}'
    elevations=[]
    for hour in range(25):
        pos=manager.orbit.propagate(station['pointing_satellite_id'],manager.current_time+timedelta(hours=hour))
        elevations.append(manager.orbit._elevation_deg(pos['latitude'],pos['longitude'],pos['altitude_m'],station['latitude_deg'],station['longitude_deg'],0))
    station['minimum_sampled_elevation_24h_deg']=round(min(elevations),3)
    assert min(elevations)>=10,station['id']
assert {x['pointing_norad'] for x in sites} == {int(s.omm['NORAD_CAT_ID']) for s in manager.satellites if s.constellation_id=='gso'}
assert len(sites) == len(used_coordinates) == 12
result=dict(configuration_date='2026-11-15',configuration_type='simulation_reference_receivers',gateway_sites=sites,station_count=len(sites),satellites_covered=12,association_model='one_satellite_one_receiver_one_fixed_link',notes='Exactly 12 satellites, 12 geographically distinct synthetic receivers and 12 fixed associations. Geometry checked hourly for 24h; no beam/channel availability or compliance claim. All antenna parameters are experimental assumptions.')
(root/'realdatas/GSO_reference_receivers.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print([(x['id'],x['pointing_satellite_name'],x['epoch_elevation_deg']) for x in sites])
