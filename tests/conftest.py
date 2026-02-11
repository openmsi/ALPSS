import pytest
import os

@pytest.fixture
def config_file_path():
    """Fixture to provide the path to the test config file."""
    return os.path.join(os.path.dirname(__file__), "input_data", "config.json")


@pytest.fixture
def valid_inputs():

    base_dir = os.path.dirname(__file__)  # Get the directory of conftest.py
    filepath = os.path.join(base_dir, "input_data", "example_file.csv")
    out_files_dir = os.path.join(base_dir, "output_data")

    return {
        "filepath": filepath,
        "out_files_dir": out_files_dir,
        "save_data": "yes",
        "start_time_user": "otsu",
        "carrier_filter_type": "gaussian_notch",
        "display_plots": "no",
        "spall_calculation": "yes",
        "window": "hann",
        "cmap": "viridis",
        "header_lines": 1,
        "time_to_skip": 2.3e-06,
        "time_to_take": 1.5e-06,
        "t_before": 5e-09,
        "t_after": 5e-08,
        "start_time_correction": 0.0,
        "freq_min": 1500000000.0,
        "freq_max": 4000000000.0,
        "smoothing_window": 601,
        "smoothing_wid": 3,
        "smoothing_amp": 1,
        "smoothing_sigma": 1,
        "smoothing_mu": 0,
        "pb_neighbors": 400,
        "pb_idx_correction": 0,
        "rc_neighbors": 400,
        "rc_idx_correction": 0,
        "sample_rate": 80000000000.0,
        "nperseg": 512,
        "noverlap": 435,
        "nfft": 5120,
        "blur_kernel": (5, 5),
        "blur_sigx": 0,
        "blur_sigy": 0,
        "carrier_band_time": 2.5e-07,
        "uncert_mult": 100,
        "order": 6,
        "wid": 50000000.0,
        "lam": 1.547461e-06,
        "C0": 4540,
        "density": 1730,
        "delta_rho": 9,
        "delta_C0": 23,
        "delta_lam": 8e-18,
        "theta": 0,
        "delta_theta": 5,
        "plot_figsize": (80, 40),
        "plot_dpi": 300,
        "iq_threshold_factor": 0.4,
        "cusum_offset": 5,
        "cusum_threshold": 1000,
        "t_fit_begin": 20,
        "t_fit_end": 300
    }

@pytest.fixture
def expected_values():
    """Fixture to provide the expected values for ALPSS tests."""
    return {
        "Velocity at Max Compression": 828.0849443007512,
        "Time at Max Compression": 6.300750500023988e-07,
        "Velocity at Max Tension": 464.46467142515036,
        "Time at Max Tension": 6.476500600052781e-07,
        "Velocity at Recompression": 574.0505816377753,
        "Time at Recompression": 6.557375600013682e-07,
        "Carrier Frequency": 2232111412.128054,
        "Spall Strength": 1427973173.609772,
        "Spall Strength Uncertainty": 10692214.866814513,
        "Strain Rate": 2278592.4760455955,
        "Strain Rate Uncertainty": 537339.1422056587,
        "Peak Shock Stress": 3251972384.76348,
        "Spect Time Res": 9.625000834177745e-10,
        "Spect Freq Res": 15624998.645815466,
        "Spect Velocity Res": 12.089538014726124,
        "Signal Start Time": 6.140750532205402e-07,
        "Smoothing Characteristic Time": 2.9298752539258723e-09,
    }


# Expected values per (start_time_user, carrier_filter_type) configuration.
# Configs that produce NaN spall values or fail entirely are excluded.
EXPECTED_VALUES_MAP = {
    ("otsu", "gaussian_notch"): {
        "Velocity at Max Compression": 828.0849443007512,
        "Time at Max Compression": 6.300750500023988e-07,
        "Velocity at Max Tension": 464.46467142515036,
        "Time at Max Tension": 6.476500600052781e-07,
        "Velocity at Recompression": 574.0505816377753,
        "Time at Recompression": 6.557375600013682e-07,
        "Carrier Frequency": 2232111412.128054,
        "Spall Strength": 1427973173.609772,
        "Spall Strength Uncertainty": 10692214.866814513,
        "Strain Rate": 2278592.4760455955,
        "Strain Rate Uncertainty": 537339.1422056587,
        "Peak Shock Stress": 3251972384.76348,
        "Spect Time Res": 9.625000834177745e-10,
        "Spect Freq Res": 15624998.645815466,
        "Spect Velocity Res": 12.089538014726124,
        "Signal Start Time": 6.140750532205402e-07,
        "Smoothing Characteristic Time": 2.9298752539258723e-09,
    },
    ("iq", "gaussian_notch"): {
        "Carrier Frequency": 2232111412.128054,
        "Spect Time Res": 9.625000834177745e-10,
        "Spect Freq Res": 15624998.645815466,
        "Spect Velocity Res": 12.089538014726124,
        "Signal Start Time": 5.491375500016327e-07,
        "Smoothing Characteristic Time": 2.9298752539258723e-09,
    },
    (7.5e-07, "gaussian_notch"): {
        "Velocity at Max Compression": 370.87498646489956,
        "Time at Max Compression": 7.764375700020087e-07,
        "Velocity at Max Tension": 349.1322320253391,
        "Time at Max Tension": 7.814750700024797e-07,
        "Velocity at Recompression": 357.67960343266185,
        "Time at Recompression": 7.926625700052647e-07,
        "Carrier Frequency": 2232111412.128054,
        "Spall Strength": 85385970.95959799,
        "Spall Strength Uncertainty": 41690593.07354747,
        "Strain Rate": 475350.169707975,
        "Strain Rate Uncertainty": 454678.9510147054,
        "Peak Shock Stress": 1456463159.346307,
        "Spect Time Res": 9.625000834177745e-10,
        "Spect Freq Res": 15624998.645815466,
        "Spect Velocity Res": 12.089538014726124,
        "Signal Start Time": 7.497875649824463e-07,
        "Smoothing Characteristic Time": 2.9298752539258723e-09,
    },
    ("otsu", "none"): {
        "Velocity at Max Compression": 828.3958998105065,
        "Time at Max Compression": 6.301375500006312e-07,
        "Velocity at Max Tension": 2.5169905105239074,
        "Time at Max Tension": 6.499375600002577e-07,
        "Velocity at Recompression": 572.6800635718317,
        "Time at Recompression": 6.561750600028726e-07,
        "Carrier Frequency": 2232111412.128054,
        "Spall Strength": 3243309064.7119617,
        "Spall Strength Uncertainty": 23599274.85110015,
        "Strain Rate": 4593726.317165109,
        "Strain Rate Uncertainty": 961594.8472264492,
        "Peak Shock Stress": 3253193538.14584,
        "Spect Time Res": 9.625000834177745e-10,
        "Spect Freq Res": 15624998.645815466,
        "Spect Velocity Res": 12.089538014726124,
        "Signal Start Time": 6.140750532205402e-07,
        "Smoothing Characteristic Time": 2.9298752539258723e-09,
    },
}
