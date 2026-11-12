import pytest

from qv_sim.sharing import Flow, solve


def test_hand_computable():
    links={('A','S1'):1.2,('A','S2'):1.0,('B','S1'):1.1,('B','S2'):0.4}
    capacities={'S1':1.0,'S2':1.0}
    flows=[Flow(g,c,.4,.4,w) for g in ['A','B'] for c,w in [('high',3),('ordinary',1)]]
    independent=solve(links,capacities,flows,'independent')
    joint=solve(links,capacities,flows,'qos')
    assert independent['throughput']==pytest.approx(1,abs=1e-6)
    assert independent['weighted_deficit']==pytest.approx(.6,abs=1e-6)
    assert joint['throughput']==pytest.approx(1.6,abs=1e-6)
    assert joint['weighted_deficit']==pytest.approx(0,abs=1e-6)
    assert joint['association']=={'A':'S2','B':'S1'}
    for result in [independent,joint]:
        assert all(load<=capacities[s]+1e-6 for s,load in result['satellite_load'].items())


def test_no_link_and_invalid_flow():
    result=solve({}, {}, [Flow('A','high',1,.5,2)], 'qos')
    assert result['throughput']==pytest.approx(0)
    assert result['weighted_deficit']==pytest.approx(1)
    with pytest.raises(ValueError):
        solve({}, {}, [Flow('A','bad',1,2,1)], 'qos')
