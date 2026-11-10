"""Benchmark cases: simulated (CASES) and real files (REAL_CASES).

Each simulated case is one synthetic signal. ``profile`` overrides
PROFILE_DEFAULTS for the case's shot type and is passed to
``generate_velocity_profile``; ``synthesis`` overrides SYNTHESIS_DEFAULTS and is
passed to ``velocity_to_pdv_voltage``. These are the only defaults: the
generator has none, so the signal and the truth always come from the same
numbers. A twin case instead rebuilds a real case's signal (see twins.py).

Each real case is a recorded file (``file``, relative to the repo root) with
``reference`` values that stand in for the truth.

``config_edits`` holds the ALPSS config keys a case changes relative to
tests/input_data/config.json. For simulated cases, run.py also sets what the
signal dictates (file, sample rate, wavelength, read window, HEL window).
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

# Twins: rebuilt from a real case (``twin["source"]``) by twins.py, with the
# knobs of twins.synthesize changing one ingredient at a time. Same
# config_edits as the source, so a twin runs like its real file.
_twin = dict(source="example_file")
CASES = [
    dict(id="twin_example", description="twin of example_file, as measured",
         twin=_twin, seed=1, config_edits={}),
    dict(id="twin_no_fade", description="twin without the carrier fade before the shock",
         twin=dict(_twin, carrier_fade=False), seed=1, config_edits={}),
    dict(id="twin_noisy", description="twin with 5x the noise",
         twin=dict(_twin, noise_scale=5), seed=1, config_edits={}),
    dict(id="twin_weak_return", description="twin with 1/4 of the Doppler amplitude",
         twin=dict(_twin, doppler_scale=0.25), seed=1, config_edits={}),
    dict(id="twin_slow", description="twin at 1/5 of the velocity (peak ~160 m/s)",
         twin=dict(_twin, velocity_scale=0.2), seed=1, config_edits={}),
]

REAL_CASES = [
    dict(
        id="example_file",  # matches the file name, which ALPSS names its outputs after
        description="example_file.csv, reference = main's Otsu start time",
        file="tests/input_data/example_file.csv",
        config_edits={},
        reference={"Signal Start Time": 614.08e-9},
    ),
]


def profile_params(case):
    return {**PROFILE_DEFAULTS[case["shot_type"]], **case["profile"]}


def synthesis_params(case):
    return {**SYNTHESIS_DEFAULTS, **case["synthesis"]}


def get_cases(only=None, include_real=False):
    pool = CASES + REAL_CASES if include_real else CASES
    if not only:
        return list(pool)
    unknown = set(only) - {c["id"] for c in pool}
    if unknown:
        raise ValueError(f"Unknown case ids: {sorted(unknown)}")
    return [c for c in pool if c["id"] in only]
