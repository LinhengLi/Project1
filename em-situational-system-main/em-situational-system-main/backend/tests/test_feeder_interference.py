import math
import numpy as np
import pytest
from app.services.feeder_interference import angle,s1428,s1528,matrix,aggregate,C


def test_patterns_and_domains():
    assert s1528(0,35,1)==35
    assert s1528(1,35,1)==32
    assert s1528(4,35,1)==15
    for q,back in [(20,-5),(25,-5),(40,-9),(100,-9),(150,-12)]:
        assert s1428(0,q)==pytest.approx(20*math.log10(q)+(7.7 if q<=100 else 8.4))
        assert s1428(180,q)==back
        assert all(math.isfinite(s1428(t,q)) for t in [0,.1,1,10,33.1,34.1,80,120,180])
    with pytest.raises(ValueError):s1428(0,19)
    assert angle([1,0,0],[0,1,0])==90


def test_hand_budget_angles_and_linear_sum():
    links=[dict(satellite_id=str(i),gateway_id='g',constellation_id='a') for i in range(3)]
    sats={'0':[1000000,0,0],'1':[1000000,1000000,0],'2':[1000000,-1000000,0]}
    result=matrix(links,sats,{'g':[0,0,0]},{'g':[1,0,0]},20e9,1,1)
    p=result['received_power_w']
    expected=10**((12+35+20*math.log10(1/(C/20e9))+7.7)/10)*(C/20e9/(4*math.pi*1e6))**2
    assert p[0,0]==pytest.approx(expected)
    assert result['tx_offaxis_deg'][0,1]==0
    assert result['rx_offaxis_deg'][0,1]==pytest.approx(45)
    off=10**((12+35-9)/10)*(C/20e9/(4*math.pi*math.sqrt(2)*1e6))**2
    assert p[0,1]==pytest.approx(off)
    a=aggregate(p,links,[0,0,0]); assert a['aggregate_power_w'][0]==pytest.approx(2*off)
    assert 10*math.log10(2*off)-10*math.log10(off)==pytest.approx(3.01029995664)
    assert aggregate(p,links,[0,1,2])['aggregate_power_w']==[0,0,0]
    sats['2']=[-1000000,0,0]
    assert matrix(links,sats,{'g':[0,0,0]},{'g':[1,0,0]},20e9,1,1)['received_power_w'][0,2]==0


def test_s1528_piecewise_boundaries_and_selected_profile():
    width=1.4990500074657407
    for side in [-15,-20,-25,-30]:
        a,b=2.58*width,6.32*width
        y=b*10**(.04*(35+side))
        assert s1528(a,35,width,side)==pytest.approx(35-3*2.58**1.5)
        assert s1528(a+1e-8,35,width,side)==35+side
        assert s1528(b,35,width,side)==35+side
        assert s1528(b+1e-8,35,width,side)==pytest.approx(35+side,abs=1e-6)
        assert s1528(y,35,width,side)==pytest.approx(0,abs=1e-10)
        assert s1528(y+1e-8,35,width,side)==0
        assert s1528(90,35,width,side)==0
        assert s1528(90+1e-8,35,width,side)==max(15+side+35/4,0)
    q=math.sqrt(10**3.5/(.6*math.pi**2))
    assert math.sqrt(1200)/q==pytest.approx(width)


def test_nonzero_tx_angle_hand_budget():
    links=[dict(satellite_id='a',gateway_id='a',constellation_id='x'),dict(satellite_id='b',gateway_id='b',constellation_id='x')]
    # Source b is overhead victim a, but its own target is 1 degree sideways.
    grounds={'a':[0,0,0],'b':[0,1e6*math.tan(math.radians(1)),0]}
    r=matrix(links,{'a':[1e6,0,0],'b':[1e6,0,0]},grounds,{'a':[1,0,0],'b':[1,0,0]},20e9,1,1)
    assert r['tx_offaxis_deg'][0,1]==pytest.approx(1)
    assert r['rx_offaxis_deg'][0,1]==0
    expected=10**((12+32+20*math.log10(20e9/C)+7.7)/10)*(C/20e9/(4*math.pi*1e6))**2
    assert r['received_power_w'][0,1]==pytest.approx(expected)


