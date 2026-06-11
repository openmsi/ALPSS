import copy
import pytest
from alpss.utils.config import flatten_config
from alpss.utils.validation import validate_inputs


@pytest.fixture
def flat_inputs(valid_inputs):
    return flatten_config(valid_inputs)


# --- _ALWAYS_REQUIRED ---


def test_valid_inputs_passes(flat_inputs):
    validate_inputs(flat_inputs)


def test_missing_always_required_raises(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    del inputs["filepath"]
    with pytest.raises(ValueError, match="Missing required config keys"):
        validate_inputs(inputs)


@pytest.mark.parametrize(
    "key",
    [
        "out_files_dir",
        "sample_rate",
        "lam",
        "uncert_mult",
    ],
)
def test_missing_required_key_raises(flat_inputs, key):
    inputs = copy.deepcopy(flat_inputs)
    del inputs[key]
    with pytest.raises(ValueError, match="Missing required config keys"):
        validate_inputs(inputs)


# --- _REQUIRED_BY_MODE: start_time_user ---




@pytest.mark.parametrize("missing_key", ["iq_threshold_factor"])
def test_iq_requires_key(flat_inputs, missing_key):
    inputs = copy.deepcopy(flat_inputs)
    inputs["start_time_user"] = "iq"
    del inputs[missing_key]
    with pytest.raises(ValueError, match="start_time_user='iq'"):
        validate_inputs(inputs)


@pytest.mark.parametrize(
    "missing_key", ["cusum_offset", "cusum_threshold"]
)
def test_cusum_requires_key(flat_inputs, missing_key):
    inputs = copy.deepcopy(flat_inputs)
    inputs["start_time_user"] = "cusum"
    del inputs[missing_key]
    with pytest.raises(ValueError, match="start_time_user='cusum'"):
        validate_inputs(inputs)


def test_float_start_time_does_not_require_mode_params(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["start_time_user"] = 7.5e-7
    inputs.pop("iq_threshold_factor", None)
    validate_inputs(inputs)


# --- _REQUIRED_BY_MODE: carrier_filter_type ---


@pytest.mark.parametrize("missing_key", ["order", "wid"])
def test_gaussian_notch_requires_key(flat_inputs, missing_key):
    inputs = copy.deepcopy(flat_inputs)
    inputs["carrier_filter_type"] = "gaussian_notch"
    del inputs[missing_key]
    with pytest.raises(ValueError, match="carrier_filter_type='gaussian_notch'"):
        validate_inputs(inputs)


@pytest.mark.parametrize("missing_key", ["wid", "t_fit_begin", "t_fit_end"])
def test_sin_fit_subtract_requires_key(flat_inputs, missing_key):
    inputs = copy.deepcopy(flat_inputs)
    inputs["carrier_filter_type"] = "sin_fit_subtract"
    del inputs[missing_key]
    with pytest.raises(ValueError, match="carrier_filter_type='sin_fit_subtract'"):
        validate_inputs(inputs)


def test_none_filter_does_not_require_order_wid(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["carrier_filter_type"] = "none"
    inputs.pop("order", None)
    inputs.pop("wid", None)
    validate_inputs(inputs)


# --- _REQUIRED_BY_MODE: spall_enabled ---


@pytest.mark.parametrize("missing_key", ["pb_neighbors", "pb_idx_correction", "rc_neighbors", "rc_idx_correction", "C0", "density", "delta_rho", "delta_C0", "delta_lam", "delta_theta"])
def test_spall_enabled_requires_key(flat_inputs, missing_key):
    inputs = copy.deepcopy(flat_inputs)
    inputs["spall_enabled"] = True
    del inputs[missing_key]
    with pytest.raises(ValueError, match="spall_enabled='True'"):
        validate_inputs(inputs)


def test_spall_enabled_false_does_not_require_params(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["spall_enabled"] = False
    inputs["hel_enabled"] = False
    inputs.pop("pb_neighbors", None)
    inputs.pop("pb_idx_correction", None)
    inputs.pop("rc_neighbors", None)
    inputs.pop("rc_idx_correction", None)
    inputs.pop("C0", None)
    inputs.pop("density", None)
    inputs.pop("delta_rho", None)
    inputs.pop("delta_C0", None)
    inputs.pop("delta_lam", None)
    inputs.pop("delta_theta", None)
    validate_inputs(inputs)


# --- _REQUIRED_BY_MODE: hel_enabled ---


@pytest.mark.parametrize("missing_key", ["hel_start_time_ns", "hel_end_time_ns", "hel_angle_threshold_deg", "hel_detection_min_points", "minimum_HEL_velocity_expected", "C_L", "density"])
def test_hel_enabled_requires_key(flat_inputs, missing_key):
    inputs = copy.deepcopy(flat_inputs)
    inputs["spall_enabled"] = False
    inputs["hel_enabled"] = True
    del inputs[missing_key]
    with pytest.raises(ValueError, match="hel_enabled='True'"):
        validate_inputs(inputs)


def test_hel_enabled_false_does_not_require_params(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["spall_enabled"] = False
    inputs["hel_enabled"] = False
    inputs.pop("hel_start_time_ns", None)
    inputs.pop("hel_end_time_ns", None)
    inputs.pop("hel_angle_threshold_deg", None)
    inputs.pop("hel_detection_min_points", None)
    inputs.pop("minimum_HEL_velocity_expected", None)
    inputs.pop("pb_neighbors", None)
    inputs.pop("pb_idx_correction", None)
    inputs.pop("rc_neighbors", None)
    inputs.pop("rc_idx_correction", None)
    inputs.pop("C0", None)
    inputs.pop("density", None)
    inputs.pop("delta_rho", None)
    inputs.pop("delta_C0", None)
    inputs.pop("delta_lam", None)
    inputs.pop("delta_theta", None)
    validate_inputs(inputs)


# --- t_after constraint ---


def test_t_after_exceeds_time_to_take_raises(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["t_after"] = inputs["time_to_take"] + 1e-9
    with pytest.raises(ValueError, match="t_after"):
        validate_inputs(inputs)



# --- unknown params ---


def test_unknown_param_raises(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["totally_made_up_param"] = 42
    with pytest.raises(ValueError, match="Unknown config params"):
        validate_inputs(inputs)


def test_multiple_unknown_params_raises(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["foo"] = 1
    inputs["bar"] = 2
    with pytest.raises(ValueError, match="Unknown config params"):
        validate_inputs(inputs)


def test_mode_specific_params_not_flagged_as_unknown(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["carrier_filter_type"] = "sin_fit_subtract"
    inputs["t_fit_begin"] = 20
    inputs["t_fit_end"] = 300
    validate_inputs(inputs)


# --- enum validation ---


@pytest.mark.parametrize("mode", ["otsu", "iq", "cusum"])
def test_valid_start_time_modes(flat_inputs, mode):
    inputs = copy.deepcopy(flat_inputs)
    inputs["start_time_user"] = mode
    if mode == "cusum":
        inputs.setdefault("cusum_offset", 5)
        inputs.setdefault("cusum_threshold", 1000)
    validate_inputs(inputs)


def test_float_start_time_valid(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["start_time_user"] = 7.5e-7
    validate_inputs(inputs)


def test_invalid_start_time_user_raises(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["start_time_user"] = "bad_mode"
    with pytest.raises(ValueError, match="Invalid start_time_user"):
        validate_inputs(inputs)


@pytest.mark.parametrize("cft", ["gaussian_notch", "sin_fit_subtract", "none"])
def test_valid_carrier_filter_types(flat_inputs, cft):
    inputs = copy.deepcopy(flat_inputs)
    inputs["carrier_filter_type"] = cft
    if cft == "sin_fit_subtract":
        inputs.setdefault("t_fit_begin", 20)
        inputs.setdefault("t_fit_end", 300)
    elif cft == "none":
        inputs.pop("order", None)
        inputs.pop("wid", None)
    validate_inputs(inputs)


def test_invalid_carrier_filter_type_raises(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["carrier_filter_type"] = "bad_filter"
    with pytest.raises(ValueError, match="Invalid carrier_filter_type"):
        validate_inputs(inputs)


# --- HEL and carrier filter incompatibility ---


def test_hel_enabled_with_gaussian_notch_raises(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["spall_enabled"] = False
    inputs["hel_enabled"] = True
    inputs["carrier_filter_type"] = "gaussian_notch"
    with pytest.raises(ValueError, match="HEL detection is incompatible with gaussian_notch"):
        validate_inputs(inputs)


def test_hel_enabled_with_sin_fit_subtract_passes(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["spall_enabled"] = False
    inputs["hel_enabled"] = True
    inputs["carrier_filter_type"] = "sin_fit_subtract"
    validate_inputs(inputs)


def test_hel_enabled_with_none_filter_passes(flat_inputs):
    inputs = copy.deepcopy(flat_inputs)
    inputs["spall_enabled"] = False
    inputs["hel_enabled"] = True
    inputs["carrier_filter_type"] = "none"
    validate_inputs(inputs)
