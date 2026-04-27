import pytest
import numpy as np

from alpss.analysis.shock_stress import (
    shock_stress_acoustic,
    shock_stress_hugoniot,
    shock_stress_hugoniot_uncertainty,
    get_hugoniot_S,
    calculate_shock_stress,
)


class TestGetHugonotS:
    def test_copper(self):
        assert get_hugoniot_S("Cu") == pytest.approx(1.49)

    def test_copper_aliases(self):
        for alias in ("cu", "Cu", "copper", "COPPER"):
            assert get_hugoniot_S(alias) == pytest.approx(1.49)

    def test_aluminum(self):
        assert get_hugoniot_S("Al") == pytest.approx(1.34)

    def test_unknown_material_returns_default(self):
        assert get_hugoniot_S("unobtainium") == pytest.approx(1.49)

    def test_custom_default(self):
        assert get_hugoniot_S("mystery", default=1.0) == pytest.approx(1.0)


class TestShockStressAcoustic:
    def test_basic(self):
        sigma = shock_stress_acoustic(density=8960, C0=3950, peak_velocity=300.0)
        assert sigma == pytest.approx(0.5 * 8960 * 3950 * 300)

    def test_zero_velocity(self):
        assert shock_stress_acoustic(8960, 3950, 0.0) == pytest.approx(0.0)


class TestShockStressHugoniot:
    def test_copper_300ms(self):
        rho, C0, S, v = 8960, 3950, 1.49, 300.0
        u_p = v / 2
        U_s = C0 + S * u_p
        expected = rho * U_s * u_p
        assert shock_stress_hugoniot(rho, C0, v, S) == pytest.approx(expected)

    def test_larger_than_acoustic_for_positive_S(self):
        rho, C0, S, v = 8960, 3950, 1.49, 200.0
        assert shock_stress_hugoniot(rho, C0, v, S) > shock_stress_acoustic(rho, C0, v)

    def test_equals_acoustic_when_S_zero(self):
        rho, C0, v = 8960, 3950, 200.0
        assert shock_stress_hugoniot(rho, C0, v, S=0.0) == pytest.approx(
            shock_stress_acoustic(rho, C0, v)
        )

    def test_gpa_value_copper(self):
        sigma_pa = shock_stress_hugoniot(8960, 3950, 300.0, 1.49)
        sigma_gpa = sigma_pa * 1e-9
        assert 1.0 < sigma_gpa < 10.0


class TestShockStressUncertainty:
    def test_positive_for_positive_unc(self):
        unc = shock_stress_hugoniot_uncertainty(8960, 3950, 300.0, 10.0, 1.49)
        assert unc > 0

    def test_scales_linearly_with_velocity_unc(self):
        unc1 = shock_stress_hugoniot_uncertainty(8960, 3950, 300.0, 10.0, 1.49)
        unc2 = shock_stress_hugoniot_uncertainty(8960, 3950, 300.0, 20.0, 1.49)
        assert unc2 == pytest.approx(2 * unc1, rel=1e-9)

    def test_zero_unc_gives_zero(self):
        assert shock_stress_hugoniot_uncertainty(8960, 3950, 300.0, 0.0, 1.49) == pytest.approx(0.0)


class TestCalculateShockStress:
    def test_hugoniot_method(self):
        r = calculate_shock_stress(8960, 3950, 300.0, method="hugoniot")
        assert r["method"] == "hugoniot"
        assert r["shock_stress_gpa"] == pytest.approx(r["shock_stress_pa"] * 1e-9)
        assert r["shock_stress_gpa"] > 0

    def test_acoustic_method(self):
        r = calculate_shock_stress(8960, 3950, 300.0, method="acoustic")
        assert r["method"] == "acoustic"
        assert np.isnan(r["S"])

    def test_material_lookup(self):
        r_cu = calculate_shock_stress(8960, 3950, 300.0, material="Cu")
        assert r_cu["S"] == pytest.approx(1.49)

    def test_explicit_S_overrides_material(self):
        r = calculate_shock_stress(8960, 3950, 300.0, material="Cu", S=1.0)
        assert r["S"] == pytest.approx(1.0)

    def test_uncertainty_propagated(self):
        r = calculate_shock_stress(8960, 3950, 300.0, peak_velocity_unc=10.0)
        assert r["shock_stress_unc_gpa"] > 0

    def test_gpa_pa_consistency(self):
        r = calculate_shock_stress(8960, 3950, 300.0, peak_velocity_unc=5.0)
        assert r["shock_stress_pa"] == pytest.approx(r["shock_stress_gpa"] * 1e9)
        assert r["shock_stress_unc_pa"] == pytest.approx(r["shock_stress_unc_gpa"] * 1e9)
