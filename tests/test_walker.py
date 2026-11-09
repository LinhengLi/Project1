from datetime import datetime, timedelta, timezone
from math import sqrt, pi

import pytest

from qv_sim.walker import WalkerDelta


def test_walker_geometry_and_period():
    epoch = datetime(2026, 11, 5, tzinfo=timezone.utc)
    walker = WalkerDelta(epoch)
    states = walker.states_at(epoch)
    assert len(states) == len({s.satellite_id for s in states}) == 120
    radius = 6378.137 + 550
    period = 2*pi*sqrt(radius**3/398600.4418)
    later = walker.states_at(epoch + timedelta(seconds=period))
    for first, second in zip(states, later):
        assert sqrt(sum(x*x for x in first.position_teme_km)) == pytest.approx(radius)
        assert sum(x*v for x, v in zip(first.position_teme_km, first.velocity_teme_km_s)) == pytest.approx(0, abs=1e-8)
        assert first.position_teme_km == pytest.approx(second.position_teme_km, abs=1e-5)
        assert first.frame == "MEAN_EQUATOR_OF_EPOCH"


@pytest.mark.parametrize("kwargs", [{"total": 121}, {"planes": 0}, {"phasing": 12}, {"altitude_km": -1}])
def test_invalid_walker(kwargs):
    with pytest.raises(ValueError):
        WalkerDelta(datetime(2026, 1, 1, tzinfo=timezone.utc), **kwargs)
