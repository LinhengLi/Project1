"""Temporal measurement and association regression tests."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('temporal', Path(__file__).parents[1]/'scripts/experiment_temporal.py')
temporal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(temporal)


def test_baseline_elevation_and_remaining_capacity():
    links = {('a','s1'):1.5, ('a','s2'):1.5, ('b','s1'):1.5, ('b','s2'):1.5}
    elevations = {e: (60 if e[1]=='s1' else 30) for e in links}
    assert temporal.baseline(links,elevations,['a','b']) == {'a':'s1','b':'s1'}
    assert temporal.baseline(links,elevations,['a','b'],True) == {'a':'s1','b':'s2'}


def test_complete_rolling_windows_and_under_run():
    rows = [{'gateway':'a','high':r,'ordinary':.3,'switch':0,'invalid_link':int(r==0)}
            for r in [0,0,.6,.6,.6,.6,.6,.6]]
    result = temporal.metrics(rows,['a'],30)
    assert result['complete_station_windows'] == 3
    assert result['longest_under_seconds'] == 10
    assert result['high_attainment'] == 2/3
    assert result['invalid_under_station_seconds'] == 10


def test_expired_fixed_link_zero_service():
    flows = [temporal.Flow('a','high',.6,.5,4),temporal.Flow('a','ordinary',.6,.3,1)]
    result = temporal.solve({('a','new'):1.5},{'new':1.5},flows,'qos',fixed={'a':'expired'})
    assert result['rates'] == [0,0]
