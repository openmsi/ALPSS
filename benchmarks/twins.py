"""Simulated twins of real files.

measure() reads what a real shot is made of: the carrier frequency, the
carrier and Doppler amplitudes over time, the velocity (the spectrogram ridge
above the carrier), the shock arrival and the noise. synthesize() rebuilds a
voltage from those with a velocity that is zero before the arrival, so the
twin's start time is known exactly. Its knobs change one ingredient at a time.
"""

import numpy as np
from scipy import signal

NPERSEG = 1024  # spectrogram window: long enough to separate ~150 m/s from the carrier
HOP = 16


def _peak_freq(x, fs):
    """Frequency of the strongest tone in x, refined by parabolic interpolation."""
    nfft = 1 << 20
    spec = np.abs(np.fft.rfft(x * np.hanning(x.size), nfft))
    k = int(np.argmax(spec[1:-1])) + 1
    a, b, c = np.log(spec[k - 1:k + 2])
    return (k + 0.5 * (a - c) / (a - 2 * b + c)) * fs / nfft


def measure(time, voltage, sample_rate, lam, carrier_band_time):
    """Ingredients of a real shot; `carrier_band_time` is the shot-free lead-in."""
    fs = sample_rate
    t = time - time[0]
    pre = t < carrier_band_time
    fc = _peak_freq(voltage[pre], fs)

    f, tc, Z = signal.stft(voltage, fs, nperseg=NPERSEG, noverlap=NPERSEG - HOP,
                           nfft=4 * NPERSEG, boundary=None, padded=False)
    A = 2 * np.abs(Z)  # scipy normalizes by the window sum, so this is the tone amplitude
    ic = int(np.argmin(np.abs(f - fc)))
    carrier_amp = A[ic - 1:ic + 2].max(axis=0)

    above = f > fc + 2 * fs / NPERSEG  # outside the carrier's main lobe
    ridge = np.argmax(A[above], axis=0)
    doppler_amp = A[above][ridge, np.arange(tc.size)]
    doppler_vel = (f[above][ridge] - fc) * lam / 2

    # arrival: the envelope above the carrier first stays well above its lead-in level
    sos = signal.butter(4, [fc + 0.25e9, min(6e9, 0.45 * fs)], "bandpass", fs=fs, output="sos")
    env = np.abs(signal.hilbert(signal.sosfiltfilt(sos, voltage)))
    env = np.convolve(env, np.ones(int(fs * 1e-9)) / int(fs * 1e-9), mode="same")
    threshold = np.median(env[pre]) + 10 * np.std(env[pre])
    hold = int(fs * 5e-9)
    hot = np.convolve(env > threshold, np.ones(hold), mode="valid") == hold
    candidates = np.flatnonzero(hot & (t[:hot.size] > carrier_band_time))
    if candidates.size == 0:
        raise ValueError("no shock arrival found")
    arrival = t[candidates[0]]

    # velocity from the ridge, kept only where the Doppler return stands out
    floor = np.median(doppler_amp[tc < carrier_band_time])
    good = (tc > arrival + NPERSEG / fs / 2) & (doppler_amp > 3 * floor)
    vel = signal.medfilt(np.interp(tc, tc[good], doppler_vel[good]), 9)

    # noise: everything but the carrier, before the shot
    sos = signal.butter(4, [fc - 0.2e9, fc + 0.2e9], "bandpass", fs=fs, output="sos")
    resid = (voltage - signal.sosfiltfilt(sos, voltage))[pre]
    nf, psd = signal.welch(resid, fs, nperseg=2048)
    ref = np.median(psd[(nf > fc + 1e9) & (nf < 15e9)])
    noise_bw = float(nf[np.flatnonzero(psd > 0.1 * ref)[-1]])

    return dict(
        sample_rate=fs, lam=lam, carrier_band_time=carrier_band_time, fc=fc, arrival=arrival,
        noise_sd=float(resid.std()), noise_bw=noise_bw,
        tc=tc, carrier_amp=carrier_amp, doppler_amp=doppler_amp, velocity=vel,
    )


def synthesize(m, seed, velocity_scale=1.0, doppler_scale=1.0, noise_scale=1.0,
               carrier_fade=True):
    """Rebuild a shot from measure()'s ingredients; returns (time, voltage, velocity).

    carrier_fade=False holds the carrier at its lead-in level until the arrival.
    """
    fs = m["sample_rate"]
    t = np.arange(int(round((m["tc"][-1] + NPERSEG / fs / 2) * fs))) / fs
    arrival = m["arrival"]
    after = t >= arrival

    # velocity: a linear rise over the first half window, where the ridge is smeared
    rise_end = arrival + NPERSEG / fs / 2
    v_rise_end = np.interp(rise_end, m["tc"], m["velocity"])
    velocity = np.where(t < rise_end,
                        v_rise_end * np.clip((t - arrival) / (rise_end - arrival), 0, 1),
                        np.interp(t, m["tc"], m["velocity"]))
    velocity = np.clip(velocity, 0, None) * velocity_scale

    carrier_amp = np.interp(t, m["tc"], m["carrier_amp"])
    if not carrier_fade:
        lead = np.median(m["carrier_amp"][m["tc"] < m["carrier_band_time"]])
        carrier_amp[~after] = lead
    doppler_amp = np.where(after, np.interp(t, m["tc"], m["doppler_amp"]), 0) * doppler_scale

    rng = np.random.default_rng(seed)
    phase = 4 * np.pi * np.cumsum(velocity) / fs / m["lam"]
    carrier = 2 * np.pi * m["fc"] * t
    voltage = (carrier_amp * np.cos(carrier)
               + doppler_amp * np.cos(carrier + phase + rng.uniform(0, 2 * np.pi)))

    noise = signal.sosfiltfilt(
        signal.butter(8, min(m["noise_bw"], 0.45 * fs), fs=fs, output="sos"),
        rng.normal(size=t.size),
    )
    voltage += noise / noise.std() * m["noise_sd"] * noise_scale
    return t, voltage, velocity
