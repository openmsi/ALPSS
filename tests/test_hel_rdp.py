import pytest
import numpy as np

from alpss.analysis.hel import hel_detection, hel_detection_rdp_hybrid, HELResult
from conftest import HEL_DETECTION_BASE as _HEL_BASE, HEL_RDP_BASE as _RDP_BASE


class TestHELRDPHybrid:
    def test_detects_hel_in_synthetic(self, synthetic_hel_signal_rdp):
        t, v, u = synthetic_hel_signal_rdp
        result = hel_detection_rdp_hybrid(
            t, v, u,
            **{**_RDP_BASE, "hel_start_ns": 0.0, "hel_end_ns": 15.0,
               "min_velocity": 50.0, "density": 8960, "acoustic_velocity": 3950,
               "C_L": 4700, "rdp_epsilon": 2.0, "slope_drop_ratio": 0.85,
               "min_plateau_duration_ns": 0.5, "min_points": 5},
        )
        assert result.ok is True
        assert result.method in ("rdp_linear", "gradient_fallback")
        assert result.strength_gpa > 0
        assert result.free_surface_velocity == pytest.approx(160, abs=15)

    def test_strain_rate_is_positive(self, synthetic_hel_signal_rdp):
        t, v, u = synthetic_hel_signal_rdp
        result = hel_detection_rdp_hybrid(
            t, v, u,
            **{**_RDP_BASE, "hel_start_ns": 0.0, "hel_end_ns": 15.0,
               "min_velocity": 50.0, "C_L": 4700, "rdp_epsilon": 2.0},
        )
        if result.ok:
            assert result.strain_rate > 0

    def test_returns_helresult_always(self, synthetic_hel_signal_rdp):
        t, v, u = synthetic_hel_signal_rdp
        result = hel_detection_rdp_hybrid(t, v, u, **{**_RDP_BASE, "min_velocity": 9999.0})
        assert isinstance(result, HELResult)

    def test_fallback_on_flat_signal(self):
        t = np.linspace(0, 20, 200)
        v = np.ones(200) * 100.0
        u = np.ones(200) * 2.0
        result = hel_detection_rdp_hybrid(t, v, u, **{**_RDP_BASE, "min_velocity": 50.0})
        assert isinstance(result, HELResult)
        assert result.method in ("rdp_linear", "gradient", "gradient_fallback")

    def test_rdp_points_stored_when_ok(self, synthetic_hel_signal_rdp):
        t, v, u = synthetic_hel_signal_rdp
        result = hel_detection_rdp_hybrid(
            t, v, u,
            **{**_RDP_BASE, "hel_start_ns": 0.0, "hel_end_ns": 15.0,
               "min_velocity": 50.0, "rdp_epsilon": 2.0},
        )
        if result.ok and result.method == "rdp_linear":
            assert result.rdp_points is not None
            assert result.rdp_points.shape[1] == 2

    def test_hel_detection_dispatches_to_hybrid(self, synthetic_hel_signal_rdp):
        """hel_detection(method='rdp_linear') should delegate correctly."""
        t, v, u = synthetic_hel_signal_rdp
        result = hel_detection(
            t, v, u,
            **{**_HEL_BASE, "hel_start_ns": 0.0, "hel_end_ns": 15.0,
               "min_velocity": 50.0, "method": "rdp_linear",
               "density": 8960, "acoustic_velocity": 3950,
               "hel_rdp_epsilon": 2.0},
        )
        assert isinstance(result, HELResult)
        assert result.method in ("rdp_linear", "gradient_fallback", "gradient")

    def test_hel_detection_gradient_still_works(self, synthetic_hel_signal_rdp):
        """Original gradient method must be unaffected."""
        t, v, u = synthetic_hel_signal_rdp
        result = hel_detection(
            t, v, u,
            **{**_HEL_BASE, "hel_start_ns": 0.0, "hel_end_ns": 15.0,
               "min_velocity": 50.0, "method": "gradient",
               "density": 8960, "acoustic_velocity": 3950},
        )
        assert isinstance(result, HELResult)
        assert result.method == "gradient"
