import argparse

from alpss.alpss_watcher import Watcher
from alpss.alpss_main import alpss_main
from alpss.multipoint.alpss_multipoint import alpss_multipoint
from alpss.utils.config import flatten_config
import os
import json
import logging
import sys
import pandas as pd

def start_watcher():
    w = Watcher()
    w.run()

def load_json_config(config):
    """Load configuration from a JSON file or return directly if it's already a dictionary."""
    if isinstance(config, dict):
        return config  # If already a dictionary, return it

    if isinstance(config, str) and os.path.exists(config):
        with open(config, "r") as file:
            return json.load(file)  # Load JSON directly

    raise ValueError(
        "Invalid config input: Provide a dictionary or a valid JSON file path."
    )


def alpss_main_with_config(config=None):
    """
    Run ALPSS with a given JSON configuration.

    Args:
        config (str or dict, optional): JSON config file, either given as parsable argument through CLI or directly as a string, or a dictionary containing config parameters.
    """

    if config is None:
        # If called from CLI, parse arguments
        parser = argparse.ArgumentParser(
            description="Run ALPSS using a JSON config file"
        )
        parser.add_argument(
            "config_path", type=str, help="Path to the JSON configuration file"
        )
        args = parser.parse_args()
        config = load_json_config(args.config_path)

    # Load the dictionary or YAML config
    else:
        config = load_json_config(config)

    # alpss_main flattens nested sections internally
    return alpss_main(**config)

def alpss_multipoint_with_config(config=None):
    """
    Run alpss_multipoint with a given nested-section JSON configuration.

    Args:
        config (str or dict, optional): Path to a JSON config file or a dict.
    """
    if config is None:
        parser = argparse.ArgumentParser(
            description="Run alpss_multipoint using a JSON config file"
        )
        parser.add_argument(
            "config_path", type=str, help="Path to the JSON configuration file"
        )
        args = parser.parse_args()
        config = load_json_config(args.config_path)
    else:
        config = load_json_config(config)

    # Flatten all sections into a single dict, then extract multipoint-specific keys
    flat = flatten_config(config)

    raw_channels = flat.pop("channels")
    channels = {name: pd.DataFrame(rows) for name, rows in raw_channels.items()}

    filepath = flat.pop("filepath")
    freq_lower = flat.pop("freq_lower", 1e9)
    freq_upper = flat.pop("freq_upper", 1e9)
    freq_refine_lower = flat.pop("freq_refine_lower", None)
    freq_refine_upper = flat.pop("freq_refine_upper", None)

    # Set per-probe by the wrapper; remove from shared kwargs to avoid conflicts
    flat.pop("freq_min", None)
    flat.pop("freq_max", None)
    flat.pop("lam", None)
    flat.pop("multipoint", None)

    return alpss_multipoint(
        channels=channels,
        filepath=filepath,
        freq_lower=freq_lower,
        freq_upper=freq_upper,
        freq_refine_lower=freq_refine_lower,
        freq_refine_upper=freq_refine_upper,
        **flat,
    )


def alpss_cli():
    """
    Entry point for console_scripts.
    Always uses sys.argv so `alpss /path/to/config.json` works.
    """
    try:
        sys.exit(alpss_main_with_config())
    except Exception as e:
        print(f"[ALPSS ERROR] {e}", file=sys.stderr)
        sys.exit(1)