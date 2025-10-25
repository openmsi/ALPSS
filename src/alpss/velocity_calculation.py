from scipy.fft import fft
from scipy.fft import ifft
from scipy.fftpack import fftshift
from alpss.num_derivative import *
from alpss.smoothing import *


# function to calculate the velocity from the filtered voltage signal
def velocity_calculation(
    spall_doi_finder_outputs, cen, carrier_filter_outputs, **inputs
):
    # unpack dictionary values in to individual variables
    fs = spall_doi_finder_outputs["fs"]
    time = spall_doi_finder_outputs["time"]
    voltage_filt = carrier_filter_outputs["voltage_filt"]
    freq_min = inputs["freq_min"]
    freq_max = inputs["freq_max"]
    lam = inputs["lam"]
    t_doi_start = spall_doi_finder_outputs["t_doi_start"]
    t_doi_end = spall_doi_finder_outputs["t_doi_end"]

    # isolate signal. filter out all frequencies that are outside the range of interest
    numpts = len(time)
    freq = fftshift(np.arange((-numpts / 2), (numpts / 2)) * fs / numpts)
    filt = (freq > freq_min) * (freq < freq_max)
    voltage_filt = ifft(fft(voltage_filt) * filt)

    # get the indices in the time array closest to the domain start and end times
    time_start_idx = np.argmin(np.abs(time - t_doi_start))
    time_end_idx = np.argmin(np.abs(time - t_doi_end))

    # unwrap the phase angle of the filtered voltage signal
    phas = np.unwrap(np.angle(voltage_filt), axis=0)

    # take the numerical derivative using the certral difference method with a 9-point stencil
    # return the derivative on the domain of interest (dpdt) as well as the padded derivative to be used for smoothing
    dpdt, dpdt_pad = num_derivative(
        phas, inputs["smoothing_window"], time_start_idx, time_end_idx, fs
    )

    # convert the derivative in to velocity
    # PDV Free-Surface Velocity Formula (matching HELIX):
    # v(t) = λ · (dφ/dt − f_center)
    # Note: This differs from standard backscatter PDV formula (λ/2); likely due to homodyne detection setup
    velocity_pad = lam * (dpdt_pad - cen)
    velocity_f = lam * (dpdt - cen)

    # crop the time array
    time_f = time[time_start_idx:time_end_idx]

    # smooth the padded velocity signal using a moving average with gaussian weights
    velocity_f_smooth = smoothing(
        velocity_pad=velocity_pad,
        smoothing_window=inputs["smoothing_window"],
        smoothing_wid=inputs["smoothing_wid"],
        smoothing_amp=inputs["smoothing_amp"],
        smoothing_sigma=inputs["smoothing_sigma"],
        smoothing_mu=inputs["smoothing_mu"],
    )
    
    # Remove baseline DC offset (mean of first 5% of signal)
    # This is standard PDV practice to remove carrier band offset
    baseline_idx = max(int(len(velocity_f_smooth) * 0.05), 5)
    baseline_offset = np.mean(velocity_f_smooth[:baseline_idx])
    
    velocity_f_smooth = velocity_f_smooth - baseline_offset
    velocity_f = velocity_f - baseline_offset
    velocity_pad = velocity_pad - baseline_offset

    # return a dictionary of the outputs
    vc_out = {
        "time_f": time_f,
        "velocity_f": velocity_f,
        "velocity_f_smooth": velocity_f_smooth,
        "phasD2_f": dpdt,
        "voltage_filt": voltage_filt,
        "time_start_idx": time_start_idx,
        "time_end_idx": time_end_idx,
    }

    return vc_out
