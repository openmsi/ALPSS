import numpy as np
import cv2 as cv
from alpss.utils import stft
import logging
from scipy import signal
from scipy.fft import fft, fftfreq
import matplotlib.pyplot as plt
import os

# function to find the specific domain of interest in the larger signal
def spall_doi_finder(data, **inputs):

    # rename the columns of the data
    data.columns = ["Time", "Ampl"]

    # put the data into numpy arrays. Zero the time data
    time = data["Time"].to_numpy()
    time = time - time[0]
    voltage = data["Ampl"].to_numpy()

    # calculate the true sample rate from the experimental data
    fs = 1 / np.mean(np.diff(time))

    # calculate the short time fourier transform
    f, t, Zxx = stft(voltage, fs, **inputs)

    # calculate magnitude of Zxx
    mag = np.abs(Zxx)

    # calculate the time and frequency resolution of the transform
    t_res = np.mean(np.diff(t))
    f_res = np.mean(np.diff(f))

    # find the index of the minimum and maximum frequencies as specified in the user inputs
    freq_min_idx = np.argmin(np.abs(f - inputs["freq_min"]))
    freq_max_idx = np.argmin(np.abs(f - inputs["freq_max"]))

    # cut the magnitude and frequency arrays to smaller ranges
    mag_cut = mag[freq_min_idx:freq_max_idx, :]
    f_doi = f[freq_min_idx:freq_max_idx]

    # calculate spectrogram power
    power_cut = 10 * np.log10(mag_cut**2)

    # convert spectrogram powers to uint8 for image processing
    smin = np.min(power_cut)
    smax = np.max(power_cut)
    a = 255 / (smax - smin)
    b = 255 - a * smax
    power_gray = a * power_cut + b
    power_gray8 = power_gray.astype(np.uint8)

    # blur using a gaussian filter
    blur = cv.GaussianBlur(
        power_gray8, inputs["blur_kernel"], inputs["blur_sigx"], inputs["blur_sigy"]
    )

    # automated thresholding using Otsu's binarization
    ret3, th3 = cv.threshold(blur, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)

    # if not using a user input value for the signal start time
    # if inputs["start_time_user"] == "none":
    def is_a_float(x):
        try:
            float(x)
            return True
        except (TypeError, ValueError):
            return False

    # start_time_user is either a float for manual search, or a string determining the algorithm to find t_start_detected
    if not is_a_float(inputs.get("start_time_user")): 
        if inputs.get('start_time_user') == "otsu":
            # Find the position/row of the top of the binary spectrogram for each time/column
            col_len = th3.shape[1]  # number of columns
            row_len = th3.shape[0]  # number of columns
            top_line = np.zeros(col_len)  # allocate space to place the indices
            f_doi_top_line = np.zeros(
                col_len
            )  # allocate space to place the corresponding frequencies

            for col_idx in range(col_len):  # loop over every column
                for row_idx in range(row_len):  # loop over every row
                    # moving from the top down, if the pixel is 255 then store the index and break to move to the next column
                    idx_top = row_len - row_idx - 1

                    if th3[idx_top, col_idx] == 255:
                        top_line[col_idx] = idx_top
                        f_doi_top_line[col_idx] = f_doi[idx_top]
                        break

            # if the signal completely drops out there will be elements of f_doi_top_line equal to zero - these points are
            # made NaNs. Same for top_line.
            f_doi_top_line_clean = f_doi_top_line.copy()
            f_doi_top_line_clean[np.where(top_line == 0)] = np.nan
            top_line_clean = top_line.copy()
            top_line_clean[np.where(top_line == 0)] = np.nan

            # find the index of t where the time is closest to the user input carrier_band_time
            carr_idx = np.argmin(np.abs(t - inputs["carrier_band_time"]))

            # calculate the average frequency of the top of the carrier band during carrier_band_time
            f_doi_carr_top_avg = np.mean(f_doi_top_line_clean[:carr_idx])

            # find the index in f_doi that is closest in frequency to f_doi_carr_top_avg
            f_doi_carr_top_idx = np.argmin(np.abs(f_doi - f_doi_carr_top_avg))

            # work backwards from the highest point on the signal top line until it matches or dips below f_doi_carr_top_idx
            highest_idx = np.argmax(f_doi_top_line_clean)
            for check_idx in range(highest_idx):
                cidx = highest_idx - check_idx - 1
                if top_line_clean[cidx] <= f_doi_carr_top_idx:
                    break
            
            # add in the user correction for the start time
            t_start_detected = t[cidx]
        elif inputs.get('start_time_user') == "iq":
            t_start_detected_iq, amplitude, phase = iq_analysis(inputs, voltage, fs, time)

            carr_idx = np.nan
            f_doi_carr_top_idx = np.nan
            f_doi_top_line_clean = np.nan
            
            t_start_detected = t_start_detected_iq
        elif inputs["start_time_user"]=="cusum": 

            # Collect necessary parameters
            carrier_band_time = inputs["carrier_band_time"]
            k=inputs["cusum_offset"]
            h=inputs["cusum_threshold"]

            # Carrier band Frequency
            carrier_mask = time < carrier_band_time
            carrier_fft_vals = fft(voltage[carrier_mask])
            carrier_fft_freqs = fftfreq(voltage[carrier_mask].size,1/fs)
            mask3 = carrier_fft_freqs > 0
            max_idx = np.argmax(np.abs(carrier_fft_vals*mask3))
            cen = carrier_fft_freqs[max_idx]
            idx = np.argmin(np.abs(f-cen))
            signal = mag[idx,:]
            mask4 = t < carrier_band_time
            mask5 = t > (t.max()-carrier_band_time)
            mu0 = np.mean(signal[mask4])
            mu1 =  0  # Expected post-change signal level
            sigma0 = np.var(signal[mask4])

            print('signal shape: ', signal.shape)
            detection_indices, change_indices, G, s = cusum(signal, mu0, mu1, sigma0, h, k)

            print("change _indices shape: ", change_indices.shape)
            detection_time = t[change_indices]

            # these params become nan because they are only needed if the program
            # is finding the signal start time automatically
            f_doi_top_line_clean = np.nan
            carr_idx = np.nan
            f_doi_carr_top_idx = np.nan

            # use the user input signal start time to define the domain of interest
            t_start_detected = detection_time
        else:
            raise TypeError(f"invalid mode assigned to variable 'start_time_user': {inputs.get('start_time_user')}")

    # if using a user input for the signal start time
    else:
        # these params become nan because they are only needed if the program
        # is finding the signal start time automatically
        f_doi_top_line_clean = np.nan
        carr_idx = np.nan
        f_doi_carr_top_idx = np.nan

        # use the user input signal start time to define the domain of interest
        t_start_detected = t[np.argmin(np.abs(t - inputs["start_time_user"]))]

    t_start_corrected = t_start_detected + float(inputs["start_time_correction"])
    t_doi_start = t_start_corrected - float(inputs["t_before"])
    t_doi_end = t_start_corrected + float(inputs["t_after"])

    t_doi_start_spec_idx = np.argmin(np.abs(t - t_doi_start))
    t_doi_end_spec_idx = np.argmin(np.abs(t - t_doi_end))
    mag_doi = mag_cut[:, t_doi_start_spec_idx:t_doi_end_spec_idx]
    power_doi = 10 * np.log10(mag_doi**2)

    # dictionary to return outputs
    sdf_out = {
        "time": time,
        "voltage": voltage,
        "fs": fs,
        "f": f,
        "t": t,
        "Zxx": Zxx,
        "t_res": t_res,
        "f_res": f_res,
        "f_doi": f_doi,
        "mag": mag,
        "th3": th3,
        "carr_idx": carr_idx,
        "f_doi_carr_top_idx": f_doi_carr_top_idx,
        "t_start_detected": t_start_detected,
        "t_start_corrected": t_start_corrected,
        "t_doi_start": t_doi_start,
        "t_doi_end": t_doi_end,
        "power_doi": power_doi,
        "start_time_user": inputs.get('start_time_user')
    }

    if inputs.get('start_time_user') == "iq":
        sdf_out['amplitude'] = amplitude
        sdf_out['phase'] = phase

    return sdf_out


