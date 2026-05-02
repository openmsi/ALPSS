import pytest
import numpy as np
from alpss.analysis.hel import hel_detection, elastic_shock_strain_rate, HELResult
from conftest import HEL_DETECTION_BASE as _BASE


class TestElasticShockStrainRate:
    def test_basic_calculation(self):
        # C_L=5000 m/s, velocity jump of 100 m/s over 10 ns
        rate = elastic_shock_strain_rate(C_L=5000, U_hel=100, U_0=0, t_hel=10, t_0=0)
        expected = (1 / (2 * 5000)) * (100 / 10)
        assert rate == pytest.approx(expected, rel=1e-9)

    def test_zero_dt_returns_nan(self):
        rate = elastic_shock_strain_rate(C_L=5000, U_hel=100, U_0=0, t_hel=5, t_0=5)
        assert np.isnan(rate)

    def test_negative_dt_returns_nan(self):
        rate = elastic_shock_strain_rate(C_L=5000, U_hel=100, U_0=0, t_hel=3, t_0=5)
        assert np.isnan(rate)



class TestHELDetection:
    def test_detects_hel_in_synthetic_signal(self, synthetic_hel_signal):
        t, v, u = synthetic_hel_signal
        result = hel_detection(
            t, v, u,
            **{**_BASE, "hel_start_ns": 3.0, "hel_end_ns": 10.0,
               "angle_threshold_deg": 45.0, "min_points": 5,
               "min_velocity": 50.0, "density": 8960, "acoustic_velocity": 3940},
        )
        assert result.ok is True
        assert result.strength_gpa > 0
        assert result.free_surface_velocity == pytest.approx(200, abs=5)
        assert 2.0 <= result.time_detection_ns <= 8.0
        assert result.consecutive_points >= 5

    def test_returns_not_ok_below_min_velocity(self, synthetic_hel_signal):
        t, v, u = synthetic_hel_signal
        result = hel_detection(
            t, v, u,
            **{**_BASE, "hel_start_ns": 3.0, "hel_end_ns": 10.0,
               "min_velocity": 500.0},  # above the plateau velocity
        )
        assert result.ok is False

    def test_returns_not_ok_for_empty_data(self):
        with pytest.raises(ValueError, match="insufficient valid data points for HEL"):
            hel_detection(np.array([]), np.array([]), np.array([]), **_BASE)

    def test_returns_not_ok_for_all_nan(self):
        t = np.linspace(0, 10, 100)
        v = np.full_like(t, np.nan)
        u = np.ones_like(t)
        with pytest.raises(ValueError, match="insufficient valid data points for HEL"):
            hel_detection(t, v, u, **_BASE)

    def test_hel_stress_calculation(self, synthetic_hel_signal):
        """Verify HEL stress = 0.5 * density * acoustic_velocity * fsv / 1e9."""
        t, v, u = synthetic_hel_signal
        density = 8960
        acoustic_velocity = 3940
        result = hel_detection(
            t, v, u,
            **{**_BASE, "hel_start_ns": 3.0, "hel_end_ns": 10.0,
               "min_points": 5, "min_velocity": 50.0,
               "density": density, "acoustic_velocity": acoustic_velocity},
        )
        expected_gpa = 0.5 * density * acoustic_velocity * abs(result.free_surface_velocity) / 1e9
        assert result.strength_gpa == pytest.approx(expected_gpa, rel=1e-6)

    def test_strain_rate_computed_when_C_L_provided(self, synthetic_hel_signal):
        t, v, u = synthetic_hel_signal
        # Use a wider window so the plateau doesn't start at index 0,
        # which allows a reference point before the segment for strain rate
        result = hel_detection(
            t, v, u,
            **{**_BASE, "hel_start_ns": -2.0, "hel_end_ns": 10.0,
               "min_points": 5, "min_velocity": 50.0,
               "density": 8960, "acoustic_velocity": 3940, "C_L": 5000},
        )
        assert result.ok is True
        assert np.isfinite(result.strain_rate)

    def test_no_material_props_gives_nan_stress(self, synthetic_hel_signal):
        """HEL detection works but stress is NaN without material properties."""
        t, v, u = synthetic_hel_signal
        result = hel_detection(
            t, v, u,
            **{**_BASE, "hel_start_ns": 3.0, "hel_end_ns": 10.0,
               "min_points": 5, "min_velocity": 50.0},
        )
        assert result.ok is True
        assert np.isnan(result.strength_gpa)
        assert result.free_surface_velocity == pytest.approx(200, abs=10)

    def test_result_has_plotting_data(self, synthetic_hel_signal):
        t, v, u = synthetic_hel_signal
        result = hel_detection(
            t, v, u,
            **{**_BASE, "hel_start_ns": 3.0, "hel_end_ns": 10.0,
               "min_points": 5, "min_velocity": 50.0},
        )
        assert result.time_window is not None
        assert result.velocity_window is not None
        assert result.gradient_smooth is not None
        assert result.angles_deg is not None
        assert result.segment_start_idx is not None
        assert result.segment_end_idx is not None
