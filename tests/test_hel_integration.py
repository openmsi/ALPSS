import os
import pytest
from alpss.commands import alpss_main_with_config
from conftest import assert_results_match

CONFIG = os.path.join(os.path.dirname(__file__), "input_data", "hel", "config_hel.json")

EXPECTED_GOOD_HEL = {
    "Carrier Frequency": 1848000000.0,
    "Signal Start Time": 1.853429688e-06,
    "Spect Time Res": 8.749999999999998e-10,
    "Spect Freq Res": 50000000.0,
    "Spect Velocity Res": 38.75,
    "Smoothing Characteristic Time": 1.8311718749999998e-09,
    "HEL Detected": True,
    "HEL Strength (GPa)": 8.962928899090132,
    "HEL Uncertainty (GPa)": 7.010631686731411,
    "HEL Free Surface Velocity (m/s)": 791.7711768526897,
    "HEL Time Detection (ns)": 1926.4453130000002,
    "HEL Consecutive Points": 7968,
    "HEL Segment Duration (ns)": 126.72656199999938,
    "HEL Strain Rate": 0.0006986632234978005,
}


def test_hel_detected_good_trace():
    assert os.path.exists(CONFIG), f"Config not found: {CONFIG}"
    results = alpss_main_with_config(CONFIG)
    result_dict = results[1]["results"][0]
    assert result_dict["HEL Detected"] is True
    assert result_dict["Error Message"] == ""
    assert_results_match(result_dict, EXPECTED_GOOD_HEL)