def cusum(signal, mu0, mu1, sigma, h, k):
    """
    Detect a single mean shift from mu0 to mu1 using CUSUM.
    Returns:
    - Detection index
    - Estimated change point index
    - Full G[k] array
    """
    # Score for general mean change
    Z = (signal - mu0)/(np.sqrt(sigma))
    s = -Z - k
    # s = ((mu1 - mu0) / sigma) * (signal - mu0) - ((mu0**2 - mu1**2) / (2 * sigma))
    G = np.zeros_like(s)

    for k in range(1, len(s)):
        G[k] = max(G[k-1] + s[k], 0)

        if G[k] > h:
            detect_idx = k
            S = np.cumsum(s[:detect_idx])
            change_idx = np.argmin(S)
            return detect_idx, change_idx, G, s

    # If no change detected
    return None, None, G, s

def iq_analysis(inputs, voltage, fs, time):
    # Extract carrier frequency from input data
    N = len(voltage)
    fft_result = np.fft.fft(voltage)
    freq = np.fft.fftfreq(N, 1/fs)
    positive_freq_mask = freq > 0
    positive_freq = freq[positive_freq_mask]
    positive_fft = np.abs(fft_result[positive_freq_mask])

    # Find the frequency with maximum amplitude within the specified range
    freq_range_mask = (positive_freq >= inputs["freq_min"]) & (positive_freq <= inputs["freq_max"])
    carrier_idx = np.argmax(positive_fft[freq_range_mask])
    carrier_frequency = positive_freq[freq_range_mask][carrier_idx]

    logging.info(f"Extracted carrier frequency during IQ analysis: {carrier_frequency} Hz")
    
    # Demodulate signal
    I = voltage * np.cos(2 * np.pi * carrier_frequency * time)
    Q = voltage * np.sin(2 * np.pi * carrier_frequency * time)

    # Apply Gaussian smoothing with skip points
    skip_points = 100 # skipping initial points to avoid IQ analysis induced signal drop
    window_length = 801
    window = np.exp(-0.5 * (np.arange(0, window_length) - (window_length - 1.0) / 2.0) / 10**2)
    I_smooth = signal.convolve(I, window, mode='same')[skip_points:] / sum(window)
    Q_smooth = signal.convolve(Q, window, mode='same')[skip_points:] / sum(window)
    
    # Calculate amplitude and phase
    amplitude = np.sqrt(I_smooth**2 + Q_smooth**2)
    phase = np.unwrap(np.arctan2(Q_smooth, I_smooth))

    # Find initial stable amplitude
    initial_amplitude = np.mean(amplitude[:int(len(amplitude)/4.5)])

    # Allow user-defined threshold factor via inputs; default to existing 0.4
    iq_threshold_factor = inputs['iq_threshold_factor']
    threshold = iq_threshold_factor * initial_amplitude
    
    # Detect start time using 50% amplitude drop
    start_index = np.where(amplitude < threshold)[0][0]
    t_start_detected_iq = time[start_index]

    # After calculating amplitude, adjust time array to match
    time_adjusted = time[skip_points:skip_points+len(amplitude)]

    # Convert amplitude to mV and time to microseconds
    amplitude_mV = amplitude * 1e3
    time_us = time_adjusted * 1e6

    ###### Plot with matched array lengths and square aspect ratio
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))
    ax1.plot(time_us, amplitude_mV, label='Complex Amplitude')
    
    # Create the actual step function used for detection
    # Before start time: amplitude is above threshold (normal)
    # After start time: amplitude drops below threshold (detected)
    step_function = np.where(time_us < t_start_detected_iq * 1e6, initial_amplitude * 1e3, threshold * 1e3)
    ax1.plot(time_us, step_function, 'r--', linewidth=2, label='Detection Threshold')
    ax1.axhline(y=threshold * 1e3, color='orange', linestyle=':', alpha=0.7, label=f'Threshold ({threshold*1e3:.1f} mV)')
    ax1.axvline(x=t_start_detected_iq * 1e6, color='red', linestyle='-', linewidth=2, 
                label=f'Start Time (IQ): {t_start_detected_iq*1e6:.1f} μs')
    ax1.set_ylabel('Amplitude (mV)', fontsize=20)
    ax1.set_xlabel('Time (μs)', fontsize=20)
    ax1.legend(fontsize=12)
    ax1.tick_params(axis='both', labelsize=20)

    # Save IQ amplitude plot as a separate figure (only if plots are enabled)
    save_all_plots = inputs.get("save_all_plots", "yes")
    save_in_subfolder = inputs.get("save_plots_in_subfolder", True)
    save_iq_start_time_plot = inputs.get('save_iq_start_time_plot', True)
    
    if save_all_plots == "yes" and save_iq_start_time_plot:
        if save_in_subfolder:
            # Create subfolder for this file's plots
            base_filename = os.path.basename(inputs["filepath"])
            name_without_ext, _ = os.path.splitext(base_filename)
            plots_subfolder = os.path.join(inputs["out_files_dir"], f"{name_without_ext}_plots")
            os.makedirs(plots_subfolder, exist_ok=True)
            plot_dir = plots_subfolder
        else:
            # Save plots in main output directory
            plot_dir = inputs["out_files_dir"]
        
        # fname_prefix = os.path.splitext(inputs.get('filepath'))[0]
        fig_iq, ax_iq = plt.subplots(figsize=(10, 6))
        ax_iq.plot(time_us, amplitude_mV, label='Complex Amplitude', linewidth=1.5)
        
        # Create the actual step function used for detection
        # Before start time: amplitude is above threshold (normal)
        # After start time: amplitude drops below threshold (detected)
        step_function = np.where(time_us < t_start_detected_iq * 1e6, initial_amplitude * 1e3, threshold * 1e3)
        ax_iq.plot(time_us, step_function, 'r--', linewidth=2, label='Detection Step Function')
        ax_iq.axhline(y=threshold * 1e3, color='orange', linestyle=':', alpha=0.7, linewidth=2, 
                    label=f'Detection Threshold ({threshold*1e3:.1f} mV)')
        ax_iq.axvline(x=t_start_detected_iq * 1e6, color='red', linestyle='-', linewidth=3, 
                    label=f'Start Time Detected: {t_start_detected_iq*1e6:.1f} μs')
        
        ax_iq.set_ylabel('Amplitude (mV)', fontsize=16)
        ax_iq.set_xlabel('Time (μs)', fontsize=16)
        ax_iq.set_title('IQ Analysis: Start Time Detection', fontsize=18, fontweight='bold')
        ax_iq.legend(fontsize=12, loc='upper right')
        ax_iq.tick_params(axis='both', labelsize=14)
        ax_iq.grid(True, alpha=0.3)
        plt.tight_layout()
        if inputs['save_data'] == "yes":
            fig_iq.savefig(os.path.join(plot_dir, f"{name_without_ext}-IQ_start_time_detection.png"), dpi=inputs.get('plot_dpi', 300), format='png', facecolor='w')
        plt.close(fig_iq)

    # Adjust phase plotting similarly
    ax2.plot(time_us, phase, label='Phase', color='green')
    ax2.set_xlabel('Time (μs)', fontsize=20)
    ax2.set_ylabel('Phase (radians)', fontsize=20)
    ax2.legend(fontsize=12)
    ax2.tick_params(axis='both', labelsize=20)
    plt.tight_layout()

    return t_start_detected_iq, amplitude, phase