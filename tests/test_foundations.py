from datetime import datetime, timezone
from math import cos, sin, radians

import pytest

from qv_sim import GroundSite, SatelliteState, Sgp4Constellation, observe
from qv_sim.orbit import julian_date

# Published Vallado SGP4 verification case, not current operational data.
TLE = """VANGUARD 1
1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753
2 00005  34.2682 348.7242 1859667 331.7664  19.3264 10.82419157413667
"""


def test_sgp4_reference(tmp_path):
    path = tmp_path / "reference.tle"
    path.write_text(TLE)
    constellation = Sgp4Constellation.from_file(path)
    time = datetime(2000, 6, 27, 18, 50, 19, 733568, tzinfo=timezone.utc)
    state = constellation.states_at(time)[0]
    assert state.position_teme_km == pytest.approx((7022.46529266, -1400.08296755, 0.03995155), abs=1e-5)
    with pytest.raises(ValueError, match="timezone"):
        constellation.states_at(datetime(2000, 6, 27))


@pytest.mark.parametrize("height, expected", [(550, True), (-550, False)])
def test_overhead_and_below_horizon(height, expected):
    time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    jd, fraction = julian_date(time)
    days = jd - 2451545 + fraction
    t = days / 36525
    angle = radians((280.46061837 + 360.98564736629 * days + 0.000387933 * t*t - t**3 / 38710000) % 360)
    radius = 6378.137 + height
    state = SatelliteState("test", "test", time, (radius*cos(angle), radius*sin(angle), 0), (0, 0, 0))
    result = observe(GroundSite("equator", 0, 0), state)
    assert result.visible is expected
    assert result.slant_range_km == pytest.approx(550)
    assert result.elevation_deg == pytest.approx(90 if expected else -90)


def test_invalid_input(tmp_path):
    path = tmp_path / "bad.tle"
    path.write_text("broken")
    with pytest.raises(ValueError):
        Sgp4Constellation.from_file(path)
    with pytest.raises(ValueError):
        GroundSite("bad", 91, 0)
