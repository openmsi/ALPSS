import pytest
import copy
import numpy as np
from unittest.mock import patch
from matplotlib.figure import Figure
from alpss.alpss_main import alpss_main


def test_velocity_only_no_spall(valid_inputs):
    """Test that velocity processing succeeds with spall_calculation='no'."""
    inputs = copy.deepcopy(valid_inputs)
    inputs["spall_calculation"] = "no"

    results = alpss_main(**inputs)
    assert results is not None, "alpss_main should return results even with spall_calculation='no'"
    assert isinstance(results[0], Figure)
    result_dict = results[1]["results"][0]
    assert not np.isnan(result_dict["Carrier Frequency"])
    # Spall values should be NaN when spall_calculation is 'no'
    assert np.isnan(result_dict["Spall Strength"])
    assert np.isnan(result_dict["Strain Rate"])


def test_analysis_failure_returns_nan_defaults(valid_inputs):
    """Test that analysis failure produces NaN defaults but still returns results."""
    inputs = copy.deepcopy(valid_inputs)

    with patch("alpss.alpss_main.spall_analysis", side_effect=RuntimeError("simulated analysis failure")):
        results = alpss_main(**inputs)

    assert results is not None, "alpss_main should return results even when analysis fails"
    assert isinstance(results[0], Figure)
    result_dict = results[1]["results"][0]
    # Velocity-derived values should still be valid
    assert not np.isnan(result_dict["Carrier Frequency"])
    # Spall analysis values should be NaN due to analysis failure
    assert np.isnan(result_dict["Spall Strength"])
    assert np.isnan(result_dict["Strain Rate"])
    assert np.isnan(result_dict["Spall Strength Uncertainty"])
    assert np.isnan(result_dict["Strain Rate Uncertainty"])


def test_velocity_failure_returns_none(valid_inputs):
    """Test that velocity processing failure returns None."""
    inputs = copy.deepcopy(valid_inputs)

    with patch("alpss.alpss_main.extract_data", side_effect=RuntimeError("simulated data failure")):
        results = alpss_main(**inputs)

    assert results is None, "alpss_main should return None when velocity processing fails"
