"""Bounds checked against independent on-axis power and diverse angle cases."""
import math
import numpy as np
import pytest
from app.services.feeder_fast_interference import compute,channel_sums
from app.services.feeder_interference import C,s1428


def inputs():
    return dict(sources=[[1e6,0,0],[1e6,2e5,0],[-1e6,0,0]],targets=[[0,0,0]]*3,
                receivers=[[0,0,0]],boresights=[[4.2e7,0,0]],normals=[[1,0,0]],
                frequencies=[18.2e9]*3,channels=[0,0,1],receiver_channels=[-1],
                diameters=[3.5],half_width=1.4990500074657407)


def test_protected_receiver_onaxis_budget_and_horizon():
    result=compute(**inputs());p=result['power_w']
    expected=10**((12+35+s1428(0,3.5*18.2e9/C))/10)*(C/18.2e9/(4*math.pi*1e6))**2
    assert p[0,0]==pytest.approx(expected,rel=1e-12,abs=0)
    assert p[0,2]==0
    assert result['eligible_pairs']==2
    assert channel_sums(p,[0,0,1])[0,0]==pytest.approx(sum(p[0]),rel=1e-12,abs=0)


def test_accumulated_screening_bound_and_channel_isolation():
    args=inputs();reference=compute(**args);budget=1e-3*reference['power_w'].max()
    for value in [0,budget,1.]:
        fast=compute(**args,omission_budget_w=value)
        exact=channel_sums(reference['power_w'],args['channels']);lo=channel_sums(fast['power_w'],args['channels'])
        assert np.all(exact>=lo)
        assert np.all(exact<=lo+fast['omitted_upper_w']+1e-25)
        assert np.all(fast['omitted_upper_w']<=value*(1+1e-12))
    assert compute(**args,omission_budget_w=1.)['evaluated_pairs']==0
    only_one=compute(**{**args,'receiver_channels':[1]})
    assert only_one['eligible_pairs']==0
    with pytest.raises(ValueError):compute(**args,omission_budget_w=-1)


def test_desired_source_excluded_and_bounds_across_pattern_regions():
    args=inputs();args['desired_source_indices']=[0]
    result=compute(**args)
    assert result['power_w'][0,0]==0
    for theta in [0,1,3.86,3.87,8,30,90,120,179]:
        t=math.radians(theta)
        # rotate service target around source, preserving victim sight line
        args['targets'][1]=[1e6-1e6*math.cos(t),2e5-1e6*math.sin(t),0]
        exact=compute(**args);fast=compute(**args,omission_budget_w=1.)
        assert np.all(channel_sums(exact['power_w'],args['channels'])<=fast['omitted_upper_w']+1e-25)
