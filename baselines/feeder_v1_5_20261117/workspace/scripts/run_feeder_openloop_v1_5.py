"""Derived exact open-loop reference. Never writes frozen inputs or snapshots.

python scripts/run_feeder_openloop_v1_5.py --frames 3 --out results/feeder_openloop_v1_5_pilot
python scripts/run_feeder_openloop_v1_5.py --frames 720 --out results/feeder_openloop_v1_5
"""
import argparse
import csv
import gzip
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'em-situational-system-main/em-situational-system-main'
sys.path.insert(0, str(PROJECT / 'backend'))
from app.services.feeder_association import select_links
from app.services.feeder_interference import C, K, matrix, aggregate, s1428, tx_pattern_at_frequency
from app.services.feeder_gso_epfd import epfd_windows
from app.services.feeder_fast_interference import angles
from app.services.orbit import load_satellites_from_tle_text
from skyfield.api import EarthSatellite, load, wgs84
from skyfield.constants import AU_KM
from skyfield.framelib import itrs
from skyfield.positionlib import Geocentric
from skyfield.sgp4lib import TEME
from sgp4.api import SatrecArray


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(',', ':')), encoding='utf-8')


def db(values):
    a = np.asarray(values)
    return np.where(a > 0, 10 * np.log10(np.maximum(a, np.finfo(float).tiny)), np.nan)


def finite_list(values):
    return np.where(np.isfinite(values), values, None).tolist()


def rx_gain(theta, q):
    """Array evaluation of unchanged S.1428-1 scalar branches."""
    theta, q = np.broadcast_arrays(theta, q)
    peak = 20*np.log10(q)+np.where(q <= 100, 7.7, 8.4)
    g1 = np.where(q <= 100, 29-25*np.log10(95/q), -1+15*np.log10(q))
    m = 20/q*np.sqrt(peak-g1)
    r = np.where(q <= 100, 95/q, 15.85*q**(-.6))
    safe = np.maximum(theta, 1e-100)
    low = np.select([theta <= 33.1, theta <= 80, q <= 25, theta <= 120],
                    [29-25*np.log10(safe), -9., -5., -4.], -9.)
    high = np.select([theta < 10, theta < 34.1, theta < 80, theta < 120],
                     [29-25*np.log10(safe), 34-30*np.log10(safe), -12., -7.], -12.)
    return np.select([theta < m, theta < r], [peak-.0025*(q*theta)**2, g1], np.where(q <= 100, low, high))


def tx_gain(theta, f, width):
    ratio = f/18.2e9
    peak = 35+20*np.log10(ratio)
    h = width/ratio
    y = 6.32*h*10**(.04*(peak-20))
    return np.select([theta <= 2.58*h, theta <= 6.32*h, theta <= y, theta <= 90],
                     [peak-3*(theta/h)**1.5, peak-20,
                      peak-20-25*np.log10(np.maximum(theta, 1e-100)/(6.32*h)), 0.],
                     np.maximum(-5+.25*peak, 0))


def exact_ngso(links, satellites, ground, normal, channels, width, diameter):
    """All N*N geometries and budgets, no screening, no temporal reuse."""
    n = len(links)
    source = np.array([satellites[x['satellite_id']] for x in links])
    target = np.array([ground[x['gateway_id']] for x in links])
    norms = np.array([normal[x['gateway_id']] for x in links])
    delta = source[None, :, :]-target[:, None, :]
    distance = np.linalg.norm(delta, axis=-1)
    tx = angles(target[None, :, :]-source[None, :, :], -delta)
    rx = angles(source[:, None, :]-target[:, None, :], delta)
    f = 17.85e9+1e8*channels
    power = 10**((12+tx_gain(tx, f[None, :], width)+rx_gain(rx, diameter*f[None, :]/C))/10)*(C/f[None, :]/(4*np.pi*distance))**2
    power[np.sum(delta*norms[:, None, :], axis=-1) <= 0] = 0
    return power


