"""Ground truth for each case, derived from the velocity-profile parameters.

Times are reported in ALPSS's time base, which starts at 0 at the first sample
of the file (spall_doi_finder subtracts time[0]); the simulated shock arrives at
t=0 in the profile's own time, i.e. at -t_begin in ALPSS time.
"""

from cases import profile_params, synthesis_params

C_LIGHT = 3e8  # same constant as pdv_synthesis


def truth_from_case(case, flat_config, velocity):
    """Expected ALPSS results for `case`.

    Keys are ALPSS results-CSV column names (see alpss/io/saving.py) so the
    summary can match them directly. `velocity` is the true velocity array;
    it is only used for the "velocity" shot type, whose peak is not a parameter.
    """
    p = profile_params(case)
    s = synthesis_params(case)
    rho = flat_config["density"]
    C0 = flat_config["C0"]
    C_L = flat_config["C_L"]
    shot = case["shot_type"]

    truth = {
        "Carrier Frequency": C_LIGHT / s["lambda_ref"] - C_LIGHT / s["lambda_tar"],
        "Signal Start Time": -p["t_begin"],
    }

    if shot == "velocity":
        v_peak = float(velocity.max())
    else:
        v_peak = p["V_plat"]
    truth["Velocity at Max Compression"] = v_peak
    truth["Peak Shock Stress"] = 0.5 * rho * C0 * v_peak

    if shot in ("HEL", "HEL-spall"):
        truth["HEL Free Surface Velocity (m/s)"] = p["V_HEL"]
        truth["HEL Strength (GPa)"] = 0.5 * rho * C_L * p["V_HEL"] / 1e9

    if shot == "HEL-spall":
        dV = p["dV_spall"]
        truth["Velocity at Max Tension"] = p["V_plat"] - dV
        truth["Time at Max Tension"] = p["t_spall"] - p["t_begin"]
        truth["Spall Strength"] = 0.5 * rho * C0 * dV
        # physical pullback slope; ALPSS measures from the time of peak velocity
        truth["Strain Rate"] = 0.5 / C0 * dV / (p["t_spall"] - p["t_plat_end"])

    return truth
