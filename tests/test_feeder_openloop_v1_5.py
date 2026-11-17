"""Independent checks for the new exact array evaluation and random policy."""
import importlib.util
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('openloop',ROOT/'scripts/run_feeder_openloop_v1_5.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_array_pattern_branches_against_scalar():
    theta=np.unique(np.r_[np.linspace(0,180,1001),10,33.1,34.1,80,90,120])
    for q in [20,25,25.001,79,100,100.001,300]:
        peak=20*np.log10(q)+(7.7 if q<=100 else 8.4)
        g1=29-25*np.log10(95/q) if q<=100 else -1+15*np.log10(q)
        boundaries=[20/q*np.sqrt(peak-g1),95/q if q<=100 else 15.85*q**(-.6)]
        a=np.r_[theta,boundaries,np.nextafter(boundaries,0),np.nextafter(boundaries,180)]
        np.testing.assert_allclose(m.rx_gain(a,q),[m.s1428(float(x),q) for x in a],atol=1e-12,rtol=1e-12)
    width=1.499050
    for f in [17.85e9,18.2e9,18.55e9]:
        h=width/(f/18.2e9);peak=35+20*np.log10(f/18.2e9)
        boundaries=np.array([2.58*h,6.32*h,6.32*h*10**(.04*(peak-20))])
        a=np.r_[theta,boundaries,np.nextafter(boundaries,0),np.nextafter(boundaries,180)]
        np.testing.assert_allclose(m.tx_gain(a,f,width),[m.tx_pattern_at_frequency(float(x),f,18.2e9,35,width) for x in a],atol=1e-12,rtol=1e-12)


def test_exact_matrices_against_existing_scalar_baseline():
    data=json.loads((ROOT/'results/feeder_association_v1_1/associations.json').read_text(encoding='utf-8'))
    profile=json.loads((ROOT/'results/feeder_antenna_sensitivity_v1_2/selected_profile.json').read_text())
    ground={};normal={}
    for g in data['ground_stations']:
        ground[g['id']]=m.wgs84.latlon(g['latitude'],g['longitude'],elevation_m=g['altitude_m']).itrs_xyz.m
        lat,lon=np.radians([g['latitude'],g['longitude']]);normal[g['id']]=[np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)]
    diameter=m.C/18.2e9*10**((45.76-7.7)/20)
    for index in [0,30,60]:
        frame=data['frames'][index];links=frame['links'];pos={p['entity_id']:p['ecef_m'] for p in frame['positions']}
        channels=m.assign(links,index,20261115)
        actual=m.exact_ngso(links,pos,ground,normal,channels,profile['tx_half_width_deg'],diameter)
        expected=m.matrix(links,pos,ground,normal,17.85e9+1e8*channels,profile['tx_half_width_deg'],diameter,tx_reference_frequency_hz=18.2e9)['received_power_w']
        np.testing.assert_allclose(actual,expected,rtol=1e-10,atol=0)


def test_random_stream_is_gateway_local_and_without_replacement():
    links=[dict(gateway_id=g,link_id=f'{g}:{i}') for g in ['A','B'] for i in range(8)]
    a=m.assign(links,10,20261115)
    np.testing.assert_array_equal(a,m.assign(links,10,20261115))
    np.testing.assert_array_equal(a[:8],m.assign(links[:8],10,20261115))
    assert set(a[:8])==set(a[8:])==set(range(8))
    assert not np.array_equal(a,m.assign(links,11,20261115))


def test_existing_gso_protected_pairings_preserved():
    scene=m.Scene()
    old=json.loads((m.PROJECT/'data/scenarios/feeder_baseline_v1.json').read_text(encoding='utf-8-sig'))
    assert scene.gs==[g for g in old['ground_stations'] if g['constellation_id']=='gso']