class Scene:
    def __init__(self):
        self.path = PROJECT/'data/scenarios/three_constellations.json'
        self.raw = json.loads(self.path.read_text(encoding='utf-8-sig'))
        self.ts = load.timescale(builtin=True)
        self.epoch = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)
        self.stations = self.raw['ground_stations']
        self.ng = [g for g in self.stations if g['constellation_id'] != 'gso']
        self.gs = [g for g in self.stations if g['constellation_id'] == 'gso']
        self.ground, self.normal = {}, {}
        for g in self.stations:
            self.ground[g['id']] = wgs84.latlon(g['latitude'], g['longitude'], elevation_m=g['altitude_m']).itrs_xyz.m
            lat, lon = np.radians([g['latitude'], g['longitude']])
            self.normal[g['id']] = np.array([np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)])
        self.objects, self.ids, self.ops = [], [], []
        self.sources = []
        for group in self.raw['constellation']['groups']:
            path = (self.path.parent/group['source']).resolve()
            if group['format'] == 'tle':
                models = load_satellites_from_tle_text(path.read_text(encoding='utf-8-sig'))
                objs = [EarthSatellite(x.tle_line1, x.tle_line2, x.name, self.ts) for x in models]
                ids = [x.id for x in models]
            else:
                records = json.loads(path.read_text(encoding='utf-8-sig'))
                objs = [EarthSatellite.from_omm(self.ts, x) for x in records]
                ids = [str(x['NORAD_CAT_ID']) for x in records]
            self.objects.extend(objs)
            self.ids.extend([group['id']+':'+x for x in ids])
            self.ops.extend([group['id']]*len(objs))
            self.sources.append(dict(system=group['id'], path=str(path.relative_to(ROOT)), sha256=sha(path), records=len(objs)))
        self.ids = np.array(self.ids); self.ops = np.array(self.ops)
        assert len(set(self.ids)) == len(self.ids)
        self.array = SatrecArray([o.model for o in self.objects])
        self.index = {x: i for i, x in enumerate(self.ids)}
        self.epochs = np.array([float(o.epoch.tt) for o in self.objects])

    def propagate(self, when):
        t = self.ts.from_datetime(when)
        # SGP4 requires UTC Julian date, including leap seconds conversion from Skyfield.
        from skyfield.constants import DAY_S
        fraction = t.tai_fraction-t._leap_seconds()/DAY_S
        errors, r, v = self.array.sgp4(np.array([float(t.whole)]), np.array([float(fraction)]))
        teme = r[:, 0, :].T
        inertial = TEME.rotation_at(t).T @ teme
        ecef = (itrs.rotation_at(t) @ inertial).T*1000
        geo = wgs84.subpoint(Geocentric(inertial/AU_KM, t=t))
        altitude = geo.elevation.km
        eligible = (errors[:, 0] == 0) & np.all(np.isfinite(ecef), axis=1)
        eligible &= ((self.ops != 'starlink') | ((altitude >= 300) & (altitude <= 650)))
        eligible &= ((self.ops != 'oneweb') | ((altitude >= 1100) & (altitude <= 1300)))
        return ecef, eligible, dict(input_count=len(self.ids), eligible_count=int(eligible.sum()),
            propagation_errors=int(np.sum(errors != 0)), excluded_ids=self.ids[~eligible].tolist(),
            epoch_age_days_min=float(np.min(t.tt-self.epochs)), epoch_age_days_max=float(np.max(t.tt-self.epochs)))

    def associate(self, ecef, eligible):
        candidates = {}
        for g in self.ng:
            js = np.where(eligible & (self.ops == g['constellation_id']))[0]
            delta = ecef[js]-self.ground[g['id']]
            distance = np.linalg.norm(delta, axis=1)
            elevation = np.degrees(np.arcsin(np.clip(delta@self.normal[g['id']]/distance, -1, 1)))
            candidates[g['id']] = [dict(satellite_id=str(self.ids[j]), gateway_id=g['id'], constellation_id=g['constellation_id'], elevation_deg=float(e), range_km=float(d/1000)) for j, e, d in zip(js, elevation, distance) if e >= 40]
        selected = select_links(candidates)
        links = [dict(r, link_id=f"feeder:{r['satellite_id']}:{g}", antenna_index=i) for g, rows in selected.items() for i, r in enumerate(rows)]
        protected = []
        for g in self.gs:
            meta = g['research_metadata']; sid = meta['pointing_satellite_id']
            assert eligible[self.index[sid]]
            delta = ecef[self.index[sid]]-self.ground[g['id']]
            el = np.degrees(np.arcsin(delta@self.normal[g['id']]/np.linalg.norm(delta)))
            protected.append(dict(link_id=meta['protected_link_id'], satellite_id=sid, gateway_id=g['id'], elevation_deg=float(el), geometry_visible=bool(el >= meta['simulation_minimum_elevation_deg'])))
        assert len(protected) == 12 and all(x['geometry_visible'] for x in protected)
        return links, protected, {g: len(rows) for g, rows in candidates.items()}


def assign(links, frame, seed):
    channels = np.zeros(len(links), dtype=int)
    for gateway in sorted({r['gateway_id'] for r in links}):
        indices = [i for i, r in enumerate(links) if r['gateway_id'] == gateway]
        entropy = int.from_bytes(hashlib.sha256(f'{seed}/{frame}/{gateway}'.encode()).digest()[:16], 'big')
        channels[indices] = np.random.Generator(np.random.PCG64(entropy)).permutation(8)[:len(indices)]
        assert len(set(channels[indices])) == len(indices) <= 8
    return channels


