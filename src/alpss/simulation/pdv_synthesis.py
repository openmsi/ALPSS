"""
pdv_synthesis.py
----------------
Core functions for generating synthetic Photonic Doppler Velocimetry (PDV) signals
from a given velocity-time history.

Workflow:
    velocity + time  →  phase  →  optical beat voltage  →  CSV output
"""

import numpy as np
from scipy.signal import ShortTimeFFT

C_LIGHT = 3e8  # m/s


# ---------------------------------------------------------------------------
# STFT helper
# ---------------------------------------------------------------------------

def compute_stft(voltage, fs, window="hann", nperseg=600, noverlap=500, nfft=5120):
    """Compute a Short-Time Fourier Transform with zero-padded boundaries.

    Returns frequency, time, and complex STFT arrays cropped to match the
    legacy scipy.signal.stft time axis (no edge padding).

    Parameters
    ----------
    voltage : np.ndarray
        1-D voltage signal.
    fs : float
        Sampling frequency in Hz.
    window : str
        Window type (passed to scipy ShortTimeFFT.from_window).
    nperseg : int
        Samples per STFT segment.
    noverlap : int
        Overlapping samples between segments.
    nfft : int
        FFT size (zero-padding).

    Returns
    -------
    f : np.ndarray    Frequency axis (Hz).
    t : np.ndarray    Time axis (s).
    Zxx : np.ndarray  Complex STFT array, shape (len(f), len(t)).
    """
    SFT = ShortTimeFFT.from_window(
        window,
        fs=fs,
        nperseg=nperseg,
        noverlap=noverlap,
        mfft=nfft,
        scale_to="magnitude",
        phase_shift=None,
    )
    Sx_full = SFT.stft(voltage, padding="zeros")
    t_full = SFT.t(len(voltage))
    f = SFT.f

    # Legacy-compatible time axis (no boundary padding)
    t_legacy = np.arange(
        nperseg / 2,
        voltage.shape[-1] - nperseg / 2 + 1,
        nperseg - noverlap,
    ) / float(fs)

    t_idx = np.argmin(np.abs(t_full - t_legacy[0]))
    t_crop = t_full[t_idx: t_idx + len(t_legacy)]
    Sx_crop = Sx_full[:, t_idx: t_idx + len(t_legacy)]

    return f, t_crop, Sx_crop


# ---------------------------------------------------------------------------
# Velocity profile generator
# ---------------------------------------------------------------------------

def generate_velocity_profile(shot_type, sample_rate=128e9, **kwargs):
    """Build a synthetic velocity-time profile for a given shot type.

    Parameters
    ----------
    shot_type : str
        One of ``"velocity"``, ``"HEL"``, ``"HEL-spall"``.
    sample_rate : float
        Digitizer sampling rate in Hz (default 128 GHz).
    **kwargs
        Override any default parameter for the chosen shot type.
        See source for available keys per shot type.

    Returns
    -------
    time : np.ndarray   Time array in seconds.
    velocity : np.ndarray  Velocity array in m/s.
    """
    if shot_type == "velocity":
        p = dict(t_begin=-500e-9, t_end=1000e-9, vel_peak=200, a=1, b=0.00001)
        p.update(kwargs)
        time = np.arange(p["t_begin"], p["t_end"], 1 / sample_rate)
        x = (time > 0) * time
        intercept = p["b"] / p["vel_peak"] / p["a"]
        velocity = (p["vel_peak"] * (x + intercept) * p["a"] - p["b"]) / (x + intercept) * p["a"]

    elif shot_type == "HEL":
        p = dict(
            t_begin=-3e-6, t_end=3e-6,
            V0=0, V_HEL=50, V_plat=300,
            t_rise1=5e-9, t_rise2=10e-9, t_rise3=20e-9,
            t_return1=50e-9, t_return2=70e-9,
        )
        p.update(kwargs)
        time = np.arange(p["t_begin"], p["t_end"], 1 / sample_rate)
        velocity = np.zeros_like(time)
        for i, t in enumerate(time):
            if t < 0:
                velocity[i] = p["V0"]
            elif t < p["t_rise1"]:
                velocity[i] = p["V0"] + (p["V_HEL"] - p["V0"]) * (t / p["t_rise1"])
            elif t < p["t_rise2"]:
                velocity[i] = p["V0"] + p["V_HEL"]
            elif t < p["t_rise3"]:
                velocity[i] = p["V_HEL"] + (p["V_plat"] - p["V_HEL"]) * (
                    (t - p["t_rise2"]) / (p["t_rise3"] - p["t_rise2"])
                )
            elif t < p["t_return1"]:
                velocity[i] = p["V_plat"]
            elif t < p["t_return2"]:
                velocity[i] = p["V_plat"] + (p["V0"] - p["V_plat"]) * (
                    (t - p["t_return1"]) / (p["t_return2"] - p["t_return1"])
                )
            else:
                velocity[i] = p["V0"]

    elif shot_type == "HEL-spall":
        p = dict(
            t_begin=-3e-6, t_end=3e-6,
            V0=0, V_HEL=100, V_plat=300,
            t_hel_start=3e-9, t_hel_end=7e-9,
            t_plat_start=15e-9, t_plat_end=25e-9,
            t_spall=40e-9, t_recover=60e-9,
            dV_spall=100,
        )
        p.update(kwargs)
        time = np.arange(p["t_begin"], p["t_end"], 1 / sample_rate)
        velocity = np.zeros_like(time)
        for i, t in enumerate(time):
            if t < 0:
                velocity[i] = p["V0"]
            elif t < p["t_hel_start"]:
                velocity[i] = p["V0"] + (p["V_HEL"] - p["V0"]) * (t / p["t_hel_start"])
            elif t < p["t_hel_end"]:
                velocity[i] = p["V_HEL"]
            elif t < p["t_plat_start"]:
                velocity[i] = p["V_HEL"] + (p["V_plat"] - p["V_HEL"]) * (
                    (t - p["t_hel_end"]) / (p["t_plat_start"] - p["t_hel_end"])
                )
            elif t < p["t_plat_end"]:
                velocity[i] = p["V_plat"]
            elif t < p["t_spall"]:
                velocity[i] = p["V_plat"] - p["dV_spall"] * (
                    (t - p["t_plat_end"]) / (p["t_spall"] - p["t_plat_end"])
                )
            elif t < p["t_recover"]:
                velocity[i] = p["V_plat"] - p["dV_spall"] + p["dV_spall"] * (
                    (t - p["t_spall"]) / (p["t_recover"] - p["t_spall"])
                )
            else:
                velocity[i] = p["V_plat"]

    else:
        raise ValueError(f"Unknown shot_type '{shot_type}'. Choose from: 'velocity', 'HEL', 'HEL-spall'.")

    return time, velocity


