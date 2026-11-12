"""Single-transmitter unwanted-emission budget at the antenna port."""
from math import isfinite, log10, log2

import numpy as np


def integrated_suppression_db(frequencies_hz, psd_w_per_hz, active_band_hz, protected_band_hz):
    """Ratio of band-integrated powers, with interpolation in linear PSD units."""
    frequencies = np.asarray(frequencies_hz, dtype=float)
    psd = np.asarray(psd_w_per_hz, dtype=float)
    if (frequencies.ndim != 1 or frequencies.size < 2 or psd.shape != frequencies.shape
            or not np.all(np.isfinite(frequencies)) or not np.all(np.isfinite(psd))
            or np.any(np.diff(frequencies) <= 0) or np.any(psd < 0)):
        raise ValueError('Expected ordered frequencies and finite nonnegative PSD')

    def integrate(band):
        low, high = band
        if not frequencies[0] <= low < high <= frequencies[-1]:
            raise ValueError('Spectrum must cover each integration band')
        inside = frequencies[(frequencies > low) & (frequencies < high)]
        grid = np.concatenate(([low], inside, [high]))
        return float(np.trapezoid(np.interp(grid, frequencies, psd), grid))

    active = integrate(active_band_hz)
    protected = integrate(protected_band_hz)
    if active <= 0 or protected <= 0:
        raise ValueError('Both bands require positive power or a positive measurement upper bound')
    return 10 * (log10(active) - log10(protected))


def fss_mask_suppression_db(centre_hz, assigned_upper_hz, necessary_hz, protected_band_hz):
    """SM.1541-7 Annex 5 §2 envelope with a flat, fully occupied in-band PSD.

    Restricted to the SM.1539-2 Table 2 normal case above 26 GHz, and to a
    protected band wholly above the assignment and inside the upper OoB domain.
    """
    low, high = protected_band_hz
    if not (centre_hz > 26e9 and 1e6 <= necessary_hz <= 500e6
            and centre_hz < assigned_upper_hz <= low < high <= centre_hz + 2.5 * necessary_hz
            and all(isfinite(value) for value in (centre_hz, assigned_upper_hz, necessary_hz, low, high))):
        raise ValueError('Protected band outside the supported upper out-of-band domain')
    # 40 log10(1 + 2*offset/B) dB below the peak. The common PSD reference
    # bandwidth cancels in the ratio. Integrate the envelope analytically.
    low_factor = 1 + 2 * (low - assigned_upper_hz) / necessary_hz
    high_factor = 1 + 2 * (high - assigned_upper_hz) / necessary_hz
    relative_leakage = (low_factor**-3 - high_factor**-3) / 6
    return -10 * log10(relative_leakage)


def port_power_budget(nominal_eirp_dbw, antenna_gain_dbi, suppression_db, limit_dbw=None):
    """Assume a fixed integrated leakage fraction as transmit power changes."""
    nominal_port_dbw = nominal_eirp_dbw - antenna_gain_dbi
    nominal_leakage_dbw = nominal_port_dbw - suppression_db
    backoff_db = 0.0 if limit_dbw is None else max(0.0, nominal_leakage_dbw - limit_dbw)
    return {
        'nominal_port_dbw': nominal_port_dbw,
        'nominal_leakage_dbw': nominal_leakage_dbw,
        'backoff_db': backoff_db,
        'allowed_port_dbw': nominal_port_dbw - backoff_db,
        'leakage_dbw': nominal_leakage_dbw - backoff_db,
        'eirp_dbw': nominal_eirp_dbw - backoff_db,
    }


def link_capacity_gbps(range_km, frequency_ghz, bandwidth_hz, eirp_dbw,
                       satellite_gt_db_per_k, extra_loss_db, implementation_gap_db,
                       spectral_efficiency_cap):
    return link_budget(range_km, frequency_ghz, bandwidth_hz, eirp_dbw,
                       satellite_gt_db_per_k, extra_loss_db, implementation_gap_db,
                       spectral_efficiency_cap)['capacity_gbps']


def link_budget(range_km, frequency_ghz, bandwidth_hz, eirp_dbw,
                satellite_gt_db_per_k, extra_loss_db, implementation_gap_db,
                spectral_efficiency_cap):
    fspl_db = 92.45 + 20 * log10(range_km) + 20 * log10(frequency_ghz)
    snr_db = (eirp_dbw + satellite_gt_db_per_k - fspl_db - extra_loss_db
              + 228.6 - 10 * log10(bandwidth_hz) - implementation_gap_db)
    efficiency = min(spectral_efficiency_cap, log2(1 + 10 ** (snr_db / 10)))
    return {'fspl_db': fspl_db, 'effective_snr_db': snr_db,
            'capacity_gbps': bandwidth_hz * efficiency / 1e9}
