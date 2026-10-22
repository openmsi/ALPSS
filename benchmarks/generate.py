"""Generate the simulated signals and their ground truth.

    poetry run python benchmarks/generate.py [--only case_01 ...] [--out DIR]

Writes, per case, into benchmarks/data/:
    <case>.csv                 [time, voltage] signal ALPSS will read
    <case>.velocity_true.csv   [time, velocity] true history, in ALPSS's time base
    <case>.truth.json          expected ALPSS results + the parameters used
"""

import argparse
import json
import os

import numpy as np

from alpss.simulation import generate_velocity_profile, velocity_to_pdv_voltage
from alpss.utils.config import flatten_config

from cases import SAMPLE_RATE, get_cases
from common import (
    CONFIG_PATH, DATA_DIR,
    signal_path, truth_path, velocity_true_path,
)
from truth import profile_params, synthesis_params, truth_from_case


def generate_case(case, flat_config, out_dir):
    params = profile_params(case)
    time, velocity = generate_velocity_profile(
        case["shot_type"], sample_rate=SAMPLE_RATE, **params
    )
    # truth.py keeps its own copy of the profile defaults; make sure it agrees
    _, velocity_check = generate_velocity_profile(
        case["shot_type"], sample_rate=SAMPLE_RATE, **case["profile"]
    )
    if not np.array_equal(velocity, velocity_check):
        raise RuntimeError(
            f"{case['id']}: truth.PROFILE_DEFAULTS no longer matches "
            "generate_velocity_profile's defaults"
        )

    # pdv_synthesis draws noise from the global numpy RNG
    np.random.seed(case["seed"])
    velocity_to_pdv_voltage(
        time, velocity, output_csv=signal_path(out_dir, case["id"]),
        **synthesis_params(case),
    )

    np.savetxt(
        velocity_true_path(out_dir, case["id"]),
        np.column_stack((time - time[0], velocity)),
        delimiter=",",
        fmt=("%.9e", "%.6f"),
    )

    record = {
        "id": case["id"],
        "description": case["description"],
        "shot_type": case["shot_type"],
        "seed": case["seed"],
        "sample_rate": SAMPLE_RATE,
        "profile": params,
        "synthesis": synthesis_params(case),
        "config": case["config"],
        "truth": truth_from_case(case, flat_config, velocity),
    }
    with open(truth_path(out_dir, case["id"]), "w") as f:
        json.dump(record, f, indent=2)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="+", help="case ids to generate")
    parser.add_argument("--out", default=DATA_DIR)
    parser.add_argument("--config", default=CONFIG_PATH,
                        help="config providing the material constants for the truth")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    with open(args.config) as f:
        flat_config = flatten_config(json.load(f))
    for case in get_cases(args.only):
        record = generate_case(case, flat_config, args.out)
        print(f"{case['id']}: {case['description']}")
        for key, value in record["truth"].items():
            print(f"    {key:<34} {value:.6g}")


if __name__ == "__main__":
    main()
