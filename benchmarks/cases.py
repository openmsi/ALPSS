"""Simulated benchmark cases.

Each case is one synthetic signal. ``profile`` overrides PROFILE_DEFAULTS for the
case's shot type and is passed to ``generate_velocity_profile``; ``synthesis``
overrides SYNTHESIS_DEFAULTS and is passed to ``velocity_to_pdv_voltage``. These
are the only defaults: the generator has none, so the signal and the truth
always come from the same numbers. ``config`` holds the
ALPSS config keys this case needs changed relative to
tests/input_data/config.json (beyond the ones run.py always derives from the
signal).
"""

SAMPLE_RATE = 128e9

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

# power_tar_dbm matches run_pdv_synthesis.py in PDV_simulated_data
SYNTHESIS_DEFAULTS = dict(lambda_ref=1550e-9, lambda_tar=1550.016e-9, power_tar_dbm=-15)

CASES = [
    dict(
        id="case_01",
        description="HEL, default timings, low noise",
        shot_type="HEL",
        profile={},
        synthesis=dict(noise_sd=0.01),
        seed=1,
        config=dict(spall_enabled=False, hel_enabled=True),
    ),
    dict(
        id="case_02",
        description="HEL-spall, default timings, low noise",
        shot_type="HEL-spall",
        profile={},
        synthesis=dict(noise_sd=0.01),
        seed=2,
        config=dict(spall_enabled=True, hel_enabled=True),
    ),
    dict(
        id="case_03",
        description="HEL-spall, default timings, high noise",
        shot_type="HEL-spall",
        profile={},
        synthesis=dict(noise_sd=0.1),
        seed=3,
        config=dict(spall_enabled=True, hel_enabled=True),
    ),
    dict(
        id="case_04",
        description="velocity ramp, default timings, low noise",
        shot_type="velocity",
        profile={},
        synthesis=dict(noise_sd=0.01),
        seed=4,
        config=dict(spall_enabled=False, hel_enabled=False),
    ),
]


def profile_params(case):
    return {**PROFILE_DEFAULTS[case["shot_type"]], **case["profile"]}


def synthesis_params(case):
    return {**SYNTHESIS_DEFAULTS, **case["synthesis"]}


def get_cases(only=None):
    if not only:
        return list(CASES)
    unknown = set(only) - {c["id"] for c in CASES}
    if unknown:
        raise ValueError(f"Unknown case ids: {sorted(unknown)}")
    return [c for c in CASES if c["id"] in only]