# ---------------------------------------------------------------------------
# Single-point PDV synthesis
# ---------------------------------------------------------------------------

def velocity_to_pdv_voltage(
    time,
    velocity,
    lambda_ref=1550e-9,
    lambda_tar=1550.016e-9,
    power_ref_dbm=0,
    power_signal_dbm=-1,
    power_tar_dbm=None,
    noise_sd=0.1,
    output_csv=None,
):
    """Convert a velocity-time history to a synthetic single-point PDV voltage signal.

    Simulates heterodyne PDV beat signal including reference, Doppler-shifted
    signal, and target (constant-reflection) fields.  Gaussian multiplicative
    noise is added.

    Parameters
    ----------
    time : np.ndarray
        Time array in seconds.
    velocity : np.ndarray
        Velocity array in m/s, same length as ``time``.
    lambda_ref : float
        Reference laser wavelength in meters (default 1550 nm).
    lambda_tar : float
        Target laser wavelength in meters (default 1550.016 nm).
    power_ref_dbm : float
        Reference beam power in dBm (default 0 dBm).
    power_signal_dbm : float
        Return signal (Doppler-shifted) power in dBm (default −1 dBm).
    power_tar_dbm : float or None
        Constant back-reflection (target output) power in dBm.
        Defaults to ``power_signal_dbm - 10`` if not provided.
    noise_sd : float
        Standard deviation of multiplicative Gaussian noise (default 0.1).
    output_csv : str or None
        If given, save ``(time, voltage)`` to this CSV path.

    Returns
    -------
    voltage : np.ndarray
        Simulated PDV voltage array, same length as ``time``.
    """
    sample_rate = 1.0 / (time[1] - time[0])

    f_tar = C_LIGHT / lambda_tar
    f_ref = C_LIGHT / lambda_ref

    if power_tar_dbm is None:
        power_tar_dbm = power_signal_dbm - 10
    E_ref0 = 10 ** (power_ref_dbm / 20)
    E_tar0 = 10 ** (power_tar_dbm / 20)
    E_s0   = 10 ** (power_signal_dbm / 20)

    position = np.cumsum(velocity / sample_rate)
    phase = 4 * np.pi * position / lambda_ref

    E_ref = E_ref0 * np.cos(2 * np.pi * f_ref * time)
    E_tar = E_tar0 * np.cos(2 * np.pi * f_tar * time)
    E_s   = E_s0   * np.cos(2 * np.pi * f_tar * time - phase)

    voltage = E_ref * E_s + E_ref * E_tar + E_tar * E_s
    voltage += voltage.max() * np.random.normal(0, noise_sd, voltage.size)

    if output_csv is not None:
        _save_waveform_csv(time, voltage, output_csv)

    return voltage


