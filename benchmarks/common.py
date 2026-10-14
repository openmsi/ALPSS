import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH_DIR = os.path.join(REPO_ROOT, "benchmarks")
DATA_DIR = os.path.join(BENCH_DIR, "data")
RUNS_DIR = os.path.join(BENCH_DIR, "runs")
CONFIG_PATH = os.path.join(REPO_ROOT, "tests", "input_data", "config.json")


def load_config(path=CONFIG_PATH):
    """Load the nested ALPSS config (sections -> keys)."""
    with open(path) as f:
        return json.load(f)


def flat(config):
    from alpss.utils.config import flatten_config

    return flatten_config(config)


def set_key(config, key, value):
    """Set `key` inside whichever section of the nested config holds it."""
    for section in config.values():
        if isinstance(section, dict) and key in section:
            section[key] = value
            return
    raise KeyError(f"{key!r} is not in any section of the config")


def signal_path(data_dir, case_id):
    return os.path.join(data_dir, f"{case_id}.csv")


def truth_path(data_dir, case_id):
    return os.path.join(data_dir, f"{case_id}.truth.json")


def velocity_true_path(data_dir, case_id):
    return os.path.join(data_dir, f"{case_id}.velocity_true.csv")
