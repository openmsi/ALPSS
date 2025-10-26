"""
ALPSS - Automated Analysis of Photonic Doppler Velocimetry Spall Signals
Jake Diamond (2024)
Johns Hopkins University
Hopkins Extreme Materials Institute (HEMI)
Please report any bugs or comments to jdiamo15@jhu.edu

This script reads configuration from a JSON file and runs ALPSS analysis.

Usage:
    python alpss_run.py                          # Reads from config.json in current directory
    python alpss_run.py path/to/your/config.json # Reads from specified config file
"""

from alpss_main import alpss_main
import json
import os
import sys


def load_config(config_path="config.json"):
    """Load configuration from a JSON file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Please create a config.json file or specify the path as an argument.\n"
            f"Example usage: python alpss_run.py /path/to/config.json"
        )
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"Loaded configuration from: {config_path}")
    return config


def main():
    # Determine which config file to use
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        # Default to config.json in current directory
        config_path = "config.json"
    
    # Load the configuration
    config = load_config(config_path)
    
    # Create output directory if it doesn't exist
    out_dir = config.get("out_files_dir", "output_data/")
    os.makedirs(out_dir, exist_ok=True)
    
    # Run ALPSS with the loaded configuration
    print("\n" + "="*60)
    print("Starting ALPSS Analysis")
    print("="*60 + "\n")
    
    alpss_main(**config)
    
    print("\n" + "="*60)
    print("ALPSS Analysis Complete!")
    print("="*60)



if __name__ == "__main__":
    main()
