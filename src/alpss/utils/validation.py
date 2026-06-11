import logging

logger = logging.getLogger("alpss")

_ALWAYS_REQUIRED = [
    "filepath",
    "out_files_dir",
    "header_lines",
    "time_to_skip",
    "time_to_take",
    "t_before",
    "t_after",
    "start_time_user",
    "start_time_correction",
    "sample_rate",
    "nperseg",
    "noverlap",
    "nfft",
    "window",
    "freq_min",
    "freq_max",
    "blur_kernel",
    "blur_sigx",
    "blur_sigy",
    "carrier_filter_type",
    "carrier_band_time",
    "smoothing_window",
    "smoothing_wid",
    "smoothing_amp",
    "smoothing_sigma",
    "smoothing_mu",
    "lam",
    "theta",
    "uncert_mult",
    "cmap",
    "plot_figsize",
    "plot_dpi",
    "save_data",
    "display_plots",
    "spall_enabled",
    "hel_enabled",
    "min_velocity_threshold",
    "max_velocity_uncertainty_threshold",
]

# Optional keys — warning is emitted if absent.
_OPTIONAL = ["bytestring"]

_REQUIRED_BY_MODE = {
    "start_time_user=otsu": [],
    "start_time_user=iq": ["iq_threshold_factor"],
    "start_time_user=cusum": ["cusum_offset", "cusum_threshold"],
    "carrier_filter_type=gaussian_notch": ["order", "wid"],
    "carrier_filter_type=sin_fit_subtract": ["wid", "t_fit_begin", "t_fit_end"],
    "spall_enabled=True": ["pb_neighbors", "pb_idx_correction", "rc_neighbors", "rc_idx_correction", "C0", "density", "delta_rho", "delta_C0", "delta_lam", "delta_theta"],
    "hel_enabled=True": ["hel_start_time_ns", "hel_end_time_ns", "hel_angle_threshold_deg", "hel_detection_min_points", "minimum_HEL_velocity_expected", "density", "C_L"],
}

_ALL_KNOWN = (
    set(_ALWAYS_REQUIRED)
    | set(_OPTIONAL)
    | {k for keys in _REQUIRED_BY_MODE.values() for k in keys}
)

_START_TIME_MODES = {"otsu", "iq", "cusum"}
_CARRIER_FILTER_TYPES = {"gaussian_notch", "sin_fit_subtract", "none"}


def validate_inputs(inputs):
    missing = [k for k in _ALWAYS_REQUIRED if k not in inputs]
    if missing:
        raise ValueError(f"Missing required config keys: {missing}")

    for mode_key, required_keys in _REQUIRED_BY_MODE.items():
        param, value = mode_key.split("=")
        # Handle boolean string values ("True"/"False" in the mode key)
        if value == "True":
            check_value = True
        elif value == "False":
            check_value = False
        else:
            check_value = value
        if inputs.get(param) == check_value:
            missing = [k for k in required_keys if k not in inputs]
            if missing:
                raise ValueError(f"{param}='{value}' requires: {missing}")

    for key in _OPTIONAL:
        if key not in inputs:
            logger.warning("Optional param '%s' not provided", key)

    unknown = [k for k in inputs if k not in _ALL_KNOWN]
    if unknown:
        raise ValueError(f"Unknown config params: {unknown}")

    for bool_key in ("save_data", "display_plots", "spall_enabled", "hel_enabled"):
        if not isinstance(inputs[bool_key], bool):
            raise ValueError(f"'{bool_key}' must be a bool, got {type(inputs[bool_key]).__name__!r}.")

    stu = inputs["start_time_user"]
    if not (isinstance(stu, (int, float)) or stu in _START_TIME_MODES):
        raise ValueError(
            f"Invalid start_time_user='{stu}'. Must be a float or one of {_START_TIME_MODES}."
        )

    cft = inputs["carrier_filter_type"]
    if cft not in _CARRIER_FILTER_TYPES:
        raise ValueError(
            f"Invalid carrier_filter_type='{cft}'. Must be one of {_CARRIER_FILTER_TYPES}."
        )

    if inputs["t_after"] > inputs["time_to_take"]:
        raise ValueError("'t_after' must be less than 'time_to_take'.")

    if inputs["hel_enabled"] and inputs["carrier_filter_type"] == "gaussian_notch":
        raise ValueError("HEL detection is incompatible with gaussian_notch filter (removes carrier signal needed for HEL analysis).")
