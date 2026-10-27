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
    # --- Start-time detection (CUSUM) cases ---
    # Velocity level: a single 5 ns step to V. The branch's CUSUM only sees
    # energy above carrier + freq_offset (250 MHz, about 194 m/s at 1550 nm).
    dict(
        id="case_05",
        description="step to 50 m/s, low noise",
        shot_type="HEL",
        profile=dict(V_HEL=50, V_plat=50),
        synthesis=dict(noise_sd=0.01),
        seed=5,
        config=dict(spall_enabled=False, hel_enabled=False),
    ),
    dict(
        id="case_06",
        description="step to 100 m/s, low noise",
        shot_type="HEL",
        profile=dict(V_HEL=100, V_plat=100),
        synthesis=dict(noise_sd=0.01),
        seed=6,
        config=dict(spall_enabled=False, hel_enabled=False),
    ),
    dict(
        id="case_07",
        description="step to 150 m/s, low noise",
        shot_type="HEL",
        profile=dict(V_HEL=150, V_plat=150),
        synthesis=dict(noise_sd=0.01),
        seed=7,
        config=dict(spall_enabled=False, hel_enabled=False),
    ),
    dict(
        id="case_08",
        description="step to 250 m/s, low noise",
        shot_type="HEL",
        profile=dict(V_HEL=250, V_plat=250),
        synthesis=dict(noise_sd=0.01),
        seed=8,
        config=dict(spall_enabled=False, hel_enabled=False),
    ),
    dict(
        id="case_09",
        description="step to 500 m/s, low noise",
        shot_type="HEL",
        profile=dict(V_HEL=500, V_plat=500),
        synthesis=dict(noise_sd=0.01),
        seed=9,
        config=dict(spall_enabled=False, hel_enabled=False),
    ),
    # Rise time: the same 300 m/s step, spread over 20 ns and 100 ns.
    dict(
        id="case_10",
        description="20 ns rise to 300 m/s, low noise",
        shot_type="HEL",
        profile=dict(
            V_HEL=300, V_plat=300,
            t_rise1=20e-9, t_rise2=25e-9, t_rise3=30e-9,
            t_return1=100e-9, t_return2=120e-9,
        ),
        synthesis=dict(noise_sd=0.01),
        seed=10,
        config=dict(spall_enabled=False, hel_enabled=False),
    ),
    dict(
        id="case_11",
        description="100 ns rise to 300 m/s, low noise",
        shot_type="HEL",
        profile=dict(
            V_HEL=300, V_plat=300,
            t_rise1=100e-9, t_rise2=105e-9, t_rise3=110e-9,
            t_return1=300e-9, t_return2=320e-9,
        ),
        synthesis=dict(noise_sd=0.01),
        seed=11,
        # widen the analysis window so it reaches the end of the rise
        config=dict(spall_enabled=False, hel_enabled=False, t_after=200e-9),
    ),
    # Noise: case_02's shot at noise levels between and beyond case_02 / case_03.
    dict(
        id="case_12",
        description="HEL-spall, default timings, medium noise (0.05)",
        shot_type="HEL-spall",
        profile={},
        synthesis=dict(noise_sd=0.05),
        seed=12,
        config=dict(spall_enabled=True, hel_enabled=True),
    ),
    dict(
        id="case_13",
        description="HEL-spall, default timings, very high noise (0.2)",
        shot_type="HEL-spall",
        profile={},
        synthesis=dict(noise_sd=0.2),
        seed=13,
        config=dict(spall_enabled=True, hel_enabled=True),
    ),
    # Carrier strength: the back-reflection that keeps the carrier present after
    # the shock (default -15 dBm). Main's CUSUM watches the carrier fade.
    dict(
        id="case_14",
        description="HEL-spall, low noise, strong carrier (-5 dBm)",
        shot_type="HEL-spall",
        profile={},
        synthesis=dict(noise_sd=0.01, power_tar_dbm=-5),
        seed=14,
        config=dict(spall_enabled=True, hel_enabled=True),
    ),
    dict(
        id="case_15",
        description="HEL-spall, low noise, weak carrier (-25 dBm)",
        shot_type="HEL-spall",
        profile={},
        synthesis=dict(noise_sd=0.01, power_tar_dbm=-25),
        seed=15,
        config=dict(spall_enabled=True, hel_enabled=True),
    ),
    # Early arrival: the shock soon after the 250 ns carrier_band_time baseline.
    dict(
        id="case_16",
        description="HEL-spall, low noise, shock at 400 ns",
        shot_type="HEL-spall",
        profile=dict(t_begin=-400e-9),
        synthesis=dict(noise_sd=0.01),
        seed=16,
        config=dict(spall_enabled=True, hel_enabled=True),
    ),
    dict(
        id="case_17",
        description="HEL-spall, low noise, shock at 300 ns",
        shot_type="HEL-spall",
        profile=dict(t_begin=-300e-9),
        synthesis=dict(noise_sd=0.01),
        seed=17,
        config=dict(spall_enabled=True, hel_enabled=True),
    ),
    # Repeats with new noise draws, to tell real differences from chance.
    dict(
        id="case_18",
        description="case_02 repeated, seed 18",
        shot_type="HEL-spall",
        profile={},
        synthesis=dict(noise_sd=0.01),
        seed=18,
        config=dict(spall_enabled=True, hel_enabled=True),
    ),
    dict(
        id="case_19",
        description="case_02 repeated, seed 19",
        shot_type="HEL-spall",
        profile={},
        synthesis=dict(noise_sd=0.01),
        seed=19,
        config=dict(spall_enabled=True, hel_enabled=True),
    ),
    dict(
        id="case_20",
        description="case_03 repeated, seed 20",
        shot_type="HEL-spall",
        profile={},
        synthesis=dict(noise_sd=0.1),
        seed=20,
        config=dict(spall_enabled=True, hel_enabled=True),
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
