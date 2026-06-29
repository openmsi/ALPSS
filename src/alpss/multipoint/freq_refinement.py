import numpy as np
import pandas as pd
import io
from scipy.fft import fft, fftfreq


def find_carrier(filepath, freq_min, freq_max, sample_rate, time_to_skip,
                 carrier_band_time, header_lines, bytestring=None, data=None, **_):
    """Cheaply estimate the carrier frequency from the pre-signal window.

    Reads only ``carrier_band_time`` worth of samples starting at
    ``time_to_skip``, then finds the FFT peak within ``[freq_min, freq_max]``.
    This is far cheaper than a full ``alpss_main`` pass and produces the same
    carrier estimate that ``carrier_frequency`` would return on the same window.

    May also be useful for single-probe runs when wide initial bounds are needed
    to accommodate shot-to-shot carrier drift.

    Parameters
    ----------
    filepath : str
        Path to the raw CSV data file.
    freq_min, freq_max : float
        Wide frequency bounds (Hz) used for the initial search.
    sample_rate : float
        Nominal sample rate (Hz); used to compute row counts.
    time_to_skip : float
        Time (s) to skip from the start of the file — matches the main run.
    carrier_band_time : float
        Duration (s) of the pre-signal window to fit; matches the main run.
    header_lines : int
        Number of header rows in the CSV.
    bytestring : bytes, optional
        In-memory data source; used instead of ``filepath`` when provided.
    data : np.ndarray, optional
        Pre-loaded 2-column array ``[time, voltage]`` already windowed to
        ``time_to_skip``. When provided, skips all file I/O.

    Returns
    -------
    cen : float
        Carrier frequency (Hz).
    """
    t_step = 1 / sample_rate
    nrows = int(round(carrier_band_time / t_step))

    if data is not None:
        chunk = data[:nrows]
        time = chunk[:, 0]
        time = time - time[0]
        voltage = chunk[:, 1]
    else:
        rows_to_skip = header_lines + int(round(time_to_skip / t_step))
        if bytestring is not None and isinstance(bytestring, bytes):
            df = pd.read_csv(io.BytesIO(bytestring), skiprows=rows_to_skip, nrows=nrows, header=None)
        else:
            df = pd.read_csv(filepath, skiprows=rows_to_skip, nrows=nrows, header=None)
        time = df.iloc[:, 0].to_numpy()
        time = time - time[0]
        voltage = df.iloc[:, 1].to_numpy()

    fs = 1 / np.mean(np.diff(time))

    freq = fftfreq(int(fs * time[-1]) + 1, 1 / fs)
    freq2 = freq[: int(freq.shape[0] / 2) - 1]

    freq_min_idx = np.argmin(np.abs(freq2 - freq_min))
    freq_max_idx = np.argmin(np.abs(freq2 - freq_max))

    ampl = np.abs(fft(voltage))
    ampl2 = ampl[: int(freq.shape[0] / 2) - 1]

    freq3 = freq2[freq_min_idx:freq_max_idx]
    ampl3 = ampl2[freq_min_idx:freq_max_idx]

    cen = freq3[np.argmax(ampl3)]
    return cen