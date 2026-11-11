import numpy as np
import pytest
from scipy import signal

from alpss.simulation import velocity_to_pdv_voltage

FS = 80e9
C_LIGHT = 3e8
LAM_REF = 1550e-9
FC = 2e9  # carrier
LAM_TAR = C_LIGHT / (C_LIGHT / LAM_REF - FC)


@pytest.fixture
def shot():
    time = np.arange(40000) / FS
    velocity = np.where(time > 250e-9, 300.0, 0.0)  # 300 m/s step: ~0.39 GHz shift
    return time, velocity


def tones(voltage, mask=None, min_db=-20):
    """Frequencies (GHz) of spectral peaks within min_db of the strongest."""
    v = voltage if mask is None else voltage[mask]
    f, p = signal.welch(v, FS, nperseg=4096)
    p = 10 * np.log10(p / p.max())
    peaks, _ = signal.find_peaks(p, height=min_db, distance=20)
    return f[peaks] / 1e9


def original(time, velocity, noise_sd):
    """velocity_to_pdv_voltage as it was before the opt-in options."""
    sample_rate = 1.0 / (time[1] - time[0])
    f_tar, f_ref = C_LIGHT / LAM_TAR, C_LIGHT / LAM_REF
    E_ref0, E_s0 = 1.0, 10 ** (-1 / 20)
    E_tar0 = 10 ** (-11 / 20)
    phase = 4 * np.pi * np.cumsum(velocity / sample_rate) / LAM_REF
    E_ref = E_ref0 * np.cos(2 * np.pi * f_ref * time)
    E_tar = E_tar0 * np.cos(2 * np.pi * f_tar * time)
    E_s = E_s0 * np.cos(2 * np.pi * f_tar * time - phase)
    voltage = E_ref * E_s + E_ref * E_tar + E_tar * E_s
    voltage += voltage.max() * np.random.normal(0, noise_sd, voltage.size)
    return voltage


def test_defaults_unchanged(shot):
    time, velocity = shot
    np.random.seed(0)
    expected = original(time, velocity, 0.05)
    np.random.seed(0)
    got = velocity_to_pdv_voltage(time, velocity, LAM_REF, LAM_TAR, noise_sd=0.05)
    np.testing.assert_array_equal(got, expected)


def test_full_products_alias_sum_frequency(shot):
    """Documents why beat_only exists: the sum term folds back as a tone."""
    time, velocity = shot
    v = velocity_to_pdv_voltage(time, velocity, LAM_REF, LAM_TAR, noise_sd=0.0)
    assert any(f > 5 for f in tones(v))


def test_beat_only_keeps_carrier_and_doppler(shot):
    time, velocity = shot
    v = velocity_to_pdv_voltage(time, velocity, LAM_REF, LAM_TAR, noise_sd=0.0, beat_only=True)
    before, after = time < 250e-9, time > 300e-9
    assert tones(v, before) == pytest.approx([FC / 1e9], abs=0.05)
    doppler = (FC + 2 * 300 / LAM_REF) / 1e9
    assert all(f < 5 for f in tones(v, after))
    assert any(abs(f - doppler) < 0.05 for f in tones(v, after))


def test_beat_only_amplitude_is_half_the_field_product(shot):
    time, _ = shot
    v = velocity_to_pdv_voltage(time, np.zeros_like(time), LAM_REF, LAM_TAR,
                                power_signal_dbm=0, power_tar_dbm=-200, noise_sd=0.0, beat_only=True)
    # E_ref = E_s = 1 and no target return: one carrier tone of amplitude 1/2
    assert np.ptp(v) == pytest.approx(1.0, rel=1e-3)


def test_signal_envelope_switches_doppler_off(shot):
    time, velocity = shot
    v = velocity_to_pdv_voltage(time, velocity, LAM_REF, LAM_TAR, noise_sd=0.0, beat_only=True,
                                signal_envelope=np.zeros_like(time))
    doppler = (FC + 2 * 300 / LAM_REF) / 1e9
    assert not any(abs(f - doppler) < 0.05 for f in tones(v, time > 300e-9, min_db=-60))


def test_noise_bandwidth_limits_noise(shot):
    time, _ = shot
    np.random.seed(1)
    v = velocity_to_pdv_voltage(time, np.zeros_like(time), LAM_REF, LAM_TAR, noise_sd=0.1,
                                beat_only=True, noise_bandwidth=10e9)
    clean = velocity_to_pdv_voltage(time, np.zeros_like(time), LAM_REF, LAM_TAR, noise_sd=0.0,
                                    beat_only=True)
    noise = v - clean
    assert noise.std() == pytest.approx(0.1 * clean.max(), rel=1e-6)
    f, p = signal.welch(noise, FS, nperseg=4096)
    assert p[f > 20e9].mean() < 1e-3 * p[f < 8e9].mean()


def test_noise_bandwidth_without_noise(shot):
    time, velocity = shot
    v = velocity_to_pdv_voltage(time, velocity, LAM_REF, LAM_TAR, noise_sd=0.0,
                                beat_only=True, noise_bandwidth=10e9)
    assert np.isfinite(v).all()
