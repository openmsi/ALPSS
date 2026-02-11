import numpy as np
from scipy.fft import (fft, fftfreq)


# calculate the carrier frequency as the frequency with the max amplitude within the frequency range of interest
# specified in the user inputs
def carrier_frequency(spall_doi_finder_outputs, **inputs):

    # unpack dictionary values in to individual variables
    fs = spall_doi_finder_outputs['fs']
    time = spall_doi_finder_outputs['time']
    voltage = spall_doi_finder_outputs['voltage']
    freq_min = inputs['freq_min']
    freq_max = inputs['freq_max']

    # cut the time and voltage signals to only take the time during the user input "carrier_band_time".
    # That way there is none of the actual target signal in the FFT.
    # Need this because in some instances the target signal is stronger than the carrier, in which case the target signal may end up being filtered out.
    # These two lines of code should prevent that from happening and make sure the carrier is filtered properly.
    time = time[: int(round(inputs["carrier_band_time"] * fs))]
    voltage = voltage[: int(round(inputs["carrier_band_time"] * fs))]

    # calculate frequency values for fft
    freq = fftfreq(int(fs * time[-1]) + 1, 1 / fs)
    freq2 = freq[:int(freq.shape[0] / 2) - 1]

    # find the frequency indices that mark the range of interest
    freq_min_idx = np.argmin(np.abs(freq2 - freq_min))
    freq_max_idx = np.argmin(np.abs(freq2 - freq_max))

    # find the amplitude values for the fft
    ampl = np.abs(fft(voltage))
    ampl2 = ampl[:int(freq.shape[0] / 2) - 1]

    # cut the frequency and amplitude to the range of interest
    freq3 = freq2[freq_min_idx: freq_max_idx]
    ampl3 = ampl2[freq_min_idx: freq_max_idx]

    # find the carrier as the frequency with the max amplitude
    cen = freq3[np.argmax(ampl3)]

    # return the carrier frequency
    return cen
