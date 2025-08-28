import pytest
from alpss.alpss_main import alpss_main
from alpss.commands import alpss_main_with_config
import os 
import logging
import copy

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
    
# @pytest.mark.parametrize("carrier_filter_type", ["sin_fit_subtract", "none"])
# @pytest.mark.parametrize("start_time_user", ["iq", "cusum", 7.5e-07])
# def test_alpss_main_modes_and_filters(valid_inputs, start_time_user, carrier_filter_type):
#     """Run across requested spall DOI modes and carrier filter types."""
#     inputs = copy.deepcopy(valid_inputs)
#     inputs["start_time_user"] = start_time_user
#     inputs["carrier_filter_type"] = carrier_filter_type

#     logging.info(
#         "Running param test in spall doi mode %s and carrier filter %s...",
#         inputs["start_time_user"], inputs["carrier_filter_type"]
#     )
#     _ = alpss_main(**inputs)


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


