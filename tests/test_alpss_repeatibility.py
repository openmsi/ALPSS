import pytest
from alpss.alpss_main import alpss_main
from alpss.commands import alpss_main_with_config
import os 

def test_alpss_main_output(valid_inputs, expected_values):
    # Call the function with valid inputs
    results = alpss_main(**valid_inputs)
    # Extract the results dictionary (results[1] should be the output dictionary)
    result_dict = results[1]

    # Iterate over the expected values and assert that the results match
    for key, expected_value in expected_values.items():
        assert key in result_dict['results'], f"Key '{key}' not found in the results."
        assert result_dict['results'][key] == pytest.approx(
            expected_value, rel=1e-9
        ), f"Mismatch for '{key}': expected {expected_value}, got {result_dict['results'][key]}"


def test_alpss_main_with_config(config_file_path, expected_values):
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
