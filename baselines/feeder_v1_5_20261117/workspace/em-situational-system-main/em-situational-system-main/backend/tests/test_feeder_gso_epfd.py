import math
import numpy as np
import pytest
from app.services.feeder_gso_epfd import overlap_hz,epfd_windows
from app.services.feeder_interference import C,s1428


def test_spectral_overlap_and_edges():
    width,mid=overlap_hz([100,200,300],[100]*3,150,40)
    np.testing.assert_array_equal(width,[20,20,0])
    assert sum(width)==40
    np.testing.assert_array_equal(overlap_hz([100],[100],100,40)[0],[40])
    np.testing.assert_array_equal(overlap_hz([100],[100],200,100)[0],[0])
    with pytest.raises(ValueError):overlap_hz([100],[0],100,1)


def scene():
    return dict(sources=[[1e6,0,0]],targets=[[0,0,0]],receivers=[[0,0,0]],boresights=[[4.2e7,0,0]],normals=[[1,0,0]],carrier_centers_hz=[18.2e9],carrier_bandwidths_hz=[1e8],tx_powers_w=[10**1.2],diameters_m=[1],tx_half_width_deg=1.4990500074657407)


def test_hand_epfd_budget_and_received_power_conversion():
    args=scene();args['windows']=[dict(center_hz=18.2e9,bandwidth_hz=4e4),dict(center_hz=18.2e9,bandwidth_hz=1e6)]
    r=epfd_windows(**args);e=r['epfd_w_m2_by_source'][0,0,:,0]
    expected=10**1.2*(4e4/1e8)*10**3.5/(4*math.pi*1e12)
    assert e[0]==pytest.approx(expected,rel=1e-12,abs=0)
    assert e[1]/e[0]==pytest.approx(25)
    gr=10**(s1428(0,18.2e9/C)/10)
    assert r['received_w_by_source'][0,0,0,0]==pytest.approx(expected*gr*(C/18.2e9)**2/(4*math.pi),rel=1e-12,abs=0)


def test_multisource_half_overlap_and_horizon():
    a=scene();a.update(sources=[[1e6,0,0]]*2+[[-1e6,0,0]],targets=[[0,0,0]]*3,carrier_centers_hz=[18.15e9,18.25e9,18.15e9],carrier_bandwidths_hz=[1e8]*3,tx_powers_w=[10**1.2]*3,windows=[dict(center_hz=18.2e9,bandwidth_hz=1e6)])
    r=epfd_windows(**a)
    np.testing.assert_allclose(r['in_window_tx_power_w'][0],[10**1.2*.005]*3,rtol=1e-12,atol=0)
    assert r['epfd_w_m2_by_source'][0,0,0,2]==0
    # fixed TX aperture: on-axis gain scales f^2, so two half-windows average f^2.
    f=r['intersection_midpoint_hz'][0,:2]
    hand=sum(10**1.2*.005*10**3.5*(v/18.2e9)**2/(4*math.pi*1e12) for v in f)
    assert r['epfd_w_m2_by_source'][0,0,0].sum()==pytest.approx(hand,rel=1e-12,abs=0)


def test_no_overlap_zero_power_and_offaxis_dish_normalization():
    a=scene();a['windows']=[dict(center_hz=18.5e9,bandwidth_hz=1e6)]
    assert not epfd_windows(**a)['epfd_w_m2_by_source'].any()
    a['windows']=[dict(center_hz=18.2e9,bandwidth_hz=1e6)];a['tx_powers_w']=[0]
    assert not epfd_windows(**a)['epfd_w_m2_by_source'].any()
    a['tx_powers_w']=[10**1.2];a['boresights']=[[4.2e7,4.2e7,0]]
    r=epfd_windows(**a)
    norm=10**((s1428(45,18.2e9/C)-s1428(0,18.2e9/C))/10)
    hand=10**1.2*.01*10**3.5/(4*math.pi*1e12)*norm
    assert r['epfd_w_m2_by_source'][0,0,0,0]==pytest.approx(hand,rel=1e-12,abs=0)
