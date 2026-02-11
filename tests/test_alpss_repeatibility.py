import pytest
from alpss.alpss_main import alpss_main
from alpss.commands import alpss_main_with_config
import os
import logging
import copy
import numpy as np
from matplotlib.figure import Figure
from conftest import EXPECTED_VALUES_MAP


def test_alpss_main_wo_configfile(valid_inputs, expected_values):
    # Call the function with valid inputs
    logging.info(f"Running test in spall doi mode {valid_inputs['start_time_user']} and carrier filter {valid_inputs['carrier_filter_type']}...")
    results = alpss_main(**valid_inputs)
    # Extract the results dictionary (results[1] should be the output dictionary)
    result_dict = results[1]

    # Iterate over the expected values and assert that the results match
    for key, expected_value in expected_values.items():
        assert key in result_dict['results'], f"Key '{key}' not found in the results."
        assert result_dict['results'][key] == pytest.approx(
            expected_value, rel=1e-9
        ), f"Mismatch for '{key}': expected {expected_value}, got {result_dict['results'][key]}"


def test_alpss_main_with_configfile(config_file_path, expected_values):
    """Test ALPSS using a JSON config file instead of direct dictionary input."""

    # Ensure the config file exists
    assert os.path.exists(config_file_path), f"Config file not found: {config_file_path}"

    # Run ALPSS using the config file
    results = alpss_main_with_config(config_file_path)

    # Extract the results dictionary (results[1] should be the output dictionary)
    result_dict = results[1]

    # Iterate over the expected values and assert that the results match
    for key, expected_value in expected_values.items():
        assert key in result_dict['results'], f"Key '{key}' not found in the results."
        assert result_dict['results'][key] == pytest.approx(
            expected_value, rel=1e-9
        ), f"Mismatch for '{key}': expected {expected_value}, got {result_dict['results'][key]}"


@pytest.mark.parametrize("start_time_user,carrier_filter_type", [
    ("otsu", "gaussian_notch"),
    ("iq", "gaussian_notch"),
    (7.5e-07, "gaussian_notch"),
    ("otsu", "none"),
])
def test_alpss_exact_values(valid_inputs, start_time_user, carrier_filter_type):
    """Test exact repeatability for key configurations."""
    inputs = copy.deepcopy(valid_inputs)
    inputs["start_time_user"] = start_time_user
    inputs["carrier_filter_type"] = carrier_filter_type

    logging.info(
        "Running exact value test: start=%s, filter=%s",
        start_time_user, carrier_filter_type
    )
    results = alpss_main(**inputs)
    assert results is not None, f"alpss_main returned None for start={start_time_user}, filter={carrier_filter_type}"

    result_dict = results[1]["results"]
    expected = EXPECTED_VALUES_MAP.get((start_time_user, carrier_filter_type))
    assert expected is not None, f"No expected values for ({start_time_user}, {carrier_filter_type})"

    for key, val in expected.items():
        assert key in result_dict, f"Key '{key}' not found in results."
        assert result_dict[key] == pytest.approx(
            val, rel=1e-9
        ), f"Mismatch for '{key}': expected {val}, got {result_dict[key]}"


@pytest.mark.parametrize("start_time_user", ["otsu", "iq", 7.5e-07])
@pytest.mark.parametrize("carrier_filter_type", ["gaussian_notch", "none"])
def test_alpss_smoke(valid_inputs, start_time_user, carrier_filter_type):
    """Smoke test: mode/filter combos complete without error and return valid results."""
    inputs = copy.deepcopy(valid_inputs)
    inputs["start_time_user"] = start_time_user
    inputs["carrier_filter_type"] = carrier_filter_type

    logging.info(
        "Running smoke test: start=%s, filter=%s",
        start_time_user, carrier_filter_type
    )
    results = alpss_main(**inputs)
    assert results is not None, f"alpss_main returned None for start={start_time_user}, filter={carrier_filter_type}"
    assert isinstance(results[0], Figure)
    result_dict = results[1]["results"]
    # Carrier frequency should always be a valid number
    assert not np.isnan(result_dict["Carrier Frequency"])
