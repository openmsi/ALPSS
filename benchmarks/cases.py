"""Benchmark cases: simulated (CASES) and real files (REAL_CASES).

Each simulated case is one synthetic signal. ``profile`` overrides
PROFILE_DEFAULTS for the case's shot type and is passed to
``generate_velocity_profile``; ``synthesis`` overrides SYNTHESIS_DEFAULTS and is
passed to ``velocity_to_pdv_voltage``. These are the only defaults: the
generator has none, so the signal and the truth always come from the same
numbers.

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

CASES = [
    # Bad: a single 5 ns step to 100 m/s. The branch's CUSUM only sees energy
    # above carrier + freq_offset (250 MHz, about 194 m/s at 1550 nm).
    dict(
        id="sim_low_velocity",
        description="step to 100 m/s, low noise",
        shot_type="HEL",
        profile=dict(V_HEL=100, V_plat=100),
        synthesis=dict(noise_sd=0.01),
        seed=6,
        config_edits=dict(spall_enabled=False, hel_enabled=False),
    ),
    # Good: shaped like tests/input_data/example_file.csv (1.5 us record, shock
    # at 614 ns, peak ~830 m/s, pullback to ~464 m/s, 2.23 GHz carrier).
    dict(
        id="sim_like_example",
        description="spall shot shaped like example_file.csv",
        shot_type="HEL-spall",
        profile=dict(
            t_begin=-614e-9, t_end=886e-9,
            V0=0, V_HEL=50, V_plat=830,
            t_hel_start=3e-9, t_hel_end=5e-9,
            t_plat_start=15e-9, t_plat_end=17e-9,
            t_spall=34e-9, t_recover=42e-9,
            dV_spall=366,
        ),
        synthesis=dict(noise_sd=0.02, lambda_tar=1550.01788e-9),
        seed=21,
        config_edits=dict(spall_enabled=True, hel_enabled=False),
    ),
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