def stats(values):
    return dict(total=float(np.sum(values)), mean=float(np.mean(values)), median=float(np.median(values)), p95=float(np.percentile(values, 95)), maximum=float(np.max(values)))


def run(frames, output):
    out = ROOT/output
    out.mkdir(parents=True, exist_ok=False)
    scene = Scene()
    profile_path = ROOT/'results/feeder_antenna_sensitivity_v1_2/selected_profile.json'
    width = json.loads(profile_path.read_text())['tx_half_width_deg']
    diameter = C/18.2e9*10**((45.76-7.7)/20)
    windows = [dict(id=f'{kind}_{i}_{int(bw)}', kind=kind, center_hz=f, bandwidth_hz=bw) for kind, fs in [('carrier_center', [17.85e9+1e8*c for c in range(8)]), ('channel_boundary', [17.9e9+1e8*c for c in range(7)])] for i, f in enumerate(fs) for bw in [4e4, 1e6]]
    seed = 20261115
    config = dict(version='v1.5_openloop_exact', frames=frames, step_seconds=10, start_utc=scene.epoch.isoformat(), endpoint_included=False,
        assignment='user confirmed 2026-11-17: within-gateway without replacement; across-gateway reuse; PCG64 SHA256(seed/frame/gateway) first 128 bits big endian', seed=seed,
        selection='same operator; gateway ID ascending rounds; elevation descending then satellite ID; >=40deg; <=8 per gateway; <=1 per satellite',
        model=dict(tx_dbw=12, bandwidth_hz=1e8, noise_k=398, threshold_db=-12.2, tx_half_width_deg=width, rx_diameter_m=diameter, diameters_m=[1,2,5], windows=windows),
        source_scope='all existing catalogue orbit candidates; only selected active feeders radiate; existing instantaneous altitude filter retained',
        scenario_sha256=sha(scene.path), profile_sha256=sha(profile_path), implementation_sha256=sha(__file__), sources=scene.sources,
        timing='perf_counter; no warmup, first frame included; all pair geometry inside interference wall interval; I/O separate; single sequential process; NumPy array evaluation of unchanged scalar branches; no pair screening/approximation/reuse',
        platform=platform.platform(), python=sys.version, dependencies={p: importlib.metadata.version(p) for p in ['numpy','skyfield','sgp4']},
        thread_environment={k: os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},
        limits='sampled research only; not continuous-time protection or regulatory compliance; 30 sampled windows, not full frequency search',
        storage='gzip JSON inputs per frame, all used positions and actual assignments; aggregate results per frame; full matrices reconstructible, first frame matrix retained')
    dump(out/'config.json', config)
    dump(out/'stations.json', scene.stations)
    orbit_audit = []
    for op in np.unique(scene.ops):
        js = np.where(scene.ops == op)[0]
        age = scene.ts.from_datetime(scene.epoch).tt-scene.epochs[js]
        orbit_audit.append(dict(system=op, count=len(js), epoch_offset_start_days_min=float(age.min()), epoch_offset_start_days_max=float(age.max()), absolute_age_gt7_days=int(np.sum(np.abs(age)>7))))
    audit = dict(total_station_records=len(scene.stations), by_system=dict(Counter(g['constellation_id'] for g in scene.stations)),
        by_position_accuracy=dict(Counter(g['research_metadata'].get('position_accuracy','unspecified') for g in scene.stations)),
        by_import_source=dict(Counter(g['research_metadata'].get('import_source_file','unspecified') for g in scene.stations)),
        orbit=orbit_audit, sources=scene.sources, station_policy='use exactly 218 Starlink, 13 OneWeb, 12 GSO records; preserve unverified/community/simulation metadata; no claim of active operational stations')
    dump(out/'audit.json', audit)
    rows=[]; replay=[]; validation={}
    windows_file = gzip.open(out/'window_epfd.csv.gz','wt',encoding='utf-8',newline='')
    writer=csv.writer(windows_file)
    writer.writerow(['frame','receiver','diameter_m','window_id','starlink_w_m2','oneweb_w_m2','combined_w_m2'])
    try:
        for frame in range(frames):
            t0=perf_counter(); when=scene.epoch+timedelta(seconds=10*frame)
            a=perf_counter(); ecef, eligible, orbit=scene.propagate(when); propagation_s=perf_counter()-a
            a=perf_counter(); links, protected, candidates=scene.associate(ecef,eligible); association_s=perf_counter()-a
            a=perf_counter(); channels=assign(links,frame,seed); random_s=perf_counter()-a
            n=len(links); assert n and len({x['satellite_id'] for x in links})==n
            used=sorted({r['satellite_id'] for r in links+protected})
            pos={s:ecef[scene.index[s]].tolist() for s in used}
            a=perf_counter()
            with gzip.open(out/f'input_{frame:03d}.json.gz','wt',encoding='utf-8') as f:
                json.dump(dict(frame=frame,timestamp=when.isoformat(),links=links,protected_links=protected,channels=channels.tolist(),positions_ecef_m=pos,candidates=candidates,orbit_audit=orbit),f,ensure_ascii=False,allow_nan=False,separators=(',',':'))
            input_io_s=perf_counter()-a
            # Start before any source/receiver arrays or pair geometry preparation.
            wall=perf_counter(); a=perf_counter()
            sat={s:np.asarray(p) for s,p in pos.items()}
            args=dict(sources=[sat[r['satellite_id']] for r in links], targets=[scene.ground[r['gateway_id']] for r in links], receivers=[scene.ground[r['gateway_id']] for r in protected], boresights=[sat[r['satellite_id']] for r in protected], normals=[scene.normal[r['gateway_id']] for r in protected],carrier_centers_hz=17.85e9+1e8*channels,carrier_bandwidths_hz=1e8,tx_powers_w=10**1.2,windows=windows,diameters_m=[1.,2.,5.],tx_half_width_deg=width)
            shared_s=perf_counter()-a; a=perf_counter()
            power=exact_ngso(links,sat,scene.ground,scene.normal,channels,width,diameter)
            ngso_s=perf_counter()-a; a=perf_counter()
            gs=epfd_windows(**args)
            gso_s=perf_counter()-a; a=perf_counter()
            # All entries, including noncochannel pairs, have received full budgets.
            same=channels[:,None]==channels[None,:]; np.fill_diagonal(same,False)
            p=power*same
            gateway=np.array([r['gateway_id'] for r in links]); operators=np.array([r['constellation_id'] for r in links])
            sameg=gateway[:,None]==gateway[None,:]; sameop=operators[:,None]==operators[None,:]
            category=np.stack([(p*sameg).sum(axis=1),(p*(~sameg & sameop)).sum(axis=1),(p*(~sameop)).sum(axis=1)])
            total=p.sum(axis=1); ratio=total/(K*398*1e8); failed=ratio>10**(-12.2/10)
            ep=gs['epfd_w_m2_by_source']; combined=ep.sum(axis=-1)
            systems=np.stack([ep[:,:,:,operators==op].sum(axis=-1) for op in ['starlink','oneweb']]+[combined],axis=-1)
            np.testing.assert_allclose(category.sum(axis=0),total,rtol=1e-12,atol=0)
            np.testing.assert_allclose(systems[:,:,:,0]+systems[:,:,:,1],combined,rtol=1e-12,atol=0)
            assert np.all(np.isfinite(power)) and np.all(power>=0) and np.all(np.isfinite(ep)) and np.all(ep>=0)
            peaks=[]; peakids=[]
            for b in [4e4,1e6]:
                js=[i for i,w in enumerate(windows) if w['bandwidth_hz']==b]
                values=systems[:,:,js,:]
                peaks.append(finite_list(db(values.max(axis=2))))
                peakids.append(np.array(js)[values.argmax(axis=2)].tolist())
            aggregation_s=perf_counter()-a; interference_s=perf_counter()-wall
            a=perf_counter()
            if frame==0:
                # Independent old scalar reference, all sources, 3 representative victims.
                indices=sorted(set([0,n//2,n-1]))
                reference=matrix(links,sat,scene.ground,scene.normal,17.85e9+1e8*channels,width,diameter,tx_reference_frequency_hz=18.2e9) if n<150 else None
                if reference is not None:
                    np.testing.assert_allclose(power,reference['received_power_w'],rtol=1e-10,atol=0)
                else:
                    from app.services.feeder_interference import angle
                    for i in indices:
                        for j,l in enumerate(links):
                            g=scene.ground[links[i]['gateway_id']]; own=sat[links[i]['satellite_id']]; source=sat[l['satellite_id']]; target=scene.ground[l['gateway_id']]; delta=source-g; f=17.85e9+1e8*channels[j]
                            scalar=0 if delta@scene.normal[links[i]['gateway_id']]<=0 else 10**((12+tx_pattern_at_frequency(angle(target-source,g-source),f,18.2e9,35,width)+s1428(angle(own-g,delta),diameter*f/C))/10)*(C/f/(4*np.pi*np.linalg.norm(delta)))**2
                            np.testing.assert_allclose(power[i,j],scalar,rtol=1e-10,atol=0)
                # Batched TEME transform checked against existing Skyfield object propagation.
                for j in [0,len(scene.ids)//2,len(scene.ids)-1]:
                    expected=scene.objects[j].at(scene.ts.from_datetime(when)).frame_xyz(itrs).m
                    np.testing.assert_allclose(ecef[j],expected,rtol=1e-11,atol=1e-4)
                np.savez_compressed(out/'first_frame_matrices.npz',ngso_power_w=power,**gs)
                validation=dict(scalar_ngso_rows=indices,scalar_full_matrix=reference is not None,skyfield_propagation_samples=3,status='passed',rtol=1e-10)
                dump(out/'validation.json',validation)
            validation_s=perf_counter()-a; a=perf_counter()
            result=dict(frame=frame,timestamp=when.isoformat(),active=n,failed=int(failed.sum()),lf=float(failed.mean()),failed_link_ids=[r['link_id'] for r,flag in zip(links,failed) if flag],in_db=finite_list(db(ratio)),category_power_w=category.tolist(),
                operators={op:dict(active=int((operators==op).sum()),failed=int(failed[operators==op].sum()),category_power_w=category[:,operators==op].sum(axis=1).tolist()) for op in ['starlink','oneweb']},
                epfd_peaks_db=peaks,peak_window_indices=peakids)
            dump(out/f'result_{frame:03d}.json',result)
            for d,diam in enumerate([1,2,5]):
                for i,r in enumerate(protected):
                    for w,window in enumerate(windows):writer.writerow([frame,r['link_id'],diam,window['id'],*systems[d,i,w].tolist()])
            windows_file.flush()
            result_io_s=perf_counter()-a
            row=dict(frame=frame,timestamp=when.isoformat(),candidate_satellites=orbit['eligible_count'],visible_candidate_pairs=sum(candidates.values()),active_gateways=len(set(gateway)),active_links=n,ngso_budget_pairs=n*n,ngso_interference_pairs=n*(n-1),cochannel_pairs=int(same.sum()),visible_cochannel_pairs=int(np.count_nonzero(p)),gso_geometry_pairs=12*n,gso_window_source_slots=12*n*30*3,gso_contributing_window_source_slots=int(np.count_nonzero(ep)),gso_receiver_windows=12*30*3,failed_links=int(failed.sum()),lf=float(failed.mean()),propagation_s=propagation_s,association_s=association_s,random_s=random_s,input_io_s=input_io_s,shared_s=shared_s,ngso_s=ngso_s,gso_s=gso_s,aggregation_s=aggregation_s,interference_s=interference_s,validation_s=validation_s,result_io_s=result_io_s,snapshot_s=perf_counter()-t0)
            rows.append(row)
            replay.append(dict(frame=frame,timestamp=when.isoformat(),active=n,failed=int(failed.sum()),lf=float(failed.mean()),interference_s=interference_s,ngso_s=ngso_s,gso_s=gso_s,epfd_peaks_db=peaks,peak_window_indices=peakids))
            if frame%10==0 or frame==frames-1:print(json.dumps(dict(frame=frame,active=n,failed=int(failed.sum()),interference_s=round(interference_s,3),snapshot_s=round(row['snapshot_s'],3))),flush=True)
    finally:
        windows_file.close()
    with (out/'timings.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer2=csv.DictWriter(f,fieldnames=list(rows[0]));writer2.writeheader();writer2.writerows(rows)
    summary=dict(frames=len(rows),active_links_min=min(r['active_links'] for r in rows),active_links_max=max(r['active_links'] for r in rows),failed_link_samples=sum(r['failed_links'] for r in rows),active_link_samples=sum(r['active_links'] for r in rows),sample_weighted_lf=sum(r['failed_links'] for r in rows)/sum(r['active_links'] for r in rows),frame_mean_lf=float(np.mean([r['lf'] for r in rows])),timing_seconds={k:stats([r[k] for r in rows]) for k in rows[0] if k.endswith('_s')},note='LF counts sampled link observations; not continuous-time failure duration')
    dump(out/'summary.json',summary)
    dump(out/'replay.json',dict(config=config,receivers=[g['id'] for g in scene.gs],stations=scene.stations,windows=windows,frames=replay,timings=rows))
    dump(out/'manifest.json',dict(files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json']))
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--frames',type=int,default=720);parser.add_argument('--out',default='results/feeder_openloop_v1_5')
    args=parser.parse_args();assert 1<=args.frames<=720
    run(args.frames,args.out)