def test_category_sum_and_strict_threshold():
    links=[dict(satellite_id=str(i),gateway_id=g,constellation_id=o) for i,(g,o) in enumerate([('a','x'),('a','x'),('b','x'),('c','y')])]
    p=np.zeros((4,4));p[0]=[999,2,3,5]
    a=aggregate(p,links,[0]*4,bandwidth_hz=1,temperature_k=1)
    assert a['category_power_w']['intra_gateway'][0]==2
    assert a['category_power_w']['same_operator_inter_gateway'][0]==3
    assert a['category_power_w']['cross_operator'][0]==5
    assert a['aggregate_power_w'][0]==10
    assert aggregate(p,links,[0,1,1,1])['aggregate_power_w'][0]==0


def test_source_frequency_vector_matches_scalar_columns():
    links=[dict(satellite_id=str(i),gateway_id='g',constellation_id='x') for i in range(2)]
    args=(links,{'0':[1e6,0,0],'1':[1e6,1e5,0]},{'g':[0,0,0]},{'g':[1,0,0]})
    vector=matrix(*args,[17.85e9,18.55e9],1,1)['received_power_w']
    for j,f in enumerate([17.85e9,18.55e9]):
        scalar=matrix(*args,f,1,1)['received_power_w']
        np.testing.assert_allclose(vector[:,j],scalar[:,j],rtol=1e-12,atol=0)


def test_frequency_correction_equals_direct_budget_and_strict_lf():
    from app.services.feeder_interference import K
    links=[dict(satellite_id=str(i),gateway_id='g',constellation_id='x') for i in range(2)]
    args=(links,{'0':[1e6,0,0],'1':[1e6,1e5,0]},{'g':[0,0,0]},{'g':[1,0,0]})
    base=matrix(*args,18.2e9,1,1)
    freq=[17.85e9,18.55e9]
    direct=matrix(*args,freq,1,1)['received_power_w']
    corrected=base['received_power_w'].copy()
    for i in range(2):
        for j in range(2):
            theta=base['rx_offaxis_deg'][i,j]
            corrected[i,j]*=(18.2e9/freq[j])**2*10**((s1428(theta,freq[j]/C)-s1428(theta,18.2e9/C))/10)
    np.testing.assert_allclose(corrected,direct,rtol=1e-12,atol=0)
    p=np.zeros((2,2));p[0,1]=K*398*1e8
    assert aggregate(p,links,[0,0],threshold_db=0)['lf_rate']==0
    p[0,1]*=1.000001
    assert aggregate(p,links,[0,0],threshold_db=0)['lf_rate']==.5


def test_fixed_aperture_tx_frequency_scaling():
    from app.services.feeder_interference import tx_pattern_at_frequency
    width=1.4990500074657407; f0=18.2e9
    for theta in [0,width,4,10,30,90,120,180]:
        assert tx_pattern_at_frequency(theta,f0,f0,35,width)==pytest.approx(s1528(theta,35,width))
    for f in [17.85e9,18.55e9]:
        peak=35+20*math.log10(f/f0)
        assert tx_pattern_at_frequency(0,f,f0,35,width)==pytest.approx(peak)
        assert tx_pattern_at_frequency(width*f0/f,f,f0,35,width)==pytest.approx(peak-3)
    with pytest.raises(ValueError):tx_pattern_at_frequency(0,0,f0,35,width)


def test_fixed_aperture_onaxis_fspl_cancellation():
    links=[dict(satellite_id='s',gateway_id='g',constellation_id='x')]
    args=(links,{'s':[1e6,0,0]},{'g':[0,0,0]},{'g':[1,0,0]})
    # RX stays on its q<=100 branch: on-axis TX/RX each gain f^2,
    # FSPL contributes f^-2, so net received power scales f^2.
    low=matrix(*args,17.85e9,1,1,tx_reference_frequency_hz=18.2e9)['received_power_w'][0,0]
    high=matrix(*args,18.55e9,1,1,tx_reference_frequency_hz=18.2e9)['received_power_w'][0,0]
    assert high/low==pytest.approx((18.55/17.85)**2,rel=1e-12)


def test_frequency_shift_crosses_s1528_main_plateau_boundary():
    from app.services.feeder_interference import tx_pattern_at_frequency
    width=1.4990500074657407;theta=3.8699535849333717
    assert theta>2.58*width
    assert theta<2.58*width*18.2/17.85
    assert s1528(theta,35,width,-20)==15
    peak=35+20*math.log10(17.85/18.2)
    expected=peak-3*(theta/(width*18.2/17.85))**1.5
    assert tx_pattern_at_frequency(theta,17.85e9,18.2e9,35,width,-20)==pytest.approx(expected)
