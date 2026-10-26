import pytest
import numpy as np
from alpss.analysis.velocity_uncertainty import velocity_uncertainty_analysis


def test_velocity_uncertainty_analysis_computes_uncertainties(valid_inputs):
    """Test that velocity_uncertainty_analysis correctly extracts peak velocity uncertainties."""
    # Create minimal vc_out and iua_out with required fields
    peak_idx = 500
    freq_uncert_val = 1e6
    vel_uncert_val = 10.5

    vc_out = {
        "peak_velocity_idx": peak_idx,
    }

    iua_out = {
        "freq_uncert": np.full(1000, 0.0),
        "vel_uncert": np.full(1000, 0.0),
    }
    iua_out["freq_uncert"][peak_idx] = freq_uncert_val
    iua_out["vel_uncert"][peak_idx] = vel_uncert_val

    # Run velocity uncertainty analysis
    result = velocity_uncertainty_analysis(vc_out, iua_out)

    # Verify output structure and values
    assert "peak_velocity_freq_uncert" in result
    assert "peak_velocity_vel_uncert" in result
    assert result["peak_velocity_freq_uncert"] == pytest.approx(freq_uncert_val, rel=1e-9)
    assert result["peak_velocity_vel_uncert"] == pytest.approx(vel_uncert_val, rel=1e-9)


def test_velocity_uncertainty_analysis_different_indices():
    """Test that velocity_uncertainty_analysis correctly handles different peak indices."""
    peak_idx = 100
    freq_uncert_val = 2.5e6
    vel_uncert_val = 25.3

    vc_out = {
        "peak_velocity_idx": peak_idx,
    }

    iua_out = {
        "freq_uncert": np.linspace(0, 5e6, 500),
        "vel_uncert": np.linspace(0, 50, 500),
    }
    iua_out["freq_uncert"][peak_idx] = freq_uncert_val
    iua_out["vel_uncert"][peak_idx] = vel_uncert_val

    result = velocity_uncertainty_analysis(vc_out, iua_out)

    assert result["peak_velocity_freq_uncert"] == pytest.approx(freq_uncert_val, rel=1e-9)
    assert result["peak_velocity_vel_uncert"] == pytest.approx(vel_uncert_val, rel=1e-9)
