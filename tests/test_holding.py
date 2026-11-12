import numpy as np
import pytest

from qv_sim.holding import solve_period
from qv_sim.sharing import Flow


def flows(gateways=('a',),load=.6):
    return [Flow(g,n,load,m,w) for g in gateways for n,m,w in [('high',.5,4),('ordinary',.3,1)]]


def test_lookahead_avoids_disappearing_link():
    links=[{('a','short'):1.5,('a','lasting'):1.0}]+[{('a','lasting'):1.0}]*5
    caps=[{'short':1.5,'lasting':1.5}]*6
    result=solve_period(links,caps,flows())
    assert result['association']=={'a':'lasting'}
    assert result['high_deficit_gbit']<1e-5
    assert result['ordinary_deficit_gbit']<1e-5
    assert result['total_gbit']==pytest.approx(30,abs=1e-4)


def test_per_station_deficit_cannot_be_offset_by_surplus():
    links=[{('a','s'):1.5}]*6
    result=solve_period(links,[{'s':1.5}]*6,flows(('a','b')))
    assert result['high_deficit_gbit']==pytest.approx(15,abs=1e-5)
    assert result['ordinary_deficit_gbit']==pytest.approx(9,abs=1e-5)


def test_high_is_strictly_prioritized_and_capacity_observed():
    result=solve_period([{('a','s'):.6}]*6,[{'s':.6}]*6,flows())
    assert result['volumes'][0]>=15-1e-5
    assert result['volumes'][1]==pytest.approx(3,abs=1e-4)
    assert np.max(np.sum(result['rates'],axis=1))<=.6+1e-6


def test_future_only_satellite_not_eligible_and_free_relaxation():
    links=[{}]+[{('a','s'):1.5}]*5
    caps=[{'s':1.5}]*6
    held=solve_period(links,caps,flows())
    free=solve_period(links,caps,flows(),free_association=True)
    assert held['association']=={}
    assert held['high_deficit_gbit']==pytest.approx(15)
    assert free['high_deficit_gbit']<1e-5


def test_fixed_expired_association_remains_zero():
    result=solve_period([{('a','s'):1.5}]*6,[{'s':1.5}]*6,flows(),fixed={'a':'expired'})
    assert result['total_gbit']==pytest.approx(0)


def test_invalid_capacity_rejected():
    with pytest.raises(ValueError):
        solve_period([{('a','s'):-1}],[{'s':1.5}],flows())
