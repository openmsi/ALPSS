"""Ground truth for each case, derived from the velocity-profile parameters.

PROFILE_DEFAULTS mirrors the defaults inside
alpss.simulation.pdv_synthesis.generate_velocity_profile. generate.py checks
that the profile built from these explicit values matches the one built from
the module's own defaults, so a drift between the two fails loudly.

Times are reported in ALPSS's time base, which starts at 0 at the first sample
of the file (spall_doi_finder subtracts time[0]); the simulated shock arrives at
t=0 in the profile's own time, i.e. at -t_begin in ALPSS time.
"""

C_LIGHT = 3e8  # same constant as pdv_synthesis

PROFILE_DEFAULTS = {
    "velocity": dict(t_begin=-500e-9, t_end=1000e-9, vel_peak=200, a=1, b=0.00001),
    "HEL": dict(
        t_begin=-3e-6, t_end=3e-6,
        V0=0, V_HEL=50, V_plat=300,
        t_rise1=5e-9, t_rise2=10e-9, t_rise3=20e-9,
        t_return1=50e-9, t_return2=70e-9,
    ),
    "HEL-spall": dict(
        t_begin=-3e-6, t_end=3e-6,
        V0=0, V_HEL=100, V_plat=300,
        t_hel_start=3e-9, t_hel_end=7e-9,
        t_plat_start=15e-9, t_plat_end=25e-9,
        t_spall=40e-9, t_recover=60e-9,
        dV_spall=100,
    ),
}

# velocity_to_pdv_voltage defaults
SYNTHESIS_DEFAULTS = dict(lambda_ref=1550e-9, lambda_tar=1550.016e-9)


def profile_params(case):
    return {**PROFILE_DEFAULTS[case["shot_type"]], **case["profile"]}


def synthesis_params(case):
    return {**SYNTHESIS_DEFAULTS, **case["synthesis"]}


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
