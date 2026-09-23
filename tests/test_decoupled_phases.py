import pytest
import copy
import numpy as np
from unittest.mock import patch
from matplotlib.figure import Figure
from alpss.commands import alpss_main_with_config


def test_velocity_only_no_spall(valid_inputs):
    """Test that velocity processing succeeds with spall_enabled=False."""
    inputs = copy.deepcopy(valid_inputs)
    inputs["spall"]["spall_enabled"] = False

    results = alpss_main_with_config(inputs)
    assert (
        results is not None
    ), "alpss_main should return results even with spall_enabled='no'"
    assert isinstance(results[0], Figure)
    result_dict = results[1]["results"][0]
    assert not np.isnan(result_dict["Carrier Frequency"])
    # Spall values should be NaN when spall_enabled is 'no'
    assert np.isnan(result_dict["Spall Strength"])
    assert np.isnan(result_dict["Strain Rate"])


def test_analysis_failure_returns_nan_defaults(valid_inputs):
    """Test that analysis failure produces NaN defaults but still returns results."""
    inputs = copy.deepcopy(valid_inputs)

    with patch(
        "alpss.utils.phases.spall_analysis",
        side_effect=RuntimeError("simulated analysis failure"),
    ):
        results = alpss_main_with_config(inputs)

    assert (
        results is not None
    ), "alpss_main should return results even when analysis fails"
    assert isinstance(results[0], Figure)
    result_dict = results[1]["results"][0]
    # Velocity-derived values should still be valid
    assert not np.isnan(result_dict["Carrier Frequency"])
    # Spall analysis values should be NaN due to analysis failure
    assert np.isnan(result_dict["Spall Strength"])
    assert np.isnan(result_dict["Strain Rate"])
    assert np.isnan(result_dict["Spall Strength Uncertainty"])
    assert np.isnan(result_dict["Strain Rate Uncertainty"])


def test_velocity_failure_raises(valid_inputs):
    """Test that velocity processing failure raises."""
    inputs = copy.deepcopy(valid_inputs)

    with pytest.raises(RuntimeError, match="simulated data failure"):
        with patch(
            "alpss.commands.extract_data",
            side_effect=RuntimeError("simulated data failure"),
        ):
            alpss_main_with_config(inputs)
