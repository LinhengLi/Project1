from math import cos, log10, radians, sqrt

import numpy as np
import pytest
from scipy.integrate import quad

from qv_sim.atmosphere import (
    _reference_atmosphere,
    _refractive_index,
    _specific_attenuation,
    gaseous_loss_db,
)
from qv_sim.spectrum import fss_mask_suppression_db, integrated_suppression_db, port_power_budget


def test_sampled_psd_integrates_linear_power_at_band_edges():
    frequencies = [0, 1, 2, 3, 4, 5]
    psd = [4, 4, 4, 2, 1, 0]
    suppression = integrated_suppression_db(frequencies, psd, (.5, 1.5), (3.5, 4.5))
    assert suppression == pytest.approx(10 * log10(4))
    with pytest.raises(ValueError, match='cover'):
        integrated_suppression_db(frequencies, psd, (.5, 1.5), (4.5, 5.5))


def test_fss_envelope_and_port_backoff():
    bandwidth = 250e6
    upper_edge = 50.125e9
    low, high = 50.2e9, 50.4e9
    integrated, _ = quad(lambda f: (1 + 2 * (f - upper_edge) / bandwidth)**-4, low, high)
    suppression = fss_mask_suppression_db(50e9, upper_edge, bandwidth, (low, high))
    assert suppression == pytest.approx(10 * log10(bandwidth / integrated))
    result = port_power_budget(65, 55, suppression, -42)
    assert result['leakage_dbw'] == pytest.approx(-42)
    assert result['eirp_dbw'] == pytest.approx(65 - (52 - suppression))
    with pytest.raises(ValueError, match='domain'):
        fss_mask_suppression_db(50e9, upper_edge, bandwidth, (low, 50.7e9))


def test_gaseous_loss_layer_sum_matches_slant_quadrature():
    pressure, temperature, vapour = _reference_atmosphere(np.array([0.0]))
    assert temperature[0] == pytest.approx(288.15)
    assert pressure[0] + vapour[0] == pytest.approx(1013.25)
    assert vapour[0] == pytest.approx(7.5 * 288.15 / 216.7)
    surface_index = _refractive_index(pressure, temperature, vapour)[0]

    def integrand(height_km):
        profile = _reference_atmosphere(np.array([height_km]))
        gamma = _specific_attenuation(50, *profile)[0]
        index = _refractive_index(*profile)[0]
        slant_cosine = 6371 * surface_index * cos(radians(25)) / ((6371 + height_km) * index)
        return gamma / sqrt(1 - slant_cosine**2)

    integrated, _ = quad(integrand, 0, 100, points=[11, 20, 32, 47, 51, 71, 86, 91])
    assert gaseous_loss_db(50, 25) == pytest.approx(integrated, abs=.001)
    assert gaseous_loss_db(50, 25) > gaseous_loss_db(50, 45) > gaseous_loss_db(50, 90) > 0