# ---------------------------------------------------------------------------
# Multi-point PDV synthesis
# ---------------------------------------------------------------------------

def velocity_to_multipoint_pdv_voltage(
    time,
    velocity,
    num_points=2,
    ref_lambdas_nm=None,
    tar_lambdas_nm=None,
    power_ref_dbm=8,
    power_signal_dbm=-10,
    power_tar_dbm=None,
    noise_sd=0.1,
    output_csv=None,
):
    """Convert a velocity-time history to a synthetic multi-point PDV voltage signal.

    Combines contributions from ``num_points`` independent PDV channels, each
    at a different wavelength pair, into a single composite voltage waveform.

    Parameters
    ----------
    time : np.ndarray
        Time array in seconds.
    velocity : np.ndarray
        Velocity array in m/s.
    num_points : int
        Number of PDV channels to synthesize (default 2).
    ref_lambdas_nm : array-like of float or None
        Reference wavelengths in **nm** for each channel.
        Default: ``[1531.116, 1537.397, 1543.730]``.
    tar_lambdas_nm : array-like of float or None
        Target (local oscillator) wavelengths in **nm** for each channel.
        Default: ``[1531.102, 1537.374, 1543.703]`` (3, 7, and 10 GHz below
        the respective reference frequencies).
    power_ref_dbm : float
        Reference power in dBm (default 8 dBm).
    power_signal_dbm : float
        Return signal (Doppler-shifted) power in dBm (default −10 dBm).
    power_tar_dbm : float or None
        Constant back-reflection (target output) power in dBm.
        Defaults to ``power_signal_dbm - 1`` if not provided.
    noise_sd : float
        Standard deviation of multiplicative Gaussian noise (default 0.1).
    output_csv : str or None
        If given, save ``(time, voltage_multi)`` to this CSV path.

    Returns
    -------
    voltage_multi : np.ndarray
        Composite multi-channel PDV voltage array, same length as ``time``.
    """
    if ref_lambdas_nm is None:
        ref_lambdas_nm = [1531.116, 1537.397, 1543.730]

    ref_lambdas = np.array(ref_lambdas_nm) * 1e-9
    ref_freqs   = C_LIGHT / ref_lambdas

    if tar_lambdas_nm is not None:
        tar_lambdas = np.array(tar_lambdas_nm) * 1e-9
        tar_freqs   = C_LIGHT / tar_lambdas
    else:
        # Default: 3, 7, 10 GHz below each reference frequency
        tar_freqs = ref_freqs - np.array([3, 7, 10]) * 1e9

    sample_rate = 1.0 / (time[1] - time[0])

    if power_tar_dbm is None:
        power_tar_dbm = power_signal_dbm - 1
    E_ref0 = 10 ** (power_ref_dbm / 20)
    E_tar0 = 10 ** (power_tar_dbm / 20)
    E_s0   = 10 ** (power_signal_dbm / 20)

    voltage_multi = np.zeros(len(time))

    for i in range(num_points):
        position = np.cumsum(velocity / sample_rate)
        phase = 4 * np.pi * position / ref_lambdas[i]
        phase_wrapped = np.remainder(phase, 2 * np.pi)

        E_ref = E_ref0 * np.cos(2 * np.pi * ref_freqs[i] * time)
        E_s   = E_s0   * np.cos(2 * np.pi * tar_freqs[i] * time - phase_wrapped)
        E_tar = E_tar0 * np.cos(2 * np.pi * tar_freqs[i] * time)

        voltage_multi += E_ref * E_s + E_ref * E_tar + E_s * E_tar

    voltage_multi *= 1 + np.random.normal(0, noise_sd, len(time))

    if output_csv is not None:
        _save_waveform_csv(time, voltage_multi, output_csv)

    return voltage_multi


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------

def _save_waveform_csv(time, voltage, filepath):
    """Write a two-column (time, voltage) CSV with high-precision formatting."""
    with open(filepath, "w", newline="") as fh:
        for t, v in zip(time, voltage):
            fh.write(f"{t:.9E},{v:.7E}\n")


def load_waveform_csv(filepath):
    """Load a two-column (time, voltage) CSV previously saved by this module.

    Returns
    -------
    time : np.ndarray
    voltage : np.ndarray
    """
    data = np.loadtxt(filepath, delimiter=",")
    return data[:, 0], data[:, 1]
