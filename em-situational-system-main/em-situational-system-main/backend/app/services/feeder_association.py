"""Research-only WGS84 geometry and deterministic same-operator associations."""
import math
import numpy as np
from skyfield.api import wgs84
from skyfield.framelib import itrs


def geometry(station, satellite_ecef):
    ground = wgs84.latlon(station.latitude, station.longitude, elevation_m=station.altitude_m).itrs_xyz.m
    delta = np.asarray(satellite_ecef) - ground
    lat, lon = np.radians([station.latitude, station.longitude])
    east = np.dot(delta, [-np.sin(lon), np.cos(lon), 0])
    north = np.dot(delta, [-np.sin(lat)*np.cos(lon), -np.sin(lat)*np.sin(lon), np.cos(lat)])
    up = np.dot(delta, [np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)])
    return dict(elevation_deg=math.degrees(math.atan2(up, math.hypot(east, north))),
                azimuth_deg=math.degrees(math.atan2(east, north)) % 360,
                range_km=float(np.linalg.norm(delta))/1000)


def select_links(candidates_by_gateway, capacity=8):
    """Fixed gateway ID order per round, highest elevation, unique satellites."""
    if capacity < 1:
        raise ValueError('capacity must be positive')
    ordered={g:sorted(rows,key=lambda r:(-r['elevation_deg'],r['satellite_id'])) for g,rows in candidates_by_gateway.items()}
    selected={g:[] for g in ordered};used=set()
    for _ in range(capacity):
        for g in sorted(ordered):
            row=next((r for r in ordered[g] if r['satellite_id'] not in used),None)
            if row is not None:
                selected[g].append(row);used.add(row['satellite_id'])
    return selected


def evaluate(manager, when):
    positions=[];audit=[];epoch_warnings=[]
    t=manager.orbit._timescale.from_datetime(when)
    for sat in manager.satellites:
        obj=manager.orbit._tle_satellites[sat.id]
        reason=None
        age=abs(float(t-obj.epoch))
        if age>7:epoch_warnings.append(dict(satellite_id=sat.id,absolute_epoch_offset_days=age))
        state=obj.at(t)
        if state.message:reason='sgp4_error: '+str(state.message)
        if reason is None:
            llh=wgs84.subpoint(state);ecef=state.frame_xyz(itrs).m
            alt=float(llh.elevation.m/1000)
            if not np.all(np.isfinite(ecef)) or not math.isfinite(alt):reason='nonfinite_position'
            elif sat.constellation_id=='starlink' and not 300<=alt<=650:reason='outside_study_altitude_300_650km'
            elif sat.constellation_id=='oneweb' and not 1100<=alt<=1300:reason='outside_study_altitude_1100_1300km'
        if reason:audit.append(dict(satellite_id=sat.id,reason=reason));continue
        positions.append(dict(entity_id=sat.id,name=sat.name,constellation_id=sat.constellation_id,latitude=float(llh.latitude.degrees),longitude=float(llh.longitude.degrees),altitude_m=alt*1000,ecef_m=ecef.tolist()))
    stations=[g for g in manager.scenario.ground_stations if g.constellation_id!='gso']
    candidates={g.id:[] for g in stations}
    for g in stations:
        for p in positions:
            if p['constellation_id']!=g.constellation_id:continue
            geo=geometry(g,p['ecef_m'])
            if geo['elevation_deg']>=40:candidates[g.id].append(dict(satellite_id=p['entity_id'],gateway_id=g.id,constellation_id=g.constellation_id,**geo))
    selected=select_links(candidates)
    links=[dict(r,link_id=f"feeder:{r['satellite_id']}:{g}",antenna_index=i,frequency_assigned=False) for g,rows in selected.items() for i,r in enumerate(rows)]
    lookup={p['entity_id']:p for p in positions}
    protected=[]
    for g in manager.scenario.ground_stations:
        if g.constellation_id!='gso':continue
        meta=g.research_metadata;p=lookup[meta['pointing_satellite_id']];geo=geometry(g,p['ecef_m'])
        protected.append(dict(link_id=meta['protected_link_id'],satellite_id=p['entity_id'],gateway_id=g.id,geometry_visible=geo['elevation_deg']>=meta['simulation_minimum_elevation_deg'],**geo))
    used={r['satellite_id'] for r in links+protected}
    return dict(timestamp=when.isoformat(),stage='geometry_and_association_only',links=links,protected_links=protected,
                positions=[p for p in positions if p['entity_id'] in used],
                station_summary=[dict(gateway_id=g.id,constellation_id=g.constellation_id,visible_candidates=len(candidates[g.id]),active_count=len(selected[g.id]),capacity=8) for g in stations],
                orbit_audit=dict(input_count=len(manager.satellites),eligible_count=len(positions),excluded=audit,epoch_warnings=epoch_warnings))
