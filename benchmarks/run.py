"""Run ALPSS over the generated cases.

    poetry run python benchmarks/run.py --label main [--set key=value ...] [--only case_01 ...]

Uses tests/input_data/config.json, changing only what each simulated signal
requires (file, sample rate, wavelength, read window, HEL window, enabled
phases) plus any --set overrides. Writes ALPSS's usual outputs into
benchmarks/runs/<label>/<case>/ and a run.json describing the run.
"""

import argparse
import copy
import datetime
import importlib.metadata
import json
import os
import subprocess
import time
import traceback

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from alpss.commands import alpss_main_with_config  # noqa: E402

from cases import get_cases  # noqa: E402
from common import (  # noqa: E402
    CONFIG_PATH, DATA_DIR, REPO_ROOT, RUNS_DIR,
    set_key, signal_path, truth_path,
)


def parse_value(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def parse_overrides(pairs):
    overrides = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep:
            raise ValueError(f"--set expects key=value, got {pair!r}")
        overrides[key] = parse_value(value)
    return overrides


def case_config(base, record, data_dir, out_dir, overrides):
    config = copy.deepcopy(base)
    t0_ns = -record["profile"]["t_begin"] * 1e9  # shock arrival in ALPSS time

    set_key(config, "filepath", signal_path(data_dir, record["id"]))
    set_key(config, "out_files_dir", out_dir)
    set_key(config, "save_data", True)
    set_key(config, "display_plots", False)
    set_key(config, "time_to_skip", 0.0)
    set_key(config, "time_to_take", "all")
    set_key(config, "sample_rate", record["sample_rate"])
    set_key(config, "lam", record["synthesis"]["lambda_ref"])
    # the config's HEL window is relative to the shock arrival
    set_key(config, "hel_start_time_ns", t0_ns + base["hel"]["hel_start_time_ns"])
    set_key(config, "hel_end_time_ns", t0_ns + base["hel"]["hel_end_time_ns"])

    for key, value in {**record["config"], **overrides}.items():
        set_key(config, key, value)
    return config


def git_state():
    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True
        ).stdout.strip()

    return {
        "sha": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", required=True, help="name of this run")
    parser.add_argument("--set", nargs="+", metavar="KEY=VALUE", dest="overrides",
                        help="override config keys for every case")
    parser.add_argument("--only", nargs="+", help="case ids to run")
    parser.add_argument("--config", default=CONFIG_PATH)
    parser.add_argument("--data", default=DATA_DIR)
    parser.add_argument("--out", default=RUNS_DIR)
    args = parser.parse_args()

    with open(args.config) as f:
        base = json.load(f)
    overrides = parse_overrides(args.overrides)
    run_dir = os.path.join(args.out, args.label)
    os.makedirs(run_dir, exist_ok=True)

    run = {
        "label": args.label,
        "started": datetime.datetime.now().isoformat(timespec="seconds"),
        "alpss_version": importlib.metadata.version("alpss"),
        "git": git_state(),
        "config": os.path.relpath(args.config, REPO_ROOT),
        "overrides": overrides,
        "data": os.path.relpath(args.data, REPO_ROOT),
        "cases": {},
    }

    for case in get_cases(args.only):
        with open(truth_path(args.data, case["id"])) as f:
            record = json.load(f)
        out_dir = os.path.join(run_dir, case["id"])
        os.makedirs(out_dir, exist_ok=True)
        config = case_config(base, record, args.data, out_dir, overrides)

        print(f"{case['id']}: {case['description']} ...", flush=True)
        start = time.perf_counter()
        try:
            alpss_main_with_config(config)
            status, error = "ok", None
        except Exception as e:
            status, error = "failed", f"{type(e).__name__}: {e}"
            traceback.print_exc()
        finally:
            plt.close("all")
        elapsed = time.perf_counter() - start
        print(f"    {status} in {elapsed:.1f} s" + (f" ({error})" if error else ""))
        run["cases"][case["id"]] = {
            "status": status, "error": error, "seconds": round(elapsed, 2)
        }

    with open(os.path.join(run_dir, "run.json"), "w") as f:
        json.dump(run, f, indent=2)
    print(f"wrote {run_dir}")


if __name__ == "__main__":
    main()
