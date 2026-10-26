import numpy as np


def default_spall_output() -> dict:
    return {
        "t_max_ten": np.nan, "t_rc": np.nan,
        "v_max_ten": np.nan, "v_rc": np.nan,
        "spall_strength_est": np.nan, "strain_rate_est": np.nan,
        "max_ten_freq_uncert": np.nan, "max_ten_vel_uncert": np.nan,
    }


def default_shock_output() -> dict:
    return {
        "peak_shock_stress": np.nan,
    }


def default_spall_uncertainty_output() -> dict:
    return {
        "spall_uncert": np.nan,
        "strain_rate_uncert": np.nan,
        "peak_velocity_freq_uncert": np.nan,
        "peak_velocity_vel_uncert": np.nan,
    }


def default_shock_result() -> dict:
    return {
        "shock_stress_pa": np.nan, "shock_stress_gpa": np.nan,
        "shock_stress_unc_pa": np.nan, "shock_stress_unc_gpa": np.nan,
        "method": "none", "S": np.nan,
    }


def default_hel_output():
    from alpss.analysis.hel import HELResult
    return HELResult(ok=False)


def default_spall_result():
    from alpss.analysis.spall import SpallResult
    return SpallResult(ok=False, dns_classification="analysis not run")
