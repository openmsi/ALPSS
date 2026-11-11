"""Simulated twins of real files.

measure() reads what a real shot is made of: the carrier frequency, the
carrier and Doppler amplitudes over time, the velocity, the shock arrival and
the noise. synthesize() feeds those to the original simulation code,
alpss.simulation.velocity_to_pdv_voltage, unchanged: the velocity is zero
before the arrival, so the twin's start time is known exactly, and the light
powers and noise level are set so the carrier, Doppler return and noise have
the real file's proportions. Its knobs change one ingredient at a time.

The carrier is tracked by demodulating at its frequency with a narrow low-pass
(CARRIER_BW) and subtracted; what is left above it is the Doppler return,
whose phase gives the velocity.
"""

import numpy as np
from scipy import signal

from alpss.simulation import velocity_to_pdv_voltage

CARRIER_BW = 20e6  # carrier amplitude changes slower than this; ~30 m/s at 1550 nm
DOPPLER_BW = 3e9  # widest Doppler shift kept, ~2300 m/s
GRID = 0.25e-9  # time step of the measured ingredients
SMOOTH = 2e-9  # smoothing of the Doppler amplitude and velocity
ARRIVAL_SHIFT = 50e6  # ~40 m/s; slower carrier changes (fades) are not an arrival
C_LIGHT = 3e8  # same constant as pdv_synthesis
POWER_SIGNAL_DBM = -1  # velocity_to_pdv_voltage's default return power


def _peak_freq(x, fs):
    """Frequency of the strongest tone in x, refined by parabolic interpolation."""
    nfft = 1 << 20
    spec = np.abs(np.fft.rfft(x * np.hanning(x.size), nfft))
    k = int(np.argmax(spec[1:-1])) + 1
    a, b, c = np.log(spec[k - 1:k + 2])
    return (k + 0.5 * (a - c) / (a - 2 * b + c)) * fs / nfft


def _lowpass(x, cutoff, fs):
    # pad by a few time constants so the record's edges don't ring
    sos = signal.butter(4, cutoff, fs=fs, output="sos")
    pad = dict(padtype="even", padlen=min(x.size - 1, int(5 * fs / cutoff)))
    return signal.sosfiltfilt(sos, x.real, **pad) + 1j * signal.sosfiltfilt(sos, x.imag, **pad)


def _smooth(x, n):
    return np.convolve(x, np.ones(n) / n, mode="same")


def measure(time, voltage, sample_rate, lam, carrier_band_time):
    """Ingredients of a real shot; `carrier_band_time` is the shot-free lead-in."""
    fs = sample_rate
    t = time - time[0]
    pre = t < carrier_band_time
    fc = _peak_freq(voltage[pre], fs)
    lo = np.exp(-2j * np.pi * fc * t)

    # carrier: slow complex amplitude at fc
    c = _lowpass(voltage * lo, CARRIER_BW, fs)
    carrier_amp = 2 * np.abs(c)
    resid = voltage - 2 * np.real(c / lo)
    # an upshifted return sits above the carrier; drop baseline drift below it
    resid = signal.sosfiltfilt(signal.butter(4, fc / 2, "highpass", fs=fs, output="sos"), resid)

    # Doppler: the upshifted part of the residual, brought to baseband
    d = _lowpass(signal.hilbert(resid) * lo, DOPPLER_BW, fs)
    n = max(1, int(fs * SMOOTH))
    doppler_amp = _smooth(np.abs(d), n)
    shift = _smooth(np.gradient(np.unwrap(np.angle(d))) * fs / (2 * np.pi), n)

    # arrival: the return shifted clearly off the carrier (ARRIVAL_SHIFT) first
    # stays well above its lead-in level, which skips the filters' edge transients
    lead = pre & (t > 50e-9)
    shifted = _smooth(np.abs(d - _lowpass(d, ARRIVAL_SHIFT, fs)), n)
    level = np.median(shifted[lead])
    threshold = level + 10 * np.median(np.abs(shifted[lead] - level))
    hold = int(fs * 5e-9)
    hot = np.convolve(shifted > threshold, np.ones(hold), mode="valid") == hold
    candidates = np.flatnonzero(hot & (t[:hot.size] > carrier_band_time))
    if candidates.size == 0:
        raise ValueError("no shock arrival found")
    arrival = t[candidates[0]]

    # velocity where the return stands out; gaps are bridged
    floor = np.median(doppler_amp[lead])
    good = (t >= arrival) & (doppler_amp > 3 * floor)
    vel = np.interp(t, t[good], shift[good] * lam / 2)

    # noise: everything but the carrier, before the shot
    nf, psd = signal.welch(resid[lead], fs, nperseg=2048)
    ref = np.median(psd[(nf > fc + 1e9) & (nf < 15e9)])
    noise_bw = float(nf[np.flatnonzero(psd > 0.1 * ref)[-1]])

    step = max(1, int(fs * GRID))
    return dict(
        sample_rate=fs, lam=lam, carrier_band_time=carrier_band_time, n=t.size,
        fc=fc, arrival=arrival, noise_sd=float(resid[lead].std()), noise_bw=noise_bw,
        tc=t[::step], carrier_amp=carrier_amp[::step], doppler_amp=doppler_amp[::step],
        velocity=signal.medfilt(vel[::step], 9),
    )


def synthesize(m, seed, velocity_scale=1.0, doppler_scale=1.0, noise_scale=1.0):
    """Rebuild a shot with velocity_to_pdv_voltage; returns (time, voltage, velocity, params).

    The simulation has constant light powers, so the twin keeps the real
    file's average proportions, not how they change over time: the moving
    return (Doppler) and the stationary reflection (the carrier left after the
    arrival) are set from their medians after the arrival, and noise_sd gives
    the same noise-to-Doppler ratio as the real file.
    """
    fs = m["sample_rate"]
    t = np.arange(m["n"]) / fs
    velocity = np.where(t >= m["arrival"],
                        np.clip(np.interp(t, m["tc"], m["velocity"]), 0, None), 0)
    velocity = velocity * velocity_scale

    tc, after = m["tc"], m["tc"] >= m["arrival"]
    doppler = np.median(m["doppler_amp"][after & (tc < m["arrival"] + 50e-9)])
    carrier = np.median(m["carrier_amp"][tc >= m["arrival"] + 20e-9])
    e_signal = 10 ** (POWER_SIGNAL_DBM / 20) * doppler_scale
    e_target = 10 ** (POWER_SIGNAL_DBM / 20) * carrier / doppler
    params = dict(
        lambda_ref=m["lam"],
        lambda_tar=C_LIGHT / (C_LIGHT / m["lam"] - m["fc"]),  # carrier at fc
        power_signal_dbm=20 * np.log10(e_signal),
        power_tar_dbm=20 * np.log10(e_target),
    )
    # velocity_to_pdv_voltage scales noise by the signal's maximum
    peak = velocity_to_pdv_voltage(t, velocity, noise_sd=0.0, **params).max()
    params["noise_sd"] = (m["noise_sd"] * noise_scale / doppler
                          * 10 ** (POWER_SIGNAL_DBM / 20) / peak)

    np.random.seed(seed)  # pdv_synthesis draws noise from the global RNG
    voltage = velocity_to_pdv_voltage(t, velocity, **params)
    return t, voltage, velocity, params
