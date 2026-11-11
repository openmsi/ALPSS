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
# knobs of twins.synthesize changing one ingredient at a time. A twin runs
# with its source's config_edits (see config_edits()), like its real file.
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

CASES = (
    _twins("example_file", _VARIANTS)
    + _twins("JHAMAL00016-035_shot02", _VARIANTS)
    + _twins("JHAMAL00016-082_shot08", _VARIANTS)
    + _twins("JHAMAL00018-051_shot01", _VARIANTS)
    + _twins("JHAMAL00018-058_shot01", _VARIANTS)
    + _twins("JHAMAB00022-01_shot01", _VARIANTS)
)

# the lab pipeline's (alpss-dagster) settings, for files from Girder
_PIPELINE = dict(
    time_to_skip=0.0, time_to_take="all", lam=1.55e-6,
    freq_min=1.8e9, freq_max=2.8e9, t_before=25e-9, t_after=100e-9,
    smoothing_window=1801, blur_kernel=[15, 5],
)

REAL_CASES = [
    dict(
        id="example_file",  # matches the file name, which ALPSS names its outputs after
        description="example_file.csv, reference = main's Otsu start time",
        file="tests/input_data/example_file.csv",
        config_edits={},
        reference={"Signal Start Time": 614.08e-9},
    ),
    dict(
        id="JHAMAL00016-035_shot02",
        description="spall shot (610 m/s), LeCroy 40 GS/s, 2026-07-14",
        file="benchmarks/data/real/JHAMAL00016-035_shot02.csv",  # from Girder, not committed
        config_edits=dict(_PIPELINE, sample_rate=40e9),
        reference={"Signal Start Time": 1223.80e-9},  # alpss-dagster's Otsu result
    ),
    dict(
        id="JHAMAL00016-082_shot08",
        description="spall shot (539 m/s), LeCroy 40 GS/s, 2026-08-12",
        file="benchmarks/data/real/JHAMAL00016-082_shot08.csv",  # from Girder, not committed
        config_edits=dict(_PIPELINE, sample_rate=40e9),
        reference={"Signal Start Time": 1483.78e-9},  # alpss-dagster's Otsu result
    ),
    dict(
        id="JHAMAL00018-051_shot01",
        description="spall shot (515 m/s), LeCroy 40 GS/s, 2026-07-29",
        file="benchmarks/data/real/JHAMAL00018-051_shot01.csv",  # from Girder, not committed
        config_edits=dict(_PIPELINE, sample_rate=40e9),
        reference={"Signal Start Time": 1402.28e-9},  # alpss-dagster's Otsu result
    ),
    dict(
        id="JHAMAL00018-058_shot01",
        description="spall shot (559 m/s), LeCroy 40 GS/s, 2026-08-12",
        file="benchmarks/data/real/JHAMAL00018-058_shot01.csv",  # from Girder, not committed
        config_edits=dict(_PIPELINE, sample_rate=40e9),
        reference={"Signal Start Time": 1239.48e-9},  # alpss-dagster's Otsu result
    ),
    dict(
        id="JHAMAB00022-01_shot01",
        description="spall shot (415 m/s), sharp rise, Keysight 128 GS/s, 2025-11-06",
        file="benchmarks/data/real/JHAMAB00022-01_shot01.csv",  # from Girder, not committed
        config_edits=dict(_PIPELINE, sample_rate=128e9),
        reference={"Signal Start Time": 2292.45e-9},  # alpss-dagster's Otsu result
    ),
]


def profile_params(case):
    return {**PROFILE_DEFAULTS[case["shot_type"]], **case["profile"]}


def synthesis_params(case):
    return {**SYNTHESIS_DEFAULTS, **case["synthesis"]}


def config_edits(case):
    """The case's config_edits; a twin starts from its source's."""
    edits = case["config_edits"]
    if "twin" in case:
        source = next(c for c in REAL_CASES if c["id"] == case["twin"]["source"])
        edits = {**source["config_edits"], **edits}
    return edits


def get_cases(only=None, include_real=False):
    pool = CASES + REAL_CASES if include_real else CASES
    if not only:
        return list(pool)
    unknown = set(only) - {c["id"] for c in pool}
    if unknown:
        raise ValueError(f"Unknown case ids: {sorted(unknown)}")
    return [c for c in pool if c["id"] in only]
