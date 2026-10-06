"""
ALPSS
Jake Diamond (2024)
Johns Hopkins University
Hopkins Extreme Materials Institute (HEMI)
Please report any bugs or comments to jdiamo15@jhu.edu


Key for input variables:
filename:                   str; filename for the data to run
save_data:                  bool; True to save output data, False to skip
spall_enabled:          bool; True to perform spall analysis, False to skip
hel_enabled:            bool; True to perform HEL detection, False to skip
start_time_user:            str or float; if 'none' the program will attempt to find the
                                             signal start time automatically. if float then
                                             the program will use that as the signal start time
header_lines:               int; number of header lines to skip in the data file
time_to_skip:               float; the amount of time to skip in the full data file before beginning to read in data
time_to_take:               float; the amount of time to take in the data file after skipping time_to_skip
t_before:                   float; amount of time before the signal start time to include in the velocity calculation
t_after:                    float; amount of time after the signal start time to include in the velocity calculation
start_time_correction:      float; amount of time to adjust the signal start time by
freq_min:                   float; minimum frequency for the region of interest
freq_max:                   float; maximum frequency for the region of interest
smoothing_window:           int; number of points to use for the smoothing window. must be an odd number
smoothing_wid:              float; half the width of the normal distribution used
                                   to calculate the smoothing weights (recommend 3)
smoothing_amp:              float; amplitude of the normal distribution used to calculate
                                   the smoothing weights (recommend 1)
smoothing_sigma:            float; standard deviation of the normal distribution used
                                   to calculate the smoothing weights (recommend 1)
smoothing_mu:               float; mean of the normal distribution used to calculate
                                   the smoothing weights (recommend 0)
pb_neighbors:               int; number of neighbors to compare to when searching
                                     for the pullback local minimum
pb_idx_correction:          int; number of local minima to adjust by if the program grabs the wrong one
rc_neighbors:               int; number of neighbors to compare to when searching
                                     for the recompression local maximum
rc_idx_correction:          int; number of local maxima to adjust by if the program grabs the wrong one
sample_rate:                float; sample rate of the oscilloscope used in the experiment
nperseg:                    int; number of points to use per segment of the stft
noverlap:                   int; number of points to overlap per segment of the stft
nfft:                       int; number of points to zero pad per segment of the stft
window:                     str or tuple or array_like; window function to use for the stft (recommend 'hann')
blur_kernel:                tuple; kernel size for gaussian blur smoothing (recommend (5, 5))
blur_sigx:                  float; standard deviation of the gaussian blur kernel in the x direction (recommend 0)
blur_sigy:                  float; standard deviation of the gaussian blur kernel in the y direction (recommend 0)
carrier_band_time:          float; length of time from the beginning of the imported data window to average
                                   the frequency of the top of the carrier band in the thresholded spectrogram
cmap:                       str; colormap for the spectrograms (recommend 'viridis')
uncert_mult:                float; factor to multiply the velocity uncertainty by when plotting - allows for easier
                                   visulaization when uncertainties are small
order:                      int; order for the gaussian notch filter used to remove the carrier band (recommend 6)
wid:                        float; width of the gaussian notch filter used to remove the carrier band (recommend 1e8)
lam:                        float; wavelength of the target laser
C0:                         float; bulk wavespeed of the sample
density:                    float; density of the sample
delta_rho:                  float; uncertainty in density of the sample
delta_C0:                   float; uncertainty in the bulk wavespeed of the sample
delta_lam:                  float; uncertainty in the wavelength of the target laser
theta:                      float; angle of incidence of the PDV probe
delta_theta:                float; uncertainty in the angle of incidence of the PDV probe
exp_data_dir:               str; directory from which to read the experimental data file
out_files_dir:              str; directory to save output data to
display_plots:              bool; True to display the final plots, False to skip. if save_data=True
                                     and display_plots=False the plots will be saved but not displayed
plot_figsize:               tuple; figure size for the final plots
plot_dpi:                   float; dpi for the final plots
"""

# %%
from alpss_main import *
import os


config = {
    "io": {
        "filename": "example_file.csv",
        "save_data": True,
        "display_plots": True,
        "header_lines": 0,
        "time_to_skip": 0e-6,
        "time_to_take": 10e-6,
        "out_files_dir": "/srv/hemi01-j01/ALPSS/tests/output_data2",
    },
    "start_time": {
        "start_time_user": "none",
        "start_time_correction": 0e-9,
        "t_before": 10e-9,
        "t_after": 200e-9,
        "carrier_band_time": 250e-9,
        "iq_threshold_factor": 0.4,
        "cusum_offset": 5,
        "cusum_threshold": 1000,
        "freq_offset": 0.5e9,
    },
    "stft": {
        "sample_rate": 128e9,
        "nperseg": 512,
        "noverlap": 435,
        "nfft": 5120,
        "window": "hann",
        "freq_min": 1e9,
        "freq_max": 5e9,
        "blur_kernel": (5, 5),
        "blur_sigx": 0,
        "blur_sigy": 0,
    },
    "carrier": {
        "carrier_filter_type": "gaussian_notch",
        "order": 6,
        "wid": 15e7,
        "t_fit_begin": 20,
        "t_fit_end": 300,
    },
    "velocity": {
        "smoothing_window": 1001,
        "smoothing_wid": 3,
        "smoothing_amp": 1,
        "smoothing_sigma": 1,
        "smoothing_mu": 0,
        "lam": 1550.016e-9,
        "theta": 0,
    },
    "material": {
        "C0": 4540,
        "density": 1730,
        "delta_rho": 9,
        "delta_C0": 23,
        "delta_lam": 8e-18,
        "delta_theta": 5,
    },
    "spall": {
        "spall_enabled": True,
        "pb_neighbors": 400,
        "pb_idx_correction": 0,
        "rc_neighbors": 400,
        "rc_idx_correction": 0,
    },
    "hel": {
        "hel_enabled": True,
        "hel_start_time_ns": 0.0,
        "hel_end_time_ns": 30.0,
        "hel_angle_threshold_deg": 45.0,
        "hel_detection_min_points": 3,
        "minimum_HEL_velocity_expected": 10.0,
    },
    "uncertainty": {
        "uncert_mult": 100,
    },
    "plotting": {
        "cmap": "viridis",
        "plot_figsize": (30, 10),
        "plot_dpi": 300,
    },
}

alpss_main(**config)

# %%
