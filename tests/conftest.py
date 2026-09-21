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
    os.makedirs(out_files_dir, exist_ok=True)

    return {
        "io": {
            "filepath": filepath,
            "out_files_dir": out_files_dir,
            "header_lines": 1,
            "time_to_skip": 2.3e-06,
            "time_to_take": 1.5e-06,
            "save_data": True,
            "display_plots": False,
        },
        "stft": {
            "sample_rate": 80000000000.0,
            "nperseg": 512,
            "noverlap": 435,
            "nfft": 5120,
            "window": "hann",
            "freq_min": 1500000000.0,
            "freq_max": 4000000000.0,
            "blur_kernel": (5, 5),
            "blur_sigx": 0,
            "blur_sigy": 0,
        },
        "start_time": {
            "start_time_user": "otsu",
            "start_time_correction": 0.0,
            "t_before": 5e-09,
            "t_after": 5e-08,
            "iq_threshold_factor": 0.4,
            "cusum_offset": 5,
            "cusum_threshold": 1000,
            "carrier_band_time": 2.5e-07,
        },
        "carrier": {
            "carrier_filter_type": "gaussian_notch",
            "order": 6,
            "wid": 50000000.0,
            "t_fit_begin": 20,
            "t_fit_end": 300,
        },
        "velocity": {
            "smoothing_window": 601,
            "smoothing_wid": 3,
            "smoothing_amp": 1,
            "smoothing_sigma": 1,
            "smoothing_mu": 0,
            "lam": 1.547461e-06,
            "theta": 0,
            "min_velocity_threshold": 25,
            "max_velocity_uncertainty_threshold": 10,
        },
        "material": {
            "C0": 4540,
            "density": 1730,
            "delta_rho": 9,
            "delta_C0": 23,
            "delta_lam": 8e-18,
            "delta_theta": 5,
            "C_L": 4540,
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
            "plot_figsize": (80, 40),
            "plot_dpi": 300,
        },
    }


@pytest.fixture
def expected_values():
    """Fixture to provide the expected values for ALPSS tests."""
    return {
        "Velocity at Max Compression": 828.0850327328,
        "Time at Max Compression": 6.300875499964942e-07,
        "Velocity at Max Tension": 464.46465388253773,
        "Time at Max Tension": 6.476625599993735e-07,
        "Velocity at Recompression": 574.0505835557449,
        "Time at Recompression": 6.557500599954635e-07,
        "Carrier Frequency": 2232111412.128054,
        "Spall Strength": 1427973589.7828648,
        "Spall Strength Uncertainty": 10691103.580931518,
        "Strain Rate": 2278593.1401259126,
        "Strain Rate Uncertainty": 537339.2423506965,
        "Peak Shock Stress": 3251972732.0449786,
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
        "Velocity at Max Compression": 828.0850327328,
        "Time at Max Compression": 6.300875499964942e-07,
        "Velocity at Max Tension": 464.46465388253773,
        "Time at Max Tension": 6.476625599993735e-07,
        "Velocity at Recompression": 574.0505835557449,
        "Time at Recompression": 6.557500599954635e-07,
        "Carrier Frequency": 2232111412.128054,
        "Spall Strength": 1427973589.7828648,
        "Spall Strength Uncertainty": 10691103.580931518,
        "Strain Rate": 2278593.1401259126,
        "Strain Rate Uncertainty": 537339.2423506965,
        "Peak Shock Stress": 3251972732.0449786,
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
        "Signal Start Time": 5.49150049995728e-07,
        "Smoothing Characteristic Time": 2.9298752539258723e-09,
    },
    (7.5e-07, "gaussian_notch"): {
        "Velocity at Max Compression": 370.876283162495,
        "Time at Max Compression": 7.764625699971384e-07,
        "Velocity at Max Tension": 349.13528681206424,
        "Time at Max Tension": 7.814875699965751e-07,
        "Velocity at Recompression": 357.6812490443015,
        "Time at Recompression": 7.926750699993601e-07,
        "Carrier Frequency": 2232111412.128054,
        "Spall Strength": 85379066.7677766,
        "Spall Strength Uncertainty": 41633721.4220989,
        "Strain Rate": 476494.10114335315,
        "Strain Rate Uncertainty": 456459.72166333743,
        "Peak Shock Stress": 1456468251.607434,
        "Spect Time Res": 9.625000834177745e-10,
        "Spect Freq Res": 15624998.645815466,
        "Spect Velocity Res": 12.089538014726124,
        "Signal Start Time": 7.497875649824463e-07,
        "Smoothing Characteristic Time": 2.9298752539258723e-09,
    },
    ("otsu", "none"): {
        "Velocity at Max Compression": 828.3958859455566,
        "Time at Max Compression": 6.301500499947266e-07,
        "Velocity at Max Tension": 2.517899990994252,
        "Time at Max Tension": 6.499500599943531e-07,
        "Velocity at Recompression": 572.6798708259383,
        "Time at Recompression": 6.56187559996968e-07,
        "Carrier Frequency": 2232111412.128054,
        "Spall Strength": 3243305438.642162,
        "Spall Strength Uncertainty": 23599141.726231325,
        "Strain Rate": 4593721.181307893,
        "Strain Rate Uncertainty": 961593.766893317,
        "Peak Shock Stress": 3253193483.6967955,
        "Spect Time Res": 9.625000834177745e-10,
        "Spect Freq Res": 15624998.645815466,
        "Spect Velocity Res": 12.089538014726124,
        "Signal Start Time": 6.140750532205402e-07,
        "Smoothing Characteristic Time": 2.9298752539258723e-09,
    },
}
