"""Benchmark cases: simulated and twin (CASES) and real files (real_cases()).

Each simulated case is one synthetic signal built from a velocity profile. ``profile`` overrides
PROFILE_DEFAULTS for the case's shot type and is passed to
``generate_velocity_profile``; ``synthesis`` overrides SYNTHESIS_DEFAULTS and is
passed to ``velocity_to_pdv_voltage``. These are the only defaults: the
generator has none, so the signal and the truth always come from the same
numbers. A twin case instead rebuilds a real case's signal (see twins.py).

Real cases are not listed here: every ``<id>.csv`` in the real-data folder
with an ``<id>-results.csv`` beside it is one, and the results file holds the
reference values that stand in for the truth (see real_cases()).

``config_edits`` holds the ALPSS config keys a simulated case changes relative
to the benchmark config. run.py also sets what the signal dictates (file,
wavelength, read window, HEL window).
"""

import os

import pandas as pd

SAMPLE_RATE = 128e9  # time grid of the simulated cases' velocity profiles

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

# Simulated: one dict per case with ``shot_type``, ``profile``, ``synthesis``,
# ``seed`` and ``config_edits``.
SIMULATED_CASES = [
    # an illustration: the default HEL-spall profile (HEL at 100 m/s, plateau
    # at 300 m/s, 100 m/s pullback) on a ~2 GHz carrier with light noise
    dict(
        id="sim_hel_spall",
        description="default HEL-spall profile, light noise",
        shot_type="HEL-spall",
        profile={},
        synthesis=dict(noise_sd=0.02),
        seed=1,
        config_edits=dict(spall_enabled=True, hel_enabled=True),
    ),
]

# Twins: rebuilt from a real case (``twin["source"]``) by twins.py, with the
# knobs of twins.synthesize changing one ingredient at a time. A twin runs with
# the benchmark config, like its real file.
def _twins(source, variants):
    """The as-measured twin of `source` plus one case per variant, named after it."""
    base = dict(id=f"{source}_twin", description=f"twin of {source}, as measured",
                twin=dict(source=source), seed=1, config_edits={})
    return [base] + [
        dict(base, id=f"{source}_{name}", description=f"twin of {source}, {desc}",
             twin=dict(source=source, **knobs))
        for name, desc, knobs in variants
    ]


_VARIANTS = [
    ("noisy", "3x the noise", dict(noise_scale=3)),
    ("weak_return", "1/4 of the Doppler amplitude", dict(doppler_scale=0.25)),
    ("slow", "1/2 of the velocity", dict(velocity_scale=0.5)),
]

TWIN_CASES = (
    _twins("example_file", _VARIANTS)
    + _twins("JHAMAL00016-035_shot02", _VARIANTS)
    + _twins("JHAMAL00016-082_shot08", _VARIANTS)
    + _twins("JHAMAL00018-051_shot01", _VARIANTS)
    + _twins("JHAMAL00018-058_shot01", _VARIANTS)
    + _twins("JHAMAB00022-01_shot01", _VARIANTS)
)

CASES = SIMULATED_CASES + TWIN_CASES

# results the summary compares against a real file's results file
REFERENCE_METRICS = [
    "Velocity at Max Compression",
    "Time at Max Compression",
    "Carrier Frequency",
    "Signal Start Time",
    "Velocity at Max Tension",
    "Time at Max Tension",
    "HEL Free Surface Velocity (m/s)",
    "HEL Time Detection (ns)",
]


def real_cases(real_dir):
    """One case per ``<id>.csv`` in `real_dir` with an ``<id>-results.csv`` beside it."""
    if not os.path.isdir(real_dir):
        return []
    cases = []
    for name in sorted(os.listdir(real_dir)):
        case_id, ext = os.path.splitext(name)
        results = os.path.join(real_dir, f"{case_id}-results.csv")
        if ext != ".csv" or case_id.endswith("-results") or not os.path.exists(results):
            continue
        row = pd.read_csv(results).iloc[0]
        cases.append(dict(
            id=case_id,  # ALPSS names its outputs after the file
            description=f"{name}, reference = {os.path.basename(results)}",
            file=os.path.join(real_dir, name),
            reference={m: float(row[m]) for m in REFERENCE_METRICS
                       if m in row and pd.notna(row[m])},
        ))
    return cases


def profile_params(case):
    return {**PROFILE_DEFAULTS[case["shot_type"]], **case["profile"]}


def synthesis_params(case):
    return {**SYNTHESIS_DEFAULTS, **case["synthesis"]}


def get_cases(only=None, real_dir=None):
    """The simulated cases, or with `real_dir` the real files found there."""
    pool = real_cases(real_dir) if real_dir else CASES
    if not only:
        return list(pool)
    unknown = set(only) - {c["id"] for c in pool}
    if unknown:
        raise ValueError(f"Unknown case ids: {sorted(unknown)}")
    return [c for c in pool if c["id"] in only]
