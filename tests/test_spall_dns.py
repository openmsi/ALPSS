import pytest
import numpy as np

from alpss.analysis.spall import (
    _rdp_simplify,
    _detect_spall_topology,
    spall_analysis_with_dns,
    SpallResult,
)


class TestRDPSimplify:
    def test_straight_line_collapses_to_endpoints(self):
        t = np.linspace(0, 10, 100)
        v = 3.0 * t + 1.0
        pts = np.column_stack((t, v))
        idx = _rdp_simplify(pts, epsilon=0.01)
        assert len(idx) == 2

    def test_fewer_than_3_points_returned_as_is(self):
        pts = np.array([[0, 0], [1, 1]])
        idx = _rdp_simplify(pts, epsilon=1.0)
        assert len(idx) == 2

    def test_checkmark_shape_preserves_key_vertices(self):
        t = np.linspace(0, 50, 500)
        v = np.zeros_like(t)
        v[t <= 10] = 500.0
        v[(t > 10) & (t <= 25)] = 500 - 25 * (t[(t > 10) & (t <= 25)] - 10)
        v[t > 25] = 125 + 5 * (t[t > 25] - 25)
        pts = np.column_stack((t, v))
        idx = _rdp_simplify(pts, epsilon=5.0)
        assert len(idx) >= 3


class TestDetectSpallTopology:
    @pytest.fixture
    def valid_checkmark(self):
        t = np.linspace(0, 80, 800)
        v = np.zeros_like(t)
        v[t <= 15] = 500.0
        v[(t > 15) & (t <= 35)] = 500 - 20 * (t[(t > 15) & (t <= 35)] - 15)
        v[t > 35] = 100 + 8 * (t[t > 35] - 35)
        return t, v

    def test_valid_spall_detected(self, valid_checkmark):
        t, v = valid_checkmark
        ok, reason, keys, pts = _detect_spall_topology(t, v, rdp_epsilon=5.0,
                                                        min_pullback_velocity=30.0,
                                                        min_recomp_ratio=0.01,
                                                        min_recomp_velocity_ratio=1.01,
                                                        min_recomp_time_ns=1.0)
        assert ok is True
        assert keys is not None
        assert keys["pullback_depth"] > 30

    def test_returns_false_for_flat_signal(self):
        t = np.linspace(0, 50, 500)
        v = np.ones(500) * 200.0
        ok, reason, keys, _ = _detect_spall_topology(t, v, rdp_epsilon=2.0)
        assert ok is False

    def test_returns_false_when_pullback_too_small(self, valid_checkmark):
        t, v = valid_checkmark
        ok, reason, keys, _ = _detect_spall_topology(
            t, v, rdp_epsilon=5.0, min_pullback_velocity=9999.0
        )
        assert ok is False
        assert "pullback" in reason.lower() or "minimum" in reason.lower()

    def test_rdp_points_returned_on_failure(self):
        t = np.linspace(0, 50, 100)
        v = np.ones(100) * 100.0
        ok, reason, keys, rdp_pts = _detect_spall_topology(t, v)
        assert rdp_pts is not None


class TestSpallAnalysisWithDNS:
    @pytest.fixture
    def vc_iua(self):
        np.random.seed(0)
        t = np.linspace(0, 80e-9, 800)
        v = np.zeros(800)
        v[t <= 15e-9] = 500.0
        drop_mask = (t > 15e-9) & (t <= 35e-9)
        v[drop_mask] = 500 - 20 * (t[drop_mask] - 15e-9) / 1e-9
        v[t > 35e-9] = 100 + 8 * (t[t > 35e-9] - 35e-9) / 1e-9
        v += np.random.normal(0, 2, 800)
        vc = {"time_f": t, "velocity_f_smooth": v}
        iua = {"vel_uncert": np.ones(800) * 5.0, "freq_uncert": np.ones(800) * 1e6}
        return vc, iua

    def test_dns_disabled_returns_early(self):
        vc = {"time_f": np.zeros(10), "velocity_f_smooth": np.zeros(10)}
        iua = {"vel_uncert": np.zeros(10), "freq_uncert": np.zeros(10)}
        r = spall_analysis_with_dns(vc, iua, spall_calculation="no",
                                    C0=3950, density=8960,
                                    pb_neighbors=3, pb_idx_correction=0)
        assert r.ok is False
        assert "disabled" in r.dns_classification

    def test_valid_spall_classified(self, vc_iua):
        vc, iua = vc_iua
        r = spall_analysis_with_dns(
            vc, iua,
            spall_detection_method="max_min",
            spall_calculation="yes",
            C0=3950, density=8960,
            pb_neighbors=5, pb_idx_correction=0,
        )
        assert isinstance(r, SpallResult)
        assert r.ok is True
        assert r.dns_classification == "Valid Spall"
        assert r.spall_strength_pa > 0
        assert np.isfinite(r.strain_rate)

    def test_rdp_method_runs(self, vc_iua):
        vc, iua = vc_iua
        r = spall_analysis_with_dns(
            vc, iua,
            spall_detection_method="rdp",
            spall_calculation="yes",
            C0=3950, density=8960,
            pb_neighbors=5, pb_idx_correction=0,
            rdp_epsilon=5.0,
            min_pullback_velocity=10.0,
        )
        assert isinstance(r, SpallResult)
        assert isinstance(r.dns_classification, str)

    def test_spall_result_fields_populated(self, vc_iua):
        vc, iua = vc_iua
        r = spall_analysis_with_dns(
            vc, iua,
            spall_detection_method="max_min",
            spall_calculation="yes",
            C0=3950, density=8960,
            pb_neighbors=5, pb_idx_correction=0,
        )
        assert np.isfinite(r.v_peak)
        assert np.isfinite(r.v_pullback)
        assert np.isfinite(r.t_peak)
        assert np.isfinite(r.t_pullback)
