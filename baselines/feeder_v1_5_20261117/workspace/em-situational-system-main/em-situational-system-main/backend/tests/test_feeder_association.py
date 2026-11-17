from types import SimpleNamespace
import numpy as np
from skyfield.api import wgs84
from app.services.feeder_association import geometry, select_links


def test_wgs84_overhead_and_horizon():
    site=SimpleNamespace(latitude=0,longitude=0,altitude_m=0)
    earth=wgs84.latlon(0,0).itrs_xyz.m
    assert abs(geometry(site,earth+np.array([550000,0,0]))['elevation_deg']-90)<1e-9
    assert abs(geometry(site,earth+np.array([0,100000,0]))['elevation_deg'])<1e-9


def test_round_robin_does_not_let_first_gateway_take_all_satellites():
    def r(s,e):return dict(satellite_id=s,elevation_deg=e)
    result=select_links({'B':[r('s1',85),r('s2',80)],'A':[r('s1',90),r('s2',89)]},2)
    assert [x['satellite_id'] for x in result['A']]==['s1']
    assert [x['satellite_id'] for x in result['B']]==['s2']


def test_elevation_ties_are_stable_and_empty_sites_allowed():
    assert select_links({'A':[dict(satellite_id='b',elevation_deg=50),dict(satellite_id='a',elevation_deg=50)],'B':[]},1)=={'A':[dict(satellite_id='a',elevation_deg=50)],'B':[]}
