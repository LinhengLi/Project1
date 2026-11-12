"""Reference-atmosphere gaseous attenuation on ascending Earth-space paths."""
from functools import lru_cache

import numpy as np

from ._p676_lines import OXYGEN, WATER_VAPOUR


# ITU-R P.835-7 Annex 1. Geopotential base height, temperature, pressure and lapse rate.
_LAYERS = (
    (0, 288.15, 1013.25, -6.5),
    (11, 216.65, 226.3226, 0),
    (20, 216.65, 54.74980, 1),
    (32, 228.65, 8.680422, 2.8),
    (47, 270.65, 1.109106, 0),
    (51, 270.65, 0.6694167, -2.8),
    (71, 214.65, 0.03956649, -2),
)


def _reference_atmosphere(height_km):
    geopotential = 6356.766 * height_km / (6356.766 + height_km)
    temperature = np.empty_like(height_km)
    pressure = np.empty_like(height_km)
    for i, (base_height, base_temperature, base_pressure, lapse_rate) in enumerate(_LAYERS):
        upper = _LAYERS[i+1][0] if i+1 < len(_LAYERS) else np.inf
        layer = (geopotential >= base_height) & (geopotential < upper) & (height_km < 86)
        dz = geopotential[layer] - base_height
        temp = base_temperature + lapse_rate * dz
        temperature[layer] = temp
        if lapse_rate:
            pressure[layer] = base_pressure * (base_temperature / temp) ** (34.1632 / lapse_rate)
        else:
            pressure[layer] = base_pressure * np.exp(-34.1632 * dz / base_temperature)
    high = height_km >= 86
    z = height_km[high]
    temperature[high] = np.where(z <= 91, 186.8673,
                                 263.1905 - 76.3232 * np.sqrt(1 - ((z-91)/19.9429)**2))
    pressure[high] = np.exp(np.polynomial.polynomial.polyval(
        z, [95.571899, -4.011801, 0.06424731, -0.000478966, 0.000001340543]))
    vapour = np.maximum(7.5 * np.exp(-height_km/2) * temperature / 216.7, 2e-6 * pressure)
    return pressure - vapour, temperature, vapour


def _specific_attenuation(frequency_ghz, dry_hpa, temperature_k, vapour_hpa):
    # P.676-13 Annex 1 equations (1)–(9). Axis 0 is height and axis 1 is spectral line.
    f = frequency_ghz
    p, theta, e = dry_hpa[:, None], (300 / temperature_k)[:, None], vapour_hpa[:, None]
    fo, a1, a2, a3, a4, a5, a6 = OXYGEN.T
    fw, b1, b2, b3, b4, b5, b6 = WATER_VAPOUR.T
    oxygen_strength = a1 * 1e-7 * p * theta**3 * np.exp(a2 * (1 - theta))
    water_strength = b1 * .1 * e * theta**3.5 * np.exp(b2 * (1 - theta))
    oxygen_width = a3 * 1e-4 * (p * theta**(.8 - a4) + 1.1 * e * theta)
    oxygen_width = np.sqrt(oxygen_width**2 + 2.25e-6)
    water_width = b3 * 1e-4 * (p * theta**b4 + b5 * e * theta**b6)
    water_width = .535 * water_width + np.sqrt(.217 * water_width**2 + 2.1316e-12 * fw**2 / theta)
    mixing = (a5 + a6 * theta) * 1e-4 * (p + e) * theta**.8
    oxygen = (oxygen_strength * _line_shape(f, fo, oxygen_width, mixing)).sum(axis=1)
    water = (water_strength * _line_shape(f, fw, water_width, 0)).sum(axis=1)
    d = 5.6e-4 * (p + e) * theta**.8
    continuum = f * p * theta**2 * (6.14e-5 * d / (d**2 + f**2)
                                  + 1.4e-12 * p * theta**1.5 / (1 + 1.9e-5 * f**1.5))
    return .1820 * f * (oxygen + water + continuum[:, 0])


def _line_shape(frequency, centres, widths, mixing):
    lower = centres - frequency
    upper = centres + frequency
    return frequency / centres * ((widths - mixing * lower) / (lower**2 + widths**2)
                                  + (widths - mixing * upper) / (upper**2 + widths**2))


def _refractive_index(dry_hpa, temperature_k, vapour_hpa):
    # P.453-14 Annex 1 equations (1) and (2).
    return 1 + 1e-6 * ((77.6 * dry_hpa + 72 * vapour_hpa) / temperature_k
                       + 3.75e5 * vapour_hpa / temperature_k**2)


@lru_cache(maxsize=32)
def _slant_layers(frequency_ghz, station_height_km):
    # P.676-13 Annex 1 §2.2.1. Clip the exponential layer grid to the path bounds.
    boundaries = np.concatenate(([0], np.cumsum(.0001 * np.exp(np.arange(922) / 100))))
    inner = boundaries[(boundaries > station_height_km) & (boundaries < 100)]
    boundaries = np.concatenate(([station_height_km], inner, [100]))
    centres = (boundaries[1:] + boundaries[:-1]) / 2
    profile = _reference_atmosphere(centres)
    attenuation = _specific_attenuation(frequency_ghz, *profile) * np.diff(boundaries)
    ground_index = _refractive_index(*_reference_atmosphere(np.array([station_height_km])))[0]
    angle_factor = (6371 + station_height_km) * ground_index / (
        (6371 + centres) * _refractive_index(*profile))
    return attenuation, angle_factor


def gaseous_loss_db(frequency_ghz, elevation_deg, station_height_km=0.0):
    """P.676-13 Annex 1 using the P.835-7 reference atmosphere to 100 km.

    Elevation is the ground apparent angle. The existing geometric angles
    above 25 degrees are used as its approximation in the feeder experiment.
    """
    if not 1 <= frequency_ghz <= 1000 or not 0 <= station_height_km < 100:
        raise ValueError('Frequency or station height outside the reference model')
    if not 5 <= elevation_deg <= 90:
        raise ValueError('This implementation supports elevations from 5 to 90 degrees')
    attenuation, angle_factor = _slant_layers(frequency_ghz, station_height_km)
    slant_cosine = angle_factor * np.cos(np.deg2rad(elevation_deg))
    return float(np.sum(attenuation / np.sqrt(1 - slant_cosine**2)))
