import numpy as np
from scipy.fft import fft, ifft, fftfreq
from scipy.fftpack import fftshift
from alpss.utils import stft
from scipy.optimize import curve_fit

# function to filter out the carrier frequency
def carrier_filter(sdf_out, cen, **inputs):
    # unpack dictionary values in to individual variables
    time = sdf_out["time"]
    voltage = sdf_out["voltage"]
    t_start_corrected = sdf_out["t_start_corrected"]
    fs = sdf_out["fs"]
    order = inputs["order"]
    wid = inputs["wid"]
    f_min = inputs["freq_min"]
    f_max = inputs["freq_max"]
    t_doi_start = sdf_out["t_doi_start"]
    t_doi_end = sdf_out["t_doi_end"]

    # get the index in the time array where the signal begins
    sig_start_idx = np.argmin(np.abs(time - t_start_corrected))

    # choose a filter type (currently gaussian notch and sine fit subtraction)
    if inputs["carrier_filter_type"] == 'gaussian_notch':
        # filter the data after the signal start time with a gaussian notch
        freq = fftshift(
            np.arange(-len(time[sig_start_idx:]) / 2, len(time[sig_start_idx:]) / 2)
            * fs
            / len(time[sig_start_idx:])
        )
        filt_2 = (
            1
            - np.exp(-((freq - cen) ** order) / wid**order)
            - np.exp(-((freq + cen) ** order) / wid**order)
        )
        voltage_filt = ifft(fft(voltage[sig_start_idx:]) * filt_2)

        # pair the filtered voltage from after the signal starts with the original data from before the signal starts
        voltage_filt = np.concatenate((voltage[0:sig_start_idx], voltage_filt))

        # parameters from the other filter type not needed
        time_fitting = 'none'
        time_domain_carrier = 'none'
        sin_fit = 'none'
        display_freq = 'none'
        display_vals = 'none'

    elif inputs["carrier_filter_type"] == 'sin_fit_subtract':
        t_fit_begin = inputs["t_fit_begin"]
        t_fit_end = inputs["t_fit_end"]
        all_freq = fftfreq(voltage.size,1/fs)
        tmin = t_fit_begin
        tmax = t_fit_end

        # perform FFT of carrier band from time tmin to tmax to determine find peaks from both carrier and dopplar signal
        carrier_analysis_time_mask = (time>(t_start_corrected + tmin)) & (time<(t_start_corrected + tmax))
        time_fitting = time[carrier_analysis_time_mask]
        fft_vals = fft(voltage[carrier_analysis_time_mask])
        freq = fftfreq(voltage[carrier_analysis_time_mask].size,1/fs)

        # extract out the carrier band peak using the already known frequency from the carrier_frequency function and the wid parameter
        mask_sin_fit = (freq>(cen-wid/2)) & (freq<(cen+wid/2))

        # the fft vals and frequencies corresponding to only the carrier peak
        fft_vals_masked = fft_vals[mask_sin_fit]
        fft_freq_masked = freq[mask_sin_fit]

        full_fft = np.zeros_like(fft_vals, dtype=complex)
        full_fft[mask_sin_fit] = fft_vals_masked

        # the corresponding time domain for the isolated carrier band
        time_domain_carrier = np.real(ifft(full_fft))

        # fit the time domain carrier band with a sine function
        def sin_func(x, a, b, c, d):
            return a * np.sin(2 * np.pi * b * x + c) + d

        try:
            # fit a sinusoid to the data
            popt, pcov = curve_fit(
                sin_func, time_fitting, time_domain_carrier, p0=[(np.max(time_domain_carrier) - np.min(time_domain_carrier)) / 2, cen, 0, 0]
            )
        except Exception:
            # if sin fitting doesn't work set the fitting parameters to be zeros
            popt = [0, 0, 0, 0]
            pcov = [0, 0, 0, 0]

        # the sinusoidal fit over the fitting time
        sin_fit = sin_func(time_fitting,*popt)

        # filter out any frequencies not in the user specified frequency bounds
        frequency_mask = (all_freq>f_min) & (all_freq<f_max)
        voltage_filt = ifft(fft(voltage)*frequency_mask).real

        # subtract the carrier band fit
        voltage_filt = voltage_filt - sin_func(time, *popt)

        # prepare the fft freqs and vals for plotting
        display_vals = fft_vals[freq>0]
        display_freq = freq[freq>0]
    elif inputs["carrier_filter_type"] == 'none': 
        voltage_filt = voltage
        time_fitting = 'none'
        time_domain_carrier = 'none'
        sin_fit = 'none'
        display_freq = 'none'
        display_vals = 'none'
    else:
        raise ValueError(f'Invalid carrier filter type: {inputs["carrier_filter_type"]}')

    # perform a stft on the filtered voltage data. Only the real part as to not get a two sided spectrogram
    f_filt, t_filt, Zxx_filt = stft(np.real(voltage_filt), fs, **inputs)

    # calculate the power
    power_filt = 10 * np.log10(np.abs(Zxx_filt) ** 2)

    # cut the data to the domain of interest
    f_min_idx = np.argmin(np.abs(f_filt - f_min))
    f_max_idx = np.argmin(np.abs(f_filt - f_max))
    t_doi_start_idx = np.argmin(np.abs(t_filt - t_doi_start))
    t_doi_end_idx = np.argmin(np.abs(t_filt - t_doi_end))
    Zxx_filt_doi = Zxx_filt[f_min_idx:f_max_idx, t_doi_start_idx:t_doi_end_idx]
    power_filt_doi = power_filt[f_min_idx:f_max_idx, t_doi_start_idx:t_doi_end_idx]

    # save outputs to a dictionary
    cf_out = {
        "voltage_filt": voltage_filt,
        "f_filt": f_filt,
        "t_filt": t_filt,
        "Zxx_filt": Zxx_filt,
        "power_filt": power_filt,
        "Zxx_filt_doi": Zxx_filt_doi,
        "power_filt_doi": power_filt_doi,
    }

    return cf_out
