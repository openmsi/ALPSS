"""Simulated benchmark cases.

Each case is one synthetic signal. ``profile`` is passed to
``generate_velocity_profile`` (empty -> that shot type's defaults), ``synthesis``
to ``velocity_to_pdv_voltage``. ``config`` holds the ALPSS config keys this case
needs changed relative to tests/input_data/config.json (beyond the ones run.py
always derives from the signal).
"""

SAMPLE_RATE = 128e9

# Matches run_pdv_synthesis.py in PDV_simulated_data
DEFAULT_SYNTHESIS = dict(power_tar_dbm=-15)

CASES = [
    dict(
        id="case_01",
        description="HEL, default timings, low noise",
        shot_type="HEL",
        profile={},
        synthesis=dict(DEFAULT_SYNTHESIS, noise_sd=0.01),
        seed=1,
        config=dict(spall_enabled=False, hel_enabled=True),
    ),
    dict(
        id="case_02",
        description="HEL-spall, default timings, low noise",
        shot_type="HEL-spall",
        profile={},
        synthesis=dict(DEFAULT_SYNTHESIS, noise_sd=0.01),
        seed=2,
        config=dict(spall_enabled=True, hel_enabled=True),
    ),
    dict(
        id="case_03",
        description="HEL-spall, default timings, high noise",
        shot_type="HEL-spall",
        profile={},
        synthesis=dict(DEFAULT_SYNTHESIS, noise_sd=0.1),
        seed=3,
        config=dict(spall_enabled=True, hel_enabled=True),
    ),
    dict(
        id="case_04",
        description="velocity ramp, default timings, low noise",
        shot_type="velocity",
        profile={},
        synthesis=dict(DEFAULT_SYNTHESIS, noise_sd=0.01),
        seed=4,
        config=dict(spall_enabled=False, hel_enabled=False),
    ),
]


def get_cases(only=None):
    if not only:
        return list(CASES)
    unknown = set(only) - {c["id"] for c in CASES}
    if unknown:
        raise ValueError(f"Unknown case ids: {sorted(unknown)}")
    return [c for c in CASES if c["id"] in only]
