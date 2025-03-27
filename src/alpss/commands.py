import argparse

from alpss.alpss_watcher import Watcher
from alpss.alpss_main import alpss_main
import os
import json
import logging

"""
Credit to Michael Cho
https://michaelcho.me/article/using-pythons-watchdog-to-monitor-changes-to-a-directory
"""


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
    Run ALPSS with a given YAML configuration.

    Args:
        config (str or dict, optional): Path to a YAML config file, either given through CLI or directly as a string, or a dictionary containing config parameters.
    """
    if config is None:  # expects an argument to be passed from CLI
        # If called from CLI, parse arguments
        parser = argparse.ArgumentParser(
            description="Run ALPSS using a YAML config file"
        )
        parser.add_argument(
            "config_path", type=str, help="Path to the YAML configuration file"
        )
        args = parser.parse_args()
        config = load_json_config(config)

    # Load the YAML config
    else:
        if type(config) == str:  # expects a path to a config file to be passed from CLI
            config = load_json_config(config)

    # Run ALPSS with the loaded config
    return alpss_main(**config)
